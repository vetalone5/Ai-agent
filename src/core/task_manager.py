import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import AgentType, TaskPriority, TaskStatus
from src.models.task import Task

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def create_task(
        self,
        task_type: str,
        agent_type: AgentType,
        priority: TaskPriority = TaskPriority.MEDIUM,
        data: dict[str, Any] | None = None,
        created_by: AgentType | None = None,
    ) -> int:
        async with self._session_factory() as session:
            task = Task(
                task_type=task_type,
                agent_type=agent_type,
                priority=priority,
                status=TaskStatus.CREATED,
                data=data or {},
                created_by=created_by or AgentType.ORCHESTRATOR,
                created_at=datetime.now(timezone.utc),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            logger.info("Created task %d: %s for %s", task.id, task_type, agent_type)
            return task.id

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return None
            return self._task_to_dict(task)

    async def update_status(
        self,
        task_id: int,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        async with self._session_factory() as session:
            values: dict[str, Any] = {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
            if result is not None:
                values["result"] = result
            if error is not None:
                values["error"] = error
            if retry_count is not None:
                values["retry_count"] = retry_count
            if status == TaskStatus.COMPLETED:
                values["completed_at"] = datetime.now(timezone.utc)

            await session.execute(update(Task).where(Task.id == task_id).values(**values))
            await session.commit()
            logger.info("Task %d status → %s", task_id, status)

    async def get_pending_tasks(
        self, agent_type: AgentType | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            query = (
                select(Task)
                .where(Task.status.in_([TaskStatus.CREATED, TaskStatus.QUEUED, TaskStatus.RETRY]))
                .order_by(Task.priority, Task.created_at)
                .limit(limit)
            )
            if agent_type:
                query = query.where(Task.agent_type == agent_type)
            result = await session.execute(query)
            return [self._task_to_dict(t) for t in result.scalars().all()]

    async def get_tasks_needing_approval(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Task)
                .where(Task.status == TaskStatus.NEEDS_APPROVAL)
                .order_by(Task.created_at)
                .limit(limit)
            )
            return [self._task_to_dict(t) for t in result.scalars().all()]

    @staticmethod
    def _task_to_dict(task: Task) -> dict[str, Any]:
        return {
            "id": task.id,
            "task_type": task.task_type,
            "agent_type": task.agent_type,
            "priority": task.priority,
            "status": task.status,
            "data": task.data,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count,
            "created_by": task.created_by,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        }
