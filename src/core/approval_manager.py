import logging
from typing import Any

from src.config.constants import TaskStatus
from src.core.event_bus import EventBus, Events
from src.core.task_manager import TaskManager

logger = logging.getLogger(__name__)


class ApprovalManager:
    def __init__(self, task_manager: TaskManager, event_bus: EventBus) -> None:
        self._tasks = task_manager
        self._events = event_bus

    async def approve(self, task_id: int, reviewer: str = "human") -> None:
        task = await self._tasks.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task["status"] != TaskStatus.NEEDS_APPROVAL:
            raise ValueError(f"Task {task_id} is not pending approval (status: {task['status']})")

        await self._tasks.update_status(task_id, TaskStatus.APPROVED)
        logger.info("Task %d approved by %s", task_id, reviewer)
        await self._events.publish(Events.TASK_APPROVED, task_id=task_id, task=task)

    async def reject(self, task_id: int, feedback: str, reviewer: str = "human") -> None:
        task = await self._tasks.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task["status"] != TaskStatus.NEEDS_APPROVAL:
            raise ValueError(f"Task {task_id} is not pending approval (status: {task['status']})")

        result = task.get("result", {})
        result["rejection_feedback"] = feedback
        await self._tasks.update_status(
            task_id, TaskStatus.REJECTED, result=result, error=f"Rejected: {feedback}"
        )
        logger.info("Task %d rejected by %s: %s", task_id, reviewer, feedback)
        await self._events.publish(
            Events.TASK_REJECTED, task_id=task_id, task=task, feedback=feedback
        )

    async def get_pending_approvals(self) -> list[dict[str, Any]]:
        return await self._tasks.get_tasks_needing_approval()
