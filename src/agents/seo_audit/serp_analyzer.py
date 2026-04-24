import logging
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

XMLRIVER_SERP = "https://xmlriver.com/search_yandex/xml"


class SerpAnalyzer:
    """Analyzes SERP composition for target keywords to determine content strategy."""

    def __init__(self, claude_client: Any) -> None:
        self._claude = claude_client
        self._http = httpx.AsyncClient(timeout=30.0)

    async def analyze_serp(self, query: str, search_engine: str = "yandex") -> dict[str, Any]:
        """Analyze the SERP for a query: content types, competition, AI presence."""
        if search_engine == "yandex":
            results = await self._fetch_yandex_serp(query)
        else:
            results = []

        analysis = self._classify_results(results)
        analysis["query"] = query
        analysis["competitiveness"] = self._score_competitiveness(results)
        analysis["recommended_content_type"] = self._recommend_content_type(analysis)

        return analysis

    async def analyze_batch(self, queries: list[str], limit: int = 10) -> list[dict[str, Any]]:
        """Analyze SERP for multiple queries."""
        results = []
        for query in queries[:limit]:
            try:
                result = await self.analyze_serp(query)
                results.append(result)
            except Exception as e:
                logger.warning("SERP analysis failed for '%s': %s", query, e)
        return results

    async def _fetch_yandex_serp(self, query: str) -> list[dict[str, Any]]:
        """Fetch SERP via XMLRiver."""
        if not settings.xmlriver_user or not settings.xmlriver_key:
            return []
        params = {
            "user": settings.xmlriver_user,
            "key": settings.xmlriver_key,
            "query": query,
            "groupby": "10",
            "lr": "225",
        }
        try:
            resp = await self._http.get(XMLRIVER_SERP, params=params)
            resp.raise_for_status()
            return self._parse_serp_response(resp.json())
        except Exception as e:
            logger.warning("XMLRiver SERP failed for '%s': %s", query, e)
            return []

    def _parse_serp_response(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        items = data.get("results", data.get("items", []))
        for i, item in enumerate(items[:10]):
            results.append({
                "position": i + 1,
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "domain": self._extract_domain(item.get("url", "")),
            })
        return results

    def _classify_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Classify SERP result types."""
        types = {"articles": 0, "aggregators": 0, "services": 0, "forums": 0, "video": 0}
        domains = []

        aggregator_markers = ["vc.ru", "habr.com", "dzen.ru", "pikabu.ru", "otzovik.com"]
        forum_markers = ["forum", "community", "discuss", "kyu.yandex", "answer"]
        video_markers = ["youtube.com", "rutube.ru", "vk.com/video"]

        for r in results:
            domain = r.get("domain", "")
            domains.append(domain)

            if any(m in domain for m in aggregator_markers):
                types["aggregators"] += 1
            elif any(m in domain for m in forum_markers):
                types["forums"] += 1
            elif any(m in domain for m in video_markers):
                types["video"] += 1
            elif any(m in domain for m in [".ru/service", ".ru/tool", "saas"]):
                types["services"] += 1
            else:
                types["articles"] += 1

        return {"result_types": types, "top_domains": domains[:5], "results_count": len(results)}

    def _score_competitiveness(self, results: list[dict[str, Any]]) -> str:
        """Estimate how competitive the SERP is."""
        if not results:
            return "unknown"
        strong_domains = ["vc.ru", "habr.com", "tadviser.ru", "rbc.ru", "forbes.ru"]
        strong_count = sum(1 for r in results if any(d in r.get("domain", "") for d in strong_domains))
        if strong_count >= 5:
            return "high"
        if strong_count >= 2:
            return "medium"
        return "low"

    def _recommend_content_type(self, analysis: dict[str, Any]) -> str:
        types = analysis.get("result_types", {})
        if types.get("forums", 0) >= 3:
            return "faq"
        if types.get("aggregators", 0) >= 4:
            return "guide"
        if types.get("video", 0) >= 2:
            return "guide"
        return "guide"

    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc
        except Exception:
            return url
