"""Content publisher: manages article lifecycle from draft to published."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from src.config.settings import settings
from src.models.article import Article
from src.tools.index_now import IndexNowClient

logger = logging.getLogger(__name__)


class ContentPublisher:
    """Handles article publication: update status, trigger indexing, notify agents."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._indexnow = IndexNowClient()

    async def publish(self, article_id: int) -> dict[str, Any]:
        """Publish an approved article: set status, generate URL, trigger indexing."""
        async with self._session_factory() as session:
            result = await session.execute(select(Article).where(Article.id == article_id))
            article = result.scalar_one_or_none()
            if not article:
                return {"error": f"Article {article_id} not found"}
            if article.status not in ("draft", "approved"):
                return {"error": f"Article {article_id} is {article.status}, not publishable"}

            published_url = f"{settings.target_site_url}/blog/{article.slug}"
            now = datetime.now(timezone.utc)

            await session.execute(
                update(Article)
                .where(Article.id == article_id)
                .values(status="published", published_url=published_url, published_at=now, updated_at=now)
            )
            await session.commit()

        indexing = await self._trigger_indexing(published_url)

        logger.info("Published article %d: %s", article_id, published_url)
        return {
            "article_id": article_id,
            "published_url": published_url,
            "published_at": now.isoformat(),
            "indexing": indexing,
        }

    async def unpublish(self, article_id: int) -> dict[str, Any]:
        async with self._session_factory() as session:
            await session.execute(
                update(Article)
                .where(Article.id == article_id)
                .values(status="draft", published_url=None, published_at=None)
            )
            await session.commit()
        return {"article_id": article_id, "status": "draft"}

    async def publish_batch(self, article_ids: list[int]) -> list[dict[str, Any]]:
        results = []
        urls = []
        for aid in article_ids:
            result = await self.publish(aid)
            results.append(result)
            if url := result.get("published_url"):
                urls.append(url)
        if urls:
            await self._indexnow.submit_urls(urls)
        return results

    async def _trigger_indexing(self, url: str) -> dict[str, Any]:
        """Submit URL to IndexNow (Yandex/Bing) and request GSC/YWM recrawl."""
        indexing_results: dict[str, Any] = {}

        try:
            indexnow = await self._indexnow.submit_url(url)
            indexing_results["indexnow"] = indexnow
        except Exception as e:
            logger.warning("IndexNow failed for %s: %s", url, e)
            indexing_results["indexnow_error"] = str(e)

        try:
            from src.tools.yandex_webmaster import YandexWebmasterClient
            ywm = YandexWebmasterClient()
            await ywm.request_recrawl(url)
            indexing_results["yandex_recrawl"] = True
        except Exception as e:
            logger.warning("Yandex recrawl failed for %s: %s", url, e)
            indexing_results["yandex_recrawl_error"] = str(e)

        return indexing_results

    async def get_published_articles(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Article)
                .where(Article.status == "published")
                .order_by(Article.published_at.desc())
                .limit(limit)
            )
            return [
                {
                    "id": a.id, "title": a.title, "slug": a.slug,
                    "published_url": a.published_url, "published_at": a.published_at,
                    "word_count": a.word_count, "geo_score": a.geo_score,
                }
                for a in result.scalars().all()
            ]
