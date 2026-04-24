"""Orchestrator — central coordinator that plans and dispatches work to agents."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from src.config.constants import AgentType, TaskPriority, TaskStatus
from src.config.settings import settings
from src.core.base_agent import BaseAgent
from src.core.event_bus import EventBus, Events
from src.models.kpi import DailyKPI
from src.models.task import Task

logger = logging.getLogger(__name__)


class Orchestrator(BaseAgent):
    agent_type = AgentType.ORCHESTRATOR

    def __init__(
        self,
        claude_client: Any,
        task_manager: Any,
        session_factory: Any,
        event_bus: EventBus,
    ) -> None:
        super().__init__(claude_client, task_manager)
        self._session_factory = session_factory
        self._events = event_bus
        self._events.subscribe(Events.TASK_COMPLETED, self._on_task_completed)
        self._events.subscribe(Events.TASK_FAILED, self._on_task_failed)
        self._events.subscribe(Events.TASK_APPROVED, self._on_task_approved)

    async def get_capabilities(self) -> list[str]:
        return ["weekly_plan", "dispatch_tasks", "review_progress"]

    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_type = task_data.get("task_type", "")

        if task_type == "weekly_plan":
            return await self.create_weekly_plan()
        elif task_type == "dispatch_tasks":
            return await self.dispatch_pending_tasks()
        elif task_type == "review_progress":
            return await self.review_progress()
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def create_weekly_plan(self) -> dict[str, Any]:
        """Monday planning: analyze KPI gaps → generate tasks for the week."""
        kpi = await self._get_current_kpi()
        pending = await self.tasks.get_pending_tasks(limit=50)
        task_summary = self._summarize_tasks(pending)

        prompt = f"""Текущие KPI:
- Посетители/мес: {kpi.get('visitors', 0)} (цель: {settings.goal_monthly_visitors})
- Регистрации/мес: {kpi.get('registrations', 0)} (цель: {settings.goal_monthly_registrations})
- Ключей в ТОП-10: {kpi.get('top10', 0)}
- AI-цитирований: {kpi.get('ai_citations', 0)}
- Bounce rate: {kpi.get('bounce_rate', 0)}%

Ожидающие задачи: {task_summary}

Доступные агенты: SEO Audit, Content Engine, Technical SEO, Analytics.

