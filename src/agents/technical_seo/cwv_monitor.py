"""Core Web Vitals monitoring and issue detection."""

import logging
from typing import Any

from src.config.constants import AgentType, TaskPriority
from src.core.task_manager import TaskManager
from src.tools.page_speed import PageSpeedClient

logger = logging.getLogger(__name__)

CWV_THRESHOLDS = {
    "lcp_ms": {"good": 2500, "poor": 4000},
    "inp_ms": {"good": 200, "poor": 500},
    "cls": {"good": 0.1, "poor": 0.25},
}


class CWVMonitor:
    """Monitors Core Web Vitals and creates tasks for performance issues."""

    def __init__(self, task_manager: TaskManager) -> None:
        self._psi = PageSpeedClient()
        self._tasks = task_manager

    async def check_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        """Check Core Web Vitals for multiple URLs."""
        results = []
        for url in urls:
            try:
                mobile = await self._psi.analyze(url, strategy="mobile")
                desktop = await self._psi.analyze(url, strategy="desktop")
                result = {
                    "url": url,
                    "mobile": mobile,
                    "desktop": desktop,
                    "issues": self._detect_issues(url, mobile),
                }
                results.append(result)
            except Exception as e:
                logger.warning("CWV check failed for %s: %s", url, e)
                results.append({"url": url, "error": str(e)})

        issues_count = sum(len(r.get("issues", [])) for r in results)
        if issues_count > 0:
            await self._create_tasks(results)

        logger.info("CWV check: %d URLs, %d issues", len(results), issues_count)
        return results

    def _detect_issues(self, url: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        issues = []
        for metric, thresholds in CWV_THRESHOLDS.items():
            value = data.get(metric, 0)
            if value is None:
                continue
            if value > thresholds["poor"]:
                issues.append({
                    "metric": metric,
                    "value": value,
                    "status": "poor",
                    "url": url,
                    "recommendation": self._get_recommendation(metric, value),
                })
            elif value > thresholds["good"]:
                issues.append({
                    "metric": metric,
                    "value": value,
                    "status": "needs_improvement",
                    "url": url,
                    "recommendation": self._get_recommendation(metric, value),
                })
        return issues

    async def _create_tasks(self, results: list[dict[str, Any]]) -> None:
        for result in results:
            for issue in result.get("issues", []):
                if issue["status"] == "poor":
                    await self._tasks.create_task(
                        task_type=f"fix_cwv_{issue['metric']}",
                        agent_type=AgentType.TECHNICAL_SEO,
                        priority=TaskPriority.HIGH,
                        data=issue,
                        created_by=AgentType.TECHNICAL_SEO,
                    )

    @staticmethod
    def _get_recommendation(metric: str, value: float) -> str:
        recommendations = {
            "lcp_ms": f"LCP {value:.0f}ms. Optimize: compress images, preload LCP element, reduce server response time.",
            "inp_ms": f"INP {value:.0f}ms. Optimize: break up long tasks (>50ms), use requestIdleCallback, defer non-critical JS.",
            "cls": f"CLS {value:.3f}. Fix: set explicit dimensions on images/ads, avoid injecting content above viewport.",
        }
        return recommendations.get(metric, f"{metric}: {value}")
