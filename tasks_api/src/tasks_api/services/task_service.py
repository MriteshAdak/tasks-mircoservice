"""Task CRUD business logic scoped to the authenticated user."""

import logging
from uuid import UUID

from tasks_api.models import Task
from tasks_api.repositories import TaskRepository
from tasks_api.schemas import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from tasks_api.validators import (
    validate_due_date,
    validate_task_status,
    validate_task_title,
    validate_update_payload_not_empty,
)

logger = logging.getLogger(__name__)


class TaskService:
    """Coordinate validation, ownership enforcement, and task persistence."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create_task(self, user_id: UUID, payload: TaskCreateRequest) -> TaskResponse:
        """Create a new task for the authenticated user.

        The user_id comes from the JWT token, never from the request body.
        """

        validate_task_title(payload.title)
        status = validate_task_status(payload.status)
        if payload.due_date is not None:
            validate_due_date(payload.due_date)

        task = Task(
            user_id=user_id,
            title=payload.title.strip(),
            description=payload.description,
            status=status,
            due_date=payload.due_date,
        )
        task = self._repository.create(task)
        logger.info("Created task %s for user %s", task.id, user_id)
        return TaskResponse.model_validate(task)

    def get_tasks(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        sort_by: str = "created_at desc",
    ) -> tuple[list[TaskResponse], int]:
        """Return paginated tasks owned by the authenticated user."""

        # Validate status filter if provided
        if status is not None:
            validate_task_status(status)

        tasks, total = self._repository.get_tasks_by_user(
            user_id,
            limit=limit,
            offset=offset,
            status=status,
            sort_by=sort_by,
        )
        return [TaskResponse.model_validate(t) for t in tasks], total

    def get_task(self, task_id: UUID, user_id: UUID) -> TaskResponse:
        """Return a single task only if owned by the authenticated user.

        Returns 404 if the task does not exist or belongs to another user.
        """

        task = self._repository.get_by_id_and_user(task_id, user_id)
        return TaskResponse.model_validate(task)

    def update_task(
        self,
        task_id: UUID,
        user_id: UUID,
        payload: TaskUpdateRequest,
    ) -> TaskResponse:
        """Update an owned task with validated field changes."""

        validate_update_payload_not_empty(
            title=payload.title,
            description=payload.description,
            status=payload.status,
            due_date=payload.due_date,
        )

        task = self._repository.get_by_id_and_user(task_id, user_id)

        if payload.title is not None:
            validate_task_title(payload.title)
            task.title = payload.title.strip()

        if payload.description is not None:
            task.description = payload.description

        if payload.status is not None:
            task.status = validate_task_status(payload.status)

        if payload.due_date is not None:
            validate_due_date(payload.due_date)
            task.due_date = payload.due_date

        task = self._repository.update(task)
        logger.info("Updated task %s for user %s", task_id, user_id)
        return TaskResponse.model_validate(task)

    def delete_task(self, task_id: UUID, user_id: UUID) -> None:
        """Delete a task only if owned by the authenticated user."""

        task = self._repository.get_by_id_and_user(task_id, user_id)
        self._repository.delete(task)
        logger.info("Deleted task %s for user %s", task_id, user_id)
