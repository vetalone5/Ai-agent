"""Dashboard dependency injection — DB sessions and managers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.approval_manager import ApprovalManager
from src.core.claude_client import ClaudeClient
from src.core.event_bus import EventBus
from src.core.task_manager import TaskManager
from src.db.session import async_session_factory, get_session

event_bus = EventBus()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_task_manager() -> TaskManager:
    return TaskManager(get_session)


def get_approval_manager() -> ApprovalManager:
    return ApprovalManager(get_task_manager(), event_bus)
