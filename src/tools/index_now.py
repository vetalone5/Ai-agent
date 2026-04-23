import logging
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINTS = [
    "https://yandex.com/indexnow",
    "https://www.bing.com/indexnow",
]


class IndexNowClient:
    """IndexNow protocol for instant URL indexing in Yandex and Bing."""

    def __init__(self) -> None:
        self._key = settings.indexnow_key
        self._host = settings.target_site_url.replace("https://", "").replace("http://", "")
        self._http = httpx.AsyncClient(timeout=15.0)

    async def submit_url(self, url: str) -> dict[str, bool]:
        """Submit a single URL for indexing."""
        return await self.submit_urls([url])

    async def submit_urls(self, urls: list[str]) -> dict[str, bool]:
        """Submit multiple URLs for indexing via IndexNow."""
        if not self._key:
            logger.warning("IndexNow key not configured, skipping submission")
            return {}

        body = {
            "host": self._host,
            "key": self._key,
            "urlList": urls,
        }

        results: dict[str, bool] = {}
        for endpoint in INDEXNOW_ENDPOINTS:
            engine = "yandex" if "yandex" in endpoint else "bing"
            try:
                resp = await self._http.post(endpoint, json=body)
                success = resp.status_code in (200, 202)
                results[engine] = success
                if success:
                    logger.info("IndexNow %s: submitted %d URLs", engine, len(urls))
                else:
                    logger.warning("IndexNow %s: status %d", engine, resp.status_code)
            except Exception as e:
                logger.error("IndexNow %s failed: %s", engine, e)
                results[engine] = False

        return results
