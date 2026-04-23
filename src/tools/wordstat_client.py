import logging
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

XMLRIVER_WORDSTAT = "https://xmlriver.com/search_yandex/xml"


class WordstatClient:
    """Yandex Wordstat API via XMLRiver for keyword research."""

    def __init__(self) -> None:
        self._user = settings.xmlriver_user
        self._key = settings.xmlriver_key
        self._http = httpx.AsyncClient(timeout=60.0)

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        params.update({"user": self._user, "key": self._key})
        resp = await self._http.get(XMLRIVER_WORDSTAT, params=params)
        resp.raise_for_status()
        return resp.json()

    async def wordstat_bulk(
        self,
        queries: list[str],
        region: str = "russia",
        include_assoc: bool = True,
        limit_per_query: int = 100,
    ) -> list[dict[str, Any]]:
        """Bulk keyword research: frequency + associations for up to 30 queries at once."""
        results = []
        # Process in batches of 30
        for i in range(0, len(queries), 30):
            batch = queries[i : i + 30]
            for query in batch:
                try:
                    data = await self._fetch_wordstat(query, region, limit_per_query, include_assoc)
                    results.extend(data)
                except Exception as e:
                    logger.warning("Wordstat failed for '%s': %s", query, e)
        logger.info("Wordstat bulk: %d queries → %d keywords", len(queries), len(results))
        return results

    async def wordstat_popular(self, query: str, region: str = "russia") -> list[dict[str, Any]]:
        """Get popular variations of a query (question-style keywords)."""
        return await self._fetch_wordstat(query, region, limit=150, include_assoc=False)

    async def wordstat_assoc(self, query: str, region: str = "russia") -> list[dict[str, Any]]:
        """Get associated queries (right column in Wordstat)."""
        params = {
            "query": query,
            "groupby": "wordstat",
            "lr": self._region_to_lr(region),
            "type": "assoc",
        }
        try:
            result = await self._request(params)
            return self._parse_wordstat_response(result, source=f"assoc:{query}")
        except Exception as e:
            logger.warning("Wordstat assoc failed for '%s': %s", query, e)
            return []

    async def _fetch_wordstat(
        self,
        query: str,
        region: str,
        limit: int,
        include_assoc: bool,
    ) -> list[dict[str, Any]]:
        params = {
            "query": query,
            "groupby": "wordstat",
            "lr": self._region_to_lr(region),
        }
        result = await self._request(params)
        keywords = self._parse_wordstat_response(result, source=f"mcp-popular:{query}")

        if include_assoc:
            assoc = await self.wordstat_assoc(query, region)
            keywords.extend(assoc)

        return keywords[:limit]

    def _parse_wordstat_response(
        self, data: dict[str, Any], source: str = "wordstat"
    ) -> list[dict[str, Any]]:
        keywords = []
        items = data.get("items", data.get("results", []))
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    keywords.append({
                        "query": item.get("keyword", item.get("query", "")),
                        "count": item.get("count", item.get("frequency", 0)),
                        "source": source,
                    })
        return keywords

    @staticmethod
    def _region_to_lr(region: str) -> str:
        regions = {
            "russia": "225",
            "moscow": "213",
            "spb": "2",
            "novosibirsk": "65",
        }
        return regions.get(region.lower(), "225")
