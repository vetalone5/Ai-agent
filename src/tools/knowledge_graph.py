"""Knowledge Graph integration: Wikidata, Google Business Profile."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


class KnowledgeGraphClient:
    """Checks and manages brand presence in Knowledge Graph sources."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0)

    async def search_wikidata(self, query: str) -> list[dict[str, Any]]:
        """Search Wikidata for an entity."""
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "ru",
            "format": "json",
            "limit": 5,
        }
        try:
            resp = await self._http.get(WIKIDATA_API, params=params)
            resp.raise_for_status()
            data = resp.json()
            return [
                {"id": r.get("id"), "label": r.get("label"), "description": r.get("description")}
                for r in data.get("search", [])
            ]
        except Exception as e:
            logger.warning("Wikidata search failed: %s", e)
            return []

    async def check_brand_entity(self, brand: str = "Spioniro") -> dict[str, Any]:
        """Check if brand has a Wikidata entity."""
        results = await self.search_wikidata(brand)
        found = any(brand.lower() in (r.get("label", "").lower()) for r in results)
        return {
            "brand": brand,
            "wikidata_found": found,
            "results": results,
            "action_needed": "create" if not found else "verify",
        }

    async def get_entity_data(self, entity_id: str) -> dict[str, Any]:
        """Get full entity data from Wikidata."""
        params = {
            "action": "wbgetentities",
            "ids": entity_id,
            "format": "json",
            "languages": "ru|en",
        }
        try:
            resp = await self._http.get(WIKIDATA_API, params=params)
            resp.raise_for_status()
            data = resp.json()
            entity = data.get("entities", {}).get(entity_id, {})
            labels = entity.get("labels", {})
            descriptions = entity.get("descriptions", {})
            return {
                "id": entity_id,
                "label_ru": labels.get("ru", {}).get("value", ""),
                "label_en": labels.get("en", {}).get("value", ""),
                "description_ru": descriptions.get("ru", {}).get("value", ""),
                "claims_count": len(entity.get("claims", {})),
            }
        except Exception as e:
            logger.warning("Wikidata entity fetch failed: %s", e)
            return {"id": entity_id, "error": str(e)}

    async def verify_consistency(self, brand: str, expected_url: str) -> dict[str, Any]:
        """Verify brand NAP consistency across platforms."""
        return {
            "brand": brand,
            "expected_url": expected_url,
            "checks": {
                "wikidata": "needs_verification",
                "google_business": "needs_verification",
                "yandex_business": "needs_verification",
                "schema_on_site": "needs_verification",
            },
            "recommendation": (
                "Ensure Name, URL, and description are identical "
                "across all platforms. Use sameAs links in Organization schema."
            ),
        }
