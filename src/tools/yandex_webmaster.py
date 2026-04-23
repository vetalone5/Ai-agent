import logging
from datetime import date, timedelta
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

YWM_API = "https://api.webmaster.yandex.net/v4"


class YandexWebmasterClient:
    """Yandex Webmaster API v4 client."""

    def __init__(self) -> None:
        self._token = settings.yandex_webmaster_token
        self._user_id = settings.yandex_webmaster_user_id
        self._host_id = settings.yandex_webmaster_host_id
        self._http = httpx.AsyncClient(timeout=30.0)

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"OAuth {self._token}"}

    @property
    def _host_url(self) -> str:
        return f"{YWM_API}/user/{self._user_id}/hosts/{self._host_id}"

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._host_url}/{path}" if not path.startswith("http") else path
        resp = await self._http.get(url, headers=self._headers, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._host_url}/{path}"
        resp = await self._http.post(url, headers=self._headers, json=json_data)
        resp.raise_for_status()
        return resp.json()

    async def get_host_info(self) -> dict[str, Any]:
        return await self._get("")

    async def get_search_queries(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Get search query analytics (positions, clicks, CTR)."""
        if not date_to:
            date_to = date.today() - timedelta(days=2)
        if not date_from:
            date_from = date_to - timedelta(days=7)

        params = {
            "order_by": "TOTAL_SHOWS",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "query_indicator": "TOTAL_SHOWS,TOTAL_CLICKS,AVG_SHOW_POSITION,AVG_CLICK_POSITION",
            "limit": limit,
            "offset": 0,
        }
        result = await self._get("search-queries/all/history", params=params)
        queries = result.get("queries", [])
        logger.info("YWM: fetched %d queries for %s..%s", len(queries), date_from, date_to)
        return queries

    async def get_indexing_stats(self) -> dict[str, Any]:
        """Get indexing statistics."""
        return await self._get("indexing/samples")

    async def get_sqi(self) -> dict[str, Any]:
        """Get Site Quality Index (ИКС / SQI)."""
        return await self._get("summary")

    async def request_recrawl(self, url: str) -> dict[str, Any]:
        """Request URL recrawl (reindex)."""
        result = await self._post("recrawl/queue", json_data={"url": url})
        logger.info("YWM: requested recrawl for %s", url)
        return result

    async def submit_sitemap(self, sitemap_url: str) -> dict[str, Any]:
        result = await self._post("sitemaps", json_data={"url": sitemap_url})
        logger.info("YWM: submitted sitemap %s", sitemap_url)
        return result

    async def get_diagnostics(self) -> dict[str, Any]:
        """Get site diagnostics (errors, warnings)."""
        return await self._get("diagnostics")

    async def set_region(self, region_id: int) -> dict[str, Any]:
        """Set regional targeting for the host."""
        return await self._post("regions", json_data={"region_id": region_id})

    def parse_query_rows(self, queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parsed = []
        for q in queries:
            indicators = q.get("indicators", {})
            parsed.append({
                "query": q.get("query_text", ""),
                "impressions": sum(indicators.get("TOTAL_SHOWS", [0])),
                "clicks": sum(indicators.get("TOTAL_CLICKS", [0])),
                "avg_position": self._avg(indicators.get("AVG_SHOW_POSITION", [])),
                "avg_click_position": self._avg(indicators.get("AVG_CLICK_POSITION", [])),
            })
        return parsed

    @staticmethod
    def _avg(values: list[float]) -> float:
        non_zero = [v for v in values if v and v > 0]
        return round(sum(non_zero) / len(non_zero), 1) if non_zero else 0.0
