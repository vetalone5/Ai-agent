import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import AgentType, TaskPriority
from src.core.task_manager import TaskManager
from src.models.site_audit import AuditIssue, PageAudit
from src.tools.crawler import Crawler

logger = logging.getLogger(__name__)

SEVERITY_AGENT_MAP = {
    "critical": (AgentType.TECHNICAL_SEO, TaskPriority.CRITICAL),
    "high": (AgentType.CONTENT_ENGINE, TaskPriority.HIGH),
    "medium": (AgentType.TECHNICAL_SEO, TaskPriority.MEDIUM),
    "low": (AgentType.TECHNICAL_SEO, TaskPriority.LOW),
}


class SiteCrawler:
    """Crawls the target site and stores audit results, creating tasks for issues."""

    def __init__(self, session_factory: Any, task_manager: TaskManager) -> None:
        self._session_factory = session_factory
        self._tasks = task_manager
        self._crawler = Crawler()

    async def run_full_crawl(self) -> dict[str, Any]:
        """Crawl entire site, save results, create tasks for issues."""
        pages = await self._crawler.crawl_site()

        total_issues = 0
        tasks_created = 0

        async with self._session_factory() as session:
            for page in pages:
                audit = PageAudit(
                    url=page["url"],
                    status_code=page.get("status_code"),
                    title=page.get("title"),
                    meta_description=page.get("meta_description"),
                    h1=page.get("h1"),
                    word_count=page.get("word_count"),
                    load_time_ms=page.get("load_time_ms"),
                    has_canonical=page.get("has_canonical"),
                    has_schema=page.get("has_schema"),
                    internal_links_count=page.get("internal_links_count", 0),
                    issues=page.get("issues"),
                )
                session.add(audit)

                for issue in page.get("issues", []):
                    severity = issue.get("severity", "low")
                    agent_type, priority = SEVERITY_AGENT_MAP.get(
                        severity, (AgentType.TECHNICAL_SEO, TaskPriority.LOW)
                    )
                    audit_issue = AuditIssue(
                        url=page["url"],
                        issue_type=issue["type"],
                        severity=severity,
                        description=issue.get("detail", ""),
                        assigned_agent=agent_type,
                    )
                    session.add(audit_issue)
                    total_issues += 1

            await session.commit()

        for page in pages:
            for issue in page.get("issues", []):
                if issue.get("severity") in ("critical", "high"):
                    severity = issue["severity"]
                    agent_type, priority = SEVERITY_AGENT_MAP[severity]
                    await self._tasks.create_task(
                        task_type=f"fix_{issue['type']}",
                        agent_type=agent_type,
                        priority=priority,
                        data={"url": page["url"], "issue": issue},
                        created_by=AgentType.SEO_AUDIT,
                    )
                    tasks_created += 1

        logger.info("Crawl complete: %d pages, %d issues, %d tasks", len(pages), total_issues, tasks_created)
        return {"pages_crawled": len(pages), "issues_found": total_issues, "tasks_created": tasks_created}