Составь план на неделю: какие задачи поручить каждому агенту?
Ответь JSON:
{{"tasks": [{{"agent": "agent_type", "task_type": "type", "priority": "high/medium/low", "description": "что делать"}}]}}"""

        response = await self.ask_claude(
            system_prompt="Ты — SEO-стратег. Планируешь работу агентов на неделю.",
            user_prompt=prompt,
            max_tokens=2000,
        )

        tasks_created = await self._create_tasks_from_plan(response)
        return {"plan": response, "tasks_created": tasks_created}

    async def dispatch_pending_tasks(self) -> dict[str, Any]:
        """Pick up pending tasks and route them to appropriate agents."""
        pending = await self.tasks.get_pending_tasks(limit=20)
        dispatched = 0

        for task in pending:
            if task["status"] == TaskStatus.CREATED:
                await self.tasks.update_status(task["id"], TaskStatus.QUEUED)
                dispatched += 1

        return {"dispatched": dispatched, "total_pending": len(pending)}

    async def review_progress(self) -> dict[str, Any]:
        """Mid-week review: check what's done, adjust priorities."""
        async with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())

            result = await session.execute(
                select(Task.status, func.count(Task.id))
                .where(Task.created_at >= week_start)
                .group_by(Task.status)
            )
            stats = dict(result.all())

        return {
            "week_stats": stats,
            "completed": stats.get(TaskStatus.COMPLETED, 0),
            "pending": stats.get(TaskStatus.CREATED, 0) + stats.get(TaskStatus.QUEUED, 0),
            "failed": stats.get(TaskStatus.FAILED, 0) + stats.get(TaskStatus.ERROR, 0),
            "awaiting_approval": stats.get(TaskStatus.NEEDS_APPROVAL, 0),
        }

    async def _get_current_kpi(self) -> dict[str, Any]:
        async with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            result = await session.execute(
                select(
                    func.coalesce(func.sum(DailyKPI.total_visitors), 0),
                    func.coalesce(func.sum(DailyKPI.registrations), 0),
                    func.coalesce(func.max(DailyKPI.keywords_top10), 0),
                    func.coalesce(func.max(DailyKPI.ai_citations_count), 0),
                    func.coalesce(func.avg(DailyKPI.bounce_rate), 0),
                ).where(DailyKPI.date >= month_start)
            )
            row = result.one()
            return {
                "visitors": int(row[0]),
                "registrations": int(row[1]),
                "top10": int(row[2]),
                "ai_citations": int(row[3]),
                "bounce_rate": round(float(row[4]), 1),
            }

    @staticmethod
    def _summarize_tasks(tasks: list[dict[str, Any]]) -> str:
        if not tasks:
            return "Нет ожидающих задач"
        by_agent: dict[str, int] = {}
        for t in tasks:
            agent = t.get("agent_type", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + 1
        return ", ".join(f"{agent}: {count}" for agent, count in by_agent.items())

    async def _create_tasks_from_plan(self, plan_text: str) -> int:
        """Parse AI plan and create real tasks."""
        try:
            start = plan_text.find("{")
            end = plan_text.rfind("}") + 1
            if start == -1 or end == 0:
                return 0
            parsed = json.loads(plan_text[start:end])
            plan_tasks = parsed.get("tasks", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Could not parse plan into tasks")
            return 0

        created = 0
        for pt in plan_tasks:
            agent = pt.get("agent", "")
            if agent not in [a.value for a in AgentType]:
                continue
            priority_map = {"critical": TaskPriority.CRITICAL, "high": TaskPriority.HIGH, "medium": TaskPriority.MEDIUM, "low": TaskPriority.LOW}
            await self.tasks.create_task(
                task_type=pt.get("task_type", "plan_task"),
                agent_type=AgentType(agent),
                priority=priority_map.get(pt.get("priority", "medium"), TaskPriority.MEDIUM),
                data={"description": pt.get("description", "")},
                created_by=AgentType.ORCHESTRATOR,
            )
            created += 1
        return created

    async def _on_task_completed(self, **data: Any) -> None:
        task_id = data.get("task_id")
        task = data.get("task")
        logger.info("Orchestrator: task %s completed (type: %s)", task_id, task.get("task_type") if task else "?")

    async def _on_task_failed(self, **data: Any) -> None:
        task_id = data.get("task_id")
        logger.warning("Orchestrator: task %s failed", task_id)

    async def _on_task_approved(self, **data: Any) -> None:
        """Post-approval processing: publish article, cross-post to Dzen, trigger indexing."""
        task_id = data.get("task_id")
        task = data.get("task", {})
        task_type = task.get("task_type", "")
        result = task.get("result", {})

        logger.info("Orchestrator: task %s approved, running post-processing", task_id)

        if task_type in ("run_pipeline", "write_article", "run_batch"):
            article_id = result.get("article_id")
            if article_id:
                await self._post_approve_article(article_id)

    async def _post_approve_article(self, article_id: int) -> None:
        """After article approval: publish → IndexNow → Dzen cross-post."""
        from src.tools.content_publisher import ContentPublisher
        from src.tools.dzen_publisher import DzenPublisher

        publisher = ContentPublisher(self._session_factory)
        pub_result = await publisher.publish(article_id)
        logger.info("Auto-published article %d: %s", article_id, pub_result.get("published_url"))

        published_url = pub_result.get("published_url", "")
        if published_url:
            from sqlalchemy import select
            from src.models.article import Article

            async with self._session_factory() as session:
                result = await session.execute(select(Article).where(Article.id == article_id))
                article = result.scalar_one_or_none()

            if article:
                dzen = DzenPublisher()
                dzen_result = await dzen.publish({
                    "title": article.title,
                    "content_md": article.content_md,
                    "published_url": published_url,
                })
                logger.info("Dzen cross-post for article %d: %s", article_id, dzen_result.get("status"))

                await self.tasks.create_task(
                    task_type="collect_positions",
                    agent_type=AgentType.ANALYTICS,
                    priority=TaskPriority.MEDIUM,
                    data={"trigger": f"article_{article_id}_published", "url": published_url},
                    created_by=AgentType.ORCHESTRATOR,
                )
