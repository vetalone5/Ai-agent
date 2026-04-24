from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.config.constants import AgentType, TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    task_type: str
    agent_type: AgentType
    priority: TaskPriority = TaskPriority.MEDIUM
    data: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: int
    task_type: str
    agent_type: str
    priority: str
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


class ApprovalAction(BaseModel):
    feedback: str = ""


class ApprovalResponse(BaseModel):
    pending: list[TaskResponse]
    count: int
