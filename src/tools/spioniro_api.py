import logging
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class SpioniroAPIClient:
    """Client for spioniro.ru API — AI mentions analytics (YandexGPT, GigaChat, ChatGPT)."""

    def __init__(self) -> None:
        self._base_url = settings.spioniro_api_url
        self._api_key = settings.spioniro_api_key
        self._http = httpx.AsyncClient(timeout=30.0)

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def get_brand_mentions(
        self,
        brand: str = "spioniro",
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Get AI mentions analytics for a brand across all platforms."""
        params: dict[str, str] = {"brand": brand}
        if platform:
            params["platform"] = platform

        resp = await self._http.get(
            f"{self._base_url}/api/v1/mentions", headers=self._headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Spioniro API: %d mentions for '%s'", data.get("total", 0), brand)
        return data

    async def get_keyword_visibility(
        self,
        keywords: list[str],
        platform: str = "yandex_gpt",
    ) -> list[dict[str, Any]]:
        """Check if specific keywords trigger AI citations for our brand."""
        body = {"keywords": keywords, "platform": platform}
        resp = await self._http.post(
            f"{self._base_url}/api/v1/visibility", headers=self._headers, json=body
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    async def get_competitors_in_ai(
        self,
        niche: str = "seo-analytics",
    ) -> list[dict[str, Any]]:
        """Get competitors mentioned by AI in our niche."""
        params = {"niche": niche}
        resp = await self._http.get(
            f"{self._base_url}/api/v1/competitors", headers=self._headers, params=params
        )
        resp.raise_for_status()
        return resp.json().get("competitors", [])

    async def get_citation_trends(
        self,
        brand: str = "spioniro",
        days: int = 30,
    ) -> dict[str, Any]:
        """Get citation trend over time."""
        params = {"brand": brand, "days": str(days)}
        resp = await self._http.get(
            f"{self._base_url}/api/v1/trends", headers=self._headers, params=params
        )
        resp.raise_for_status()
        return resp.json()
