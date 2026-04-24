"""Advanced spioniro.ru API client for AI visibility tracking."""

import logging
from typing import Any

from src.tools.spioniro_api import SpioniroAPIClient

logger = logging.getLogger(__name__)


class SpioniroTracker:
    """Wraps spioniro.ru API with higher-level analytics functions."""

    def __init__(self) -> None:
        self._api = SpioniroAPIClient()

    async def get_full_visibility_report(self) -> dict[str, Any]:
        """Comprehensive AI visibility report across all platforms."""
        mentions = await self._api.get_brand_mentions("spioniro")
        trends = await self._api.get_citation_trends("spioniro", days=30)
        competitors = await self._api.get_competitors_in_ai("seo-analytics")

        total = mentions.get("total", 0)
        by_platform = mentions.get("by_platform", {})

        return {
            "total_mentions": total,
            "yandex_gpt": by_platform.get("yandex_gpt", 0),
            "gigachat": by_platform.get("gigachat", 0),
            "chatgpt": by_platform.get("chatgpt", 0),
            "trend_30d": trends.get("trend", "stable"),
            "competitor_count": len(competitors),
            "top_competitors": competitors[:5],
        }

    async def check_keyword_batch(
        self,
        keywords: list[str],
        platform: str = "yandex_gpt",
    ) -> dict[str, Any]:
        """Check batch of keywords for AI citation status."""
        results = await self._api.get_keyword_visibility(keywords, platform)
        cited = [r for r in results if r.get("cited")]
        not_cited = [r for r in results if not r.get("cited")]

        return {
            "total_checked": len(keywords),
            "cited": len(cited),
            "not_cited": len(not_cited),
            "citation_rate": round(len(cited) / max(len(keywords), 1) * 100, 1),
            "cited_keywords": [r.get("keyword") for r in cited],
            "missing_keywords": [r.get("keyword") for r in not_cited],
        }
