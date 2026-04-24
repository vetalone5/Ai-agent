import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.kpi import DailyKPI
from src.tools.yandex_metrica import YandexMetricaClient

logger = logging.getLogger(__name__)


class TrafficAnalyzer:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._metrica = YandexMetricaClient()

    async def collect_daily_traffic(self) -> dict[str, Any]:
        """Collect yesterday's traffic data and save to DailyKPI."""
        try:
            summary = await self._metrica.get_traffic_summary()
            sources = await self._metrica.get_traffic_sources()
            parsed = self._metrica.parse_traffic_summary(summary)

            kpi = await self._save_daily_kpi(parsed, sources)
            logger.info(
                "Traffic collected: %d visits, bounce=%.1f%%",
                kpi.get("total_visitors", 0),
                kpi.get("bounce_rate", 0),
            )
            return kpi
        except Exception as e:
            logger.error("Failed to collect traffic: %s", e)
            return {}

    async def _save_daily_kpi(
        self, metrics: dict[str, Any], sources: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._session_factory() as session:
            kpi = DailyKPI(
                date=datetime.now(timezone.utc),
                total_visitors=int(metrics.get("visits", 0)),
                organic_visitors=self._extract_organic(sources),
                bounce_rate=float(metrics.get("bounceRate", 0)),
                avg_session_duration=float(metrics.get("avgVisitDurationSeconds", 0)),
                pages_per_session=float(metrics.get("pageDepth", 1)),
                traffic_sources=self._parse_sources(sources),
            )
            session.add(kpi)
            await session.commit()
            return {
                "total_visitors": kpi.total_visitors,
                "organic_visitors": kpi.organic_visitors,
                "bounce_rate": kpi.bounce_rate,
                "avg_session_duration": kpi.avg_session_duration,
                "pages_per_session": kpi.pages_per_session,
            }

    def _extract_organic(self, sources: dict[str, Any]) -> int:
        """Extract organic traffic count from sources response."""
        rows = sources.get("data", [])
        for row in rows:
            dims = row.get("dimensions", [{}])
            source_name = dims[0].get("name", "") if dims else ""
            if "organic" in source_name.lower():
                metrics = row.get("metrics", [0])
                return int(metrics[0]) if metrics else 0
        return 0

    @staticmethod
    def _parse_sources(sources: dict[str, Any]) -> dict[str, int]:
        """Parse traffic sources into {source: visits} dict."""
        rows = sources.get("data", [])
        result: dict[str, int] = {}
        for row in rows:
            dims = row.get("dimensions", [{}])
            source_name = dims[0].get("name", "unknown") if dims else "unknown"
            metrics = row.get("metrics", [0])
            result[source_name] = int(metrics[0]) if metrics else 0
        return result

    async def get_utm_report(self, days: int = 30) -> list[dict[str, Any]]:
        """Get UTM-based report for content performance tracking."""
        try:
            data = await self._metrica.get_utm_analytics()
            rows = data.get("data", [])
            report = []
            for row in rows:
                dims = row.get("dimensions", [])
                metrics = row.get("metrics", [])
                report.append({
                    "utm_source": dims[0].get("name", "") if len(dims) > 0 else "",
                    "utm_medium": dims[1].get("name", "") if len(dims) > 1 else "",
                    "utm_campaign": dims[2].get("name", "") if len(dims) > 2 else "",
                    "utm_content": dims[3].get("name", "") if len(dims) > 3 else "",
                    "visits": int(metrics[0]) if len(metrics) > 0 else 0,
                    "users": int(metrics[1]) if len(metrics) > 1 else 0,
                    "bounce_rate": round(metrics[2], 2) if len(metrics) > 2 else 0.0,
                    "avg_duration": round(metrics[3], 1) if len(metrics) > 3 else 0.0,
                })
            return report
        except Exception as e:
            logger.error("UTM report failed: %s", e)
            return []
