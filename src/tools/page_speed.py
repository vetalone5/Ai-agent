import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PSI_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


class PageSpeedClient:
    """Google PageSpeed Insights API for Core Web Vitals."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=60.0)

    async def analyze(self, url: str, strategy: str = "mobile") -> dict[str, Any]:
        """Run PageSpeed analysis. strategy: 'mobile' or 'desktop'."""
        params = {
            "url": url,
            "strategy": strategy,
            "category": "performance",
        }
        resp = await self._http.get(PSI_API, params=params)
        resp.raise_for_status()
        data = resp.json()
        return self._extract_cwv(data)

    def _extract_cwv(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract Core Web Vitals from PSI response."""
        lhr = data.get("lighthouseResult", {})
        audits = lhr.get("audits", {})
        metrics = lhr.get("categories", {}).get("performance", {})

        # Field data (real users from CrUX)
        field = data.get("loadingExperience", {}).get("metrics", {})

        cwv = {
            "performance_score": metrics.get("score", 0) * 100,
            "lcp_ms": self._get_audit_value(audits, "largest-contentful-paint"),
            "inp_ms": self._get_field_value(field, "INTERACTION_TO_NEXT_PAINT"),
            "cls": self._get_audit_value(audits, "cumulative-layout-shift"),
            "fcp_ms": self._get_audit_value(audits, "first-contentful-paint"),
            "ttfb_ms": self._get_audit_value(audits, "server-response-time"),
            "speed_index": self._get_audit_value(audits, "speed-index"),
            "total_blocking_time": self._get_audit_value(audits, "total-blocking-time"),
        }

        cwv["lcp_status"] = "good" if cwv["lcp_ms"] < 2500 else "poor" if cwv["lcp_ms"] > 4000 else "needs_improvement"
        cwv["inp_status"] = "good" if (cwv["inp_ms"] or 0) < 200 else "poor" if (cwv["inp_ms"] or 0) > 500 else "needs_improvement"
        cwv["cls_status"] = "good" if cwv["cls"] < 0.1 else "poor" if cwv["cls"] > 0.25 else "needs_improvement"

        logger.info("PSI: LCP=%.0fms (%s), INP=%sms, CLS=%.3f (%s), score=%.0f",
                     cwv["lcp_ms"], cwv["lcp_status"],
                     cwv["inp_ms"] or "N/A", cwv["cls"], cwv["cls_status"],
                     cwv["performance_score"])
        return cwv

    @staticmethod
    def _get_audit_value(audits: dict, key: str) -> float:
        audit = audits.get(key, {})
        return audit.get("numericValue", 0)

    @staticmethod
    def _get_field_value(field: dict, key: str) -> float | None:
        metric = field.get(key, {})
        return metric.get("percentile", None)
