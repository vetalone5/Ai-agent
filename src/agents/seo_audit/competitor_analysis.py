import logging
from typing import Any

from sqlalchemy import select

from src.models.site_audit import Competitor
from src.tools.crawler import Crawler

logger = logging.getLogger(__name__)


class CompetitorAnalyzer:
    """Analyzes competitor blogs for content gaps and strategies."""

    def __init__(self, session_factory: Any, claude_client: Any) -> None:
        self._session_factory = session_factory
        self._claude = claude_client

    async def analyze_all(self) -> list[dict[str, Any]]:
        """Analyze all registered competitors."""
        competitors = await self._get_competitors()
        results = []

        for comp in competitors:
            try:
                analysis = await self._analyze_competitor(comp)
                results.append(analysis)
            except Exception as e:
                logger.error("Failed to analyze %s: %s", comp["domain"], e)

        logger.info("Analyzed %d/%d competitors", len(results), len(competitors))
        return results

    async def find_content_gaps(self) -> dict[str, Any]:
        """Find topics covered by competitors but not by us."""
        analyses = await self.analyze_all()

        competitor_topics: set[str] = set()
        for a in analyses:
            competitor_topics.update(a.get("topics", []))

        our_crawler = Crawler()
        our_pages = await our_crawler.crawl_site()
        our_topics = set()
        for page in our_pages:
            h2_list = page.get("h2_list", [])
            our_topics.update(h.lower() for h in h2_list)
            if page.get("title"):
                our_topics.add(page["title"].lower())

        gaps = competitor_topics - our_topics

        prompt = (
            f"У нас есть топики на нашем сайте: {list(our_topics)[:30]}\n"
            f"У конкурентов есть топики, которых у нас нет: {list(gaps)[:30]}\n"
            f"Выдели 10 самых важных контент-гэпов для сайта аналитики AI-упоминаний бренда. "
            f"Формат: JSON-список строк."
        )
        try:
            ai_gaps = await self._claude.complete(
                system_prompt="Ты — SEO-аналитик. Отвечай JSON-списком строк.",
                user_prompt=prompt,
                max_tokens=500,
            )
        except Exception:
            ai_gaps = str(list(gaps)[:10])

        return {"total_gaps": len(gaps), "top_gaps": ai_gaps, "competitor_count": len(analyses)}

    async def _get_competitors(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(select(Competitor))
            return [
                {"domain": c.domain, "name": c.name, "blog_url": c.blog_url}
                for c in result.scalars().all()
            ]

    async def _analyze_competitor(self, comp: dict[str, Any]) -> dict[str, Any]:
        blog_url = comp.get("blog_url")
        if not blog_url:
            return {"domain": comp["domain"], "topics": [], "article_count": 0}

        crawler = Crawler(base_url=blog_url, max_pages=30)
        pages = await crawler.crawl_site()

        topics = []
        for page in pages:
            if page.get("title"):
                topics.append(page["title"].lower())
            for h2 in page.get("h2_list", []):
                topics.append(h2.lower())

        return {
            "domain": comp["domain"],
            "name": comp.get("name"),
            "article_count": len(pages),
            "topics": topics,
            "avg_word_count": self._avg([p.get("word_count", 0) for p in pages]),
            "schema_usage": sum(1 for p in pages if p.get("has_schema")),
        }

    @staticmethod
    def _avg(values: list[int]) -> float:
        non_zero = [v for v in values if v > 0]
        return round(sum(non_zero) / len(non_zero), 0) if non_zero else 0
