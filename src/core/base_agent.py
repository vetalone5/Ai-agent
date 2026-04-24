import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from src.config.constants import AgentType, TaskStatus
from src.config.cost_config import ModelTier, get_task_config

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    agent_type: AgentType

    def __init__(self, claude_client: Any, task_manager: Any) -> None:
        self.claude = claude_client
        self.tasks = task_manager
        self.logger = logging.getLogger(f"agent.{self.agent_type}")

    @abstractmethod
    async def execute_task(self, task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a specific task. Return result dict."""

    @abstractmethod
    async def get_capabilities(self) -> list[str]:
        """Return list of task types this agent can handle."""

    async def run_task(self, task_id: int) -> dict[str, Any]:
        task = await self.tasks.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        await self.tasks.update_status(task_id, TaskStatus.RUNNING)
        self.logger.info("Starting task %d: %s", task_id, task.get("task_type"))

        try:
            result = await self.execute_task(task_id, task)
            new_status = (
                TaskStatus.NEEDS_APPROVAL
                if result.get("requires_approval")
                else TaskStatus.COMPLETED
            )
            await self.tasks.update_status(task_id, new_status, result=result)
            self.logger.info("Task %d finished with status: %s", task_id, new_status)
            return result

        except Exception as e:
            self.logger.error("Task %d failed: %s", task_id, e, exc_info=True)
            retry_count = task.get("retry_count", 0)
            if retry_count < 3:
                await self.tasks.update_status(
                    task_id, TaskStatus.RETRY, error=str(e), retry_count=retry_count + 1
                )
            else:
                await self.tasks.update_status(task_id, TaskStatus.ERROR, error=str(e))
            raise

    async def ask_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        task_type: str = "",
    ) -> str:
        """Call LLM with automatic model tier selection based on task type."""
        config = get_task_config(task_type) if task_type else {}
        tier = config.get("tier", ModelTier.STANDARD)
        budget = config.get("max_tokens", max_tokens)

        if tier is None:
            self.logger.debug("Task %s doesn't need LLM, skipping", task_type)
            return ""

        return await self.claude.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=min(budget, max_tokens),
            tier=tier,
            agent=self.agent_type,
        )

    async def ask_cheap(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        """Shortcut for cheap model — use for short tasks."""
        return await self.claude.complete_cheap(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            agent=self.agent_type,
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
