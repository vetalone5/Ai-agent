import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed %s to event '%s'", handler.__qualname__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type] = [h for h in self._handlers[event_type] if h is not handler]

    async def publish(self, event_type: str, **data: Any) -> None:
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return

        logger.debug("Publishing '%s' to %d handlers", event_type, len(handlers))
        tasks = [self._safe_call(h, event_type, data) for h in handlers]
        await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_call(handler: EventHandler, event_type: str, data: dict[str, Any]) -> None:
        try:
            await handler(**data)
        except Exception:
            logger.error("Handler %s failed for event '%s'", handler.__qualname__, event_type, exc_info=True)


class Events:
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_NEEDS_APPROVAL = "task.needs_approval"
    TASK_APPROVED = "task.approved"
    TASK_REJECTED = "task.rejected"
    AUDIT_COMPLETED = "audit.completed"
    CONTENT_READY = "content.ready"
    KPI_ALERT = "kpi.alert"
    BEHAVIORAL_ALERT = "behavioral.alert"
