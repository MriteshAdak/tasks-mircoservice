"""Pydantic schemas for task API request and response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tasks_api.enums import TaskStatus


class TaskCreateRequest(BaseModel):
    """Payload for creating a new task."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str = Field(default=TaskStatus.TODO)
    due_date: datetime | None = None


class TaskUpdateRequest(BaseModel):
    """Payload for partially updating an existing task."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    """Public representation of a task."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: str | None
    status: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int
    limit: int
    offset: int


class TaskListResponse(BaseModel):
    """Paginated task list with metadata."""

    items: list[TaskResponse]
    pagination: PaginationMeta
