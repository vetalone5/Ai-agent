import logging
from datetime import date, timedelta
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

GSC_API_BASE = "https://www.googleapis.com/webmasters/v3"
GSC_SEARCHANALYTICS = "https://searchconsole.googleapis.com/webmasters/v3"


class GoogleSearchConsoleClient:
    """Google Search Console API client using service account OAuth2."""

    def __init__(self) -> None:
        self._site_url = settings.gsc_site_url
        self._credentials_path = settings.gsc_service_account_json
        self._access_token: str | None = None
        self._http = httpx.AsyncClient(timeout=30.0)

    async def _get_token(self) -> str:
        if self._access_token:
            return self._access_token
        # In production: use google-auth library with service account JSON
        # For now, expect token to be refreshed externally or via settings
        raise NotImplementedError(
            "Set up google-auth service account credentials. "
            "See: https://developers.google.com/webmaster-tools/v1/how-tos/authorizing"
        )

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._http.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def get_search_analytics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        dimensions: list[str] | None = None,
        row_limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch search analytics (positions, clicks, CTR, impressions)."""
        if not end_date:
            end_date = date.today() - timedelta(days=3)
        if not start_date:
            start_date = end_date - timedelta(days=7)
        if not dimensions:
            dimensions = ["query", "page"]

        url = f"{GSC_SEARCHANALYTICS}/sites/{self._site_url}/searchAnalytics/query"
        body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions,
            "rowLimit": row_limit,
            "startRow": 0,
        }

        result = await self._request("POST", url, json=body)
        rows = result.get("rows", [])
        logger.info("GSC: fetched %d rows for %s..%s", len(rows), start_date, end_date)
        return rows

    async def get_sitemaps(self) -> list[dict[str, Any]]:
        url = f"{GSC_API_BASE}/sites/{self._site_url}/sitemaps"
        result = await self._request("GET", url)
        return result.get("sitemap", [])

    async def submit_sitemap(self, sitemap_url: str) -> None:
        url = f"{GSC_API_BASE}/sites/{self._site_url}/sitemaps/{sitemap_url}"
        await self._request("PUT", url)
        logger.info("GSC: submitted sitemap %s", sitemap_url)

    async def get_indexing_status(self) -> dict[str, Any]:
        """Get URL inspection data (requires Indexing API)."""
        url = f"https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
        body = {
            "inspectionUrl": self._site_url,
            "siteUrl": self._site_url,
        }
        return await self._request("POST", url, json=body)

    def parse_analytics_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform raw GSC rows into structured format."""
        parsed = []
        for row in rows:
            keys = row.get("keys", [])
            parsed.append({
                "query": keys[0] if len(keys) > 0 else "",
                "page": keys[1] if len(keys) > 1 else "",
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            })
        return parsed
