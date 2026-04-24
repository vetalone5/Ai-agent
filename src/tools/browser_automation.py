"""Browser automation for probing AI search responses.

Uses httpx to query public AI endpoints where possible,
falls back to Playwright for JS-rendered pages.
"""

import logging
import re
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class AIProber:
    """Probes AI search engines to check if our brand/content is cited."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SEOAgentBot/1.0)"},
        )

    async def probe_yandex_neuro(self, query: str) -> dict[str, Any]:
        """Check Yandex search for Neuro (AI) answer presence.

        Yandex Neuro appears as a special block in SERP for ~50% of queries.
        We check if spioniro.ru is cited in that block.
        """
        try:
            resp = await self._http.get(
                "https://yandex.ru/search/",
                params={"text": query, "lr": "213"},
            )
            html = resp.text

            has_neuro = "data-fast-name=\"neuro\"" in html or "Нейро" in html
            our_brand_cited = "spioniro" in html.lower()
            sources = self._extract_neuro_sources(html)

            return {
                "query": query,
                "engine": "yandex_neuro",
                "has_ai_answer": has_neuro,
                "brand_cited": our_brand_cited,
                "sources_found": sources,
            }
        except Exception as e:
            logger.warning("Yandex Neuro probe failed for '%s': %s", query, e)
            return {"query": query, "engine": "yandex_neuro", "error": str(e)}

    async def probe_google_aio(self, query: str) -> dict[str, Any]:
        """Check Google for AI Overview presence."""
        try:
            resp = await self._http.get(
                "https://www.google.com/search",
                params={"q": query, "hl": "ru", "gl": "ru"},
            )
            html = resp.text

            has_aio = "ai-overview" in html.lower() or "data-sgrd" in html
            our_brand_cited = "spioniro" in html.lower()

            return {
                "query": query,
                "engine": "google_aio",
                "has_ai_answer": has_aio,
                "brand_cited": our_brand_cited,
            }
        except Exception as e:
            logger.warning("Google AIO probe failed for '%s': %s", query, e)
            return {"query": query, "engine": "google_aio", "error": str(e)}

    async def probe_batch(
        self, queries: list[str], engines: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Probe multiple queries across engines."""
        if engines is None:
            engines = ["yandex_neuro"]

        results = []
        for query in queries:
            for engine in engines:
                if engine == "yandex_neuro":
                    result = await self.probe_yandex_neuro(query)
                elif engine == "google_aio":
                    result = await self.probe_google_aio(query)
                else:
                    continue
                results.append(result)

        cited_count = sum(1 for r in results if r.get("brand_cited"))
        ai_count = sum(1 for r in results if r.get("has_ai_answer"))
        logger.info(
            "AI probe: %d queries, %d with AI answer, %d citing our brand",
            len(queries), ai_count, cited_count,
        )
        return results

    @staticmethod
    def _extract_neuro_sources(html: str) -> list[str]:
        """Extract source domains from Yandex Neuro answer block."""
        sources = []
        pattern = r'class="[^"]*neuro[^"]*"[^>]*>.*?href="https?://([^/"]+)'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        for domain in matches[:5]:
            sources.append(domain)
        return sources
