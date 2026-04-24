import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.kpi import DailyKPI
from src.tools.spioniro_api import SpioniroAPIClient

logger = logging.getLogger(__name__)


class GeoMetricsCollector:
    """Collects AI citation metrics via spioniro.ru API."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._spioniro = SpioniroAPIClient()

    async def collect_ai_citations(self) -> dict[str, Any]:
        """Check brand mentions across AI platforms via spioniro.ru API."""
        try:
            mentions = await self._spioniro.get_brand_mentions(brand="spioniro")
            total = mentions.get("total", 0)
            by_platform = mentions.get("by_platform", {})

            await self._update_daily_kpi(total, by_platform)

            logger.info(
                "GEO metrics: %d total citations (YandexGPT=%d, GigaChat=%d, ChatGPT=%d)",
                total,
                by_platform.get("yandex_gpt", 0),
                by_platform.get("gigachat", 0),
                by_platform.get("chatgpt", 0),
            )
            return {"total_citations": total, "by_platform": by_platform}

        except Exception as e:
            logger.error("Failed to collect GEO metrics: %s", e)
            return {"error": str(e)}

    async def check_keyword_visibility(self, keywords: list[str]) -> list[dict[str, Any]]:
        """Check which keywords trigger AI citations for our brand."""
        try:
            results = await self._spioniro.get_keyword_visibility(
                keywords=keywords, platform="yandex_gpt"
            )
            cited = [r for r in results if r.get("cited")]
            logger.info(
                "Keyword visibility: %d/%d keywords cited in YandexGPT",
                len(cited), len(keywords),
            )
            return results
        except Exception as e:
            logger.error("Keyword visibility check failed: %s", e)
            return []

    async def _update_daily_kpi(self, total: int, details: dict[str, Any]) -> None:
        async with self._session_factory() as session:
            today = datetime.now(timezone.utc).date()
            await session.execute(
                update(DailyKPI)
                .where(DailyKPI.date >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc))
                .values(ai_citations_count=total, ai_citations_details=details)
            )
            await session.commit()
