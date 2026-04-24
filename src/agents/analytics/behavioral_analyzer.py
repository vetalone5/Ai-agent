import logging
from typing import Any

from src.config.constants import AgentType, TaskPriority
from src.core.task_manager import TaskManager
from src.tools.yandex_metrica import YandexMetricaClient

logger = logging.getLogger(__name__)

BOUNCE_THRESHOLD = 70.0
DURATION_THRESHOLD = 30.0
DEVIATION_THRESHOLD = 20.0


class BehavioralAnalyzer:
    """Analyzes behavioral metrics from Yandex.Metrica and generates tasks for agents."""

    def __init__(self, session_factory: Any, task_manager: TaskManager) -> None:
        self._session_factory = session_factory
        self._tasks = task_manager
        self._metrica = YandexMetricaClient()

    async def analyze_and_create_tasks(self) -> dict[str, Any]:
        """Full behavioral analysis cycle: collect → analyze → create tasks."""
        try:
            raw = await self._metrica.get_page_metrics(limit=50)
            pages = self._metrica.parse_page_metrics(raw)
        except Exception as e:
            logger.error("Failed to fetch page metrics: %s", e)
            return {"error": str(e), "tasks_created": 0}

        issues = self._find_issues(pages)
        tasks_created = 0

        for issue in issues:
            task_id = await self._create_task_for_issue(issue)
            if task_id:
                tasks_created += 1

        logger.info(
            "Behavioral analysis: %d pages, %d issues, %d tasks created",
            len(pages), len(issues), tasks_created,
        )
        return {"pages_analyzed": len(pages), "issues_found": len(issues), "tasks_created": tasks_created}

    def _find_issues(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        issues = []
        for page in pages:
            url = page.get("url", "")
            bounce = page.get("bounce_rate", 0)
            duration = page.get("avg_duration", 0)
            visits = page.get("visits", 0)

            if visits < 10:
                continue

            if bounce > BOUNCE_THRESHOLD:
                issues.append({
                    "url": url,
                    "type": "high_bounce",
                    "metric": "bounce_rate",
                    "value": bounce,
                    "threshold": BOUNCE_THRESHOLD,
                    "agent": AgentType.CONTENT_ENGINE,
                    "priority": TaskPriority.HIGH if bounce > 85 else TaskPriority.MEDIUM,
                    "recommendation": f"Bounce rate {bounce:.1f}% on {url}. Review content quality, add table of contents, improve first 1000 chars.",
                })

            if duration < DURATION_THRESHOLD and visits > 20:
                issues.append({
                    "url": url,
                    "type": "low_duration",
                    "metric": "avg_duration",
                    "value": duration,
                    "threshold": DURATION_THRESHOLD,
                    "agent": AgentType.CONTENT_ENGINE,
                    "priority": TaskPriority.MEDIUM,
                    "recommendation": f"Avg time {duration:.0f}s on {url}. Content may be thin or not matching user intent.",
                })

        return issues

    async def _create_task_for_issue(self, issue: dict[str, Any]) -> int | None:
        try:
            task_id = await self._tasks.create_task(
                task_type=f"behavioral_fix_{issue['type']}",
                agent_type=issue["agent"],
                priority=issue["priority"],
                data={
                    "url": issue["url"],
                    "metric": issue["metric"],
                    "value": issue["value"],
                    "threshold": issue["threshold"],
                    "recommendation": issue["recommendation"],
                },
                created_by=AgentType.ANALYTICS,
            )
            return task_id
        except Exception as e:
            logger.error("Failed to create task for %s: %s", issue["url"], e)
            return None
