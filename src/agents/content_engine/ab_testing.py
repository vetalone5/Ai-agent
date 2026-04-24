"""A/B testing for meta tags (title, description) to improve CTR."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update

from src.models.article import Article, ArticleMetrics

logger = logging.getLogger(__name__)

MIN_IMPRESSIONS_FOR_TEST = 100
MIN_TEST_DURATION_DAYS = 14
CTR_IMPROVEMENT_THRESHOLD = 10


class MetaTagABTester:
    """Runs A/B tests on article meta tags to optimize CTR from SERP."""

    def __init__(self, session_factory: Any, claude_client: Any) -> None:
        self._session_factory = session_factory
        self._claude = claude_client

    async def generate_variant(self, article_id: int) -> dict[str, Any]:
        """Generate alternative meta title/description for testing."""
        async with self._session_factory() as session:
            result = await session.execute(select(Article).where(Article.id == article_id))
            article = result.scalar_one_or_none()
            if not article:
                return {"error": "Article not found"}

        prompt = f"""Текущие мета-теги статьи:
Title: {article.meta_title}
Description: {article.meta_description}
Ключевое слово: {article.marker_keyword}
Тип: {article.content_type}

Сгенерируй 3 альтернативных варианта Title и Description для A/B теста.
Цель: повысить CTR из поисковой выдачи.

Правила:
- Title: до 60 символов, ключевик ближе к началу
- Description: до 160 символов, CTA, НЕ дублирует Title
- Используй триггеры: цифры, вопросы, года, эмоции
- Вариант A: data-driven (с цифрами)
- Вариант B: вопрос-based
- Вариант C: benefit-focused

JSON формат:
{{"variants": [{{"title": "...", "description": "...", "strategy": "..."}}]}}"""

        response = await self._claude.complete(
            system_prompt="Ты — CRO-специалист. Оптимизируешь мета-теги для CTR.",
            user_prompt=prompt,
            max_tokens=800,
        )
        return {
            "article_id": article_id,
            "current_title": article.meta_title,
            "current_description": article.meta_description,
            "variants": response,
            "requires_approval": True,
        }

    async def find_test_candidates(self, min_impressions: int = MIN_IMPRESSIONS_FOR_TEST) -> list[dict[str, Any]]:
        """Find articles with enough impressions but low CTR — good test candidates."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Article).where(Article.status == "published").limit(50)
            )
            articles = result.scalars().all()

        candidates = []
        for article in articles:
            metrics = await self._get_avg_metrics(article.id)
            if not metrics:
                continue
            if metrics["impressions"] >= min_impressions and metrics["ctr"] < 5.0:
                candidates.append({
                    "article_id": article.id,
                    "title": article.title,
                    "current_ctr": metrics["ctr"],
                    "impressions": metrics["impressions"],
                    "potential_gain": f"+{int(metrics['impressions'] * 0.02)} clicks if CTR +2%",
                })

        candidates.sort(key=lambda x: x["impressions"], reverse=True)
        return candidates

    async def apply_variant(self, article_id: int, new_title: str, new_description: str) -> dict[str, Any]:
        """Apply a new meta tag variant to an article."""
        async with self._session_factory() as session:
            old = await session.execute(select(Article).where(Article.id == article_id))
            article = old.scalar_one_or_none()
            if not article:
                return {"error": "Article not found"}

            previous = {"title": article.meta_title, "description": article.meta_description}

            await session.execute(
                update(Article)
                .where(Article.id == article_id)
                .values(
                    meta_title=new_title[:70],
                    meta_description=new_description[:170],
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        logger.info("A/B test applied for article %d: title changed", article_id)
        return {
            "article_id": article_id,
            "previous": previous,
            "new": {"title": new_title[:70], "description": new_description[:170]},
            "test_start": datetime.now(timezone.utc).isoformat(),
            "evaluate_after": (datetime.now(timezone.utc) + timedelta(days=MIN_TEST_DURATION_DAYS)).isoformat(),
        }

    async def _get_avg_metrics(self, article_id: int) -> dict[str, float] | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArticleMetrics)
                .where(ArticleMetrics.article_id == article_id)
                .order_by(ArticleMetrics.date.desc())
                .limit(7)
            )
            rows = result.scalars().all()
            if not rows:
                return None

            total_views = sum(r.page_views for r in rows)
            total_visitors = sum(r.unique_visitors for r in rows)
            avg_bounce = sum(r.bounce_rate for r in rows) / len(rows)
            return {
                "impressions": total_views,
                "visitors": total_visitors,
                "ctr": round(total_visitors / max(total_views, 1) * 100, 2),
                "bounce_rate": round(avg_bounce, 2),
            }
