import logging
from datetime import date, timedelta
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

METRICA_API = "https://api-metrica.yandex.net/stat/v1"


class YandexMetricaClient:
    """Yandex.Metrica API client for traffic and behavioral analytics."""

    def __init__(self) -> None:
        self._token = settings.yandex_metrica_token
        self._counter_id = settings.yandex_metrica_counter_id
        self._http = httpx.AsyncClient(timeout=30.0)

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"OAuth {self._token}"}

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        params["id"] = self._counter_id
        url = f"{METRICA_API}/{endpoint}"
        resp = await self._http.get(url, headers=self._headers, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_traffic_summary(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Get overall traffic metrics: visits, users, bounces, duration."""
        if not date_to:
            date_to = date.today() - timedelta(days=1)
        if not date_from:
            date_from = date_to - timedelta(days=7)

        params = {
            "date1": date_from.isoformat(),
            "date2": date_to.isoformat(),
            "metrics": "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:avgVisitDurationSeconds,ym:s:pageDepth",
            "group": "day",
        }
        result = await self._get("data/bytime", params)
        logger.info("Metrica: fetched traffic summary %s..%s", date_from, date_to)
        return result

    async def get_traffic_sources(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Get traffic by source: organic, direct, social, referral, etc."""
        if not date_to:
            date_to = date.today() - timedelta(days=1)
        if not date_from:
            date_from = date_to - timedelta(days=7)

        params = {
            "date1": date_from.isoformat(),
            "date2": date_to.isoformat(),
            "metrics": "ym:s:visits,ym:s:users,ym:s:bounceRate",
            "dimensions": "ym:s:lastTrafficSource",
        }
        return await self._get("data", params)

    async def get_page_metrics(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get per-page behavioral metrics: time, bounce, scroll depth."""
        if not date_to:
            date_to = date.today() - timedelta(days=1)
        if not date_from:
            date_from = date_to - timedelta(days=7)

        params = {
            "date1": date_from.isoformat(),
            "date2": date_to.isoformat(),
            "metrics": "ym:s:visits,ym:s:bounceRate,ym:s:avgVisitDurationSeconds,ym:s:pageDepth",
            "dimensions": "ym:s:startURL",
            "sort": "-ym:s:visits",
            "limit": limit,
        }
        return await self._get("data", params)

    async def get_conversions(
        self,
        goal_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Get conversion data (registrations, goals)."""
        if not date_to:
            date_to = date.today() - timedelta(days=1)
        if not date_from:
            date_from = date_to - timedelta(days=7)

        metrics = "ym:s:goal<goal_id>reaches,ym:s:goal<goal_id>conversionRate"
        if goal_id:
            metrics = metrics.replace("<goal_id>", str(goal_id))
        else:
            metrics = "ym:s:visits,ym:s:users"

        params = {
            "date1": date_from.isoformat(),
            "date2": date_to.isoformat(),
            "metrics": metrics,
            "group": "day",
        }
        return await self._get("data/bytime", params)

    async def get_utm_analytics(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Get UTM-based traffic analytics for content tracking."""
        if not date_to:
            date_to = date.today() - timedelta(days=1)
        if not date_from:
            date_from = date_to - timedelta(days=30)

        params = {
            "date1": date_from.isoformat(),
            "date2": date_to.isoformat(),
            "metrics": "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
            "dimensions": "ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign,ym:s:UTMContent",
            "sort": "-ym:s:visits",
            "limit": limit,
        }
        return await self._get("data", params)

    def parse_traffic_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract key metrics from traffic summary response."""
        totals = data.get("totals", [[]])
        metrics = data.get("query", {}).get("metrics", [])

        result: dict[str, float] = {}
        for i, metric in enumerate(metrics):
            values = totals[i] if i < len(totals) else []
            total = sum(v for v in values if v is not None)
            key = metric.split(":")[-1]
            result[key] = round(total / len(values), 2) if values else 0
        return result

    def parse_page_metrics(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse per-page data into structured list."""
        rows = data.get("data", [])
        parsed = []
        for row in rows:
            dims = row.get("dimensions", [{}])
            metrics = row.get("metrics", [])
            url = dims[0].get("name", "") if dims else ""
            parsed.append({
                "url": url,
                "visits": int(metrics[0]) if len(metrics) > 0 else 0,
                "bounce_rate": round(metrics[1], 2) if len(metrics) > 1 else 0.0,
                "avg_duration": round(metrics[2], 1) if len(metrics) > 2 else 0.0,
                "page_depth": round(metrics[3], 2) if len(metrics) > 3 else 0.0,
            })
        return parsed
