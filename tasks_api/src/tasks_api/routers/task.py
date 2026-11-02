"""HTTP endpoints for task CRUD operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from tasks_api.auth.dependencies import get_current_user
from tasks_api.dependencies import get_task_service
from tasks_api.schemas import (
    PaginationMeta,
    TaskCreateRequest,
    TaskListResponse,
    TaskResponse,
    TaskUpdateRequest,
)
from tasks_api.schemas.auth import TokenClaims
from tasks_api.services import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    current_user: TokenClaims = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Create a new task using the authenticated user's ID from the JWT token."""

    return task_service.create_task(current_user.sub, payload)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    current_user: TokenClaims = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at desc"),
) -> TaskListResponse:
    """List tasks owned by the authenticated user with pagination."""

    items, total = task_service.get_tasks(
        current_user.sub,
        limit=limit,
        offset=offset,
        status=status_filter,
        sort_by=sort_by,
    )
    return TaskListResponse(
        items=items,
        pagination=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    current_user: TokenClaims = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Get a task by ID, returning 404 if not found or not owned."""

    return task_service.get_task(task_id, current_user.sub)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    payload: TaskUpdateRequest,
    current_user: TokenClaims = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Update a task by ID, returning 404 if not found or not owned."""

    return task_service.update_task(task_id, current_user.sub, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    current_user: TokenClaims = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
) -> Response:
    """Delete a task by ID, returning 404 if not found or not owned."""

    task_service.delete_task(task_id, current_user.sub)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
