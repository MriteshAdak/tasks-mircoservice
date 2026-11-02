"""Persistence operations for tasks owned by :mod:`task_api`."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from tasks_api.exceptions import DatabaseOperationException, TaskNotFoundException
from tasks_api.models import Task


class TaskRepository:
    """Encapsulate task-schema SQLAlchemy queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, task: Task) -> Task:
        """Persist a new task."""

        try:
            self._session.add(task)
            self._session.commit()
            self._session.refresh(task)
            return task
        except SQLAlchemyError as error:
            self._session.rollback()
            raise DatabaseOperationException("Could not create the task.") from error

    def get_by_id_and_user(self, task_id: UUID, user_id: UUID) -> Task:
        """Return a task only if it belongs to the specified user.

        Returns 404 regardless of whether the task exists but belongs to
        another user or does not exist at all — prevents IDOR enumeration.
        """

        try:
            task = self._session.scalar(
                select(Task).where(Task.id == task_id, Task.user_id == user_id)
            )
        except SQLAlchemyError as error:
            raise DatabaseOperationException("Could not retrieve the task.") from error
        if task is None:
            raise TaskNotFoundException(str(task_id))
        return task

    def get_tasks_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        sort_by: str = "created_at desc",
    ) -> tuple[list[Task], int]:
        """Return paginated tasks for a user with optional status filter.

        Returns a tuple of (tasks, total_count) for pagination metadata.
        """

        try:
            query = select(Task).where(Task.user_id == user_id)
            count_query = (
                select(func.count()).select_from(Task).where(Task.user_id == user_id)
            )

            if status is not None:
                query = query.where(Task.status == status)
                count_query = count_query.where(Task.status == status)

            # Parse sort_by into column + direction
            sort_column, sort_direction = self._parse_sort_by(sort_by)
            if sort_direction == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            total = self._session.scalar(count_query) or 0

            query = query.limit(limit).offset(offset)
            tasks = list(self._session.scalars(query).all())

            return tasks, total
        except SQLAlchemyError as error:
            raise DatabaseOperationException("Could not retrieve tasks.") from error

    def update(self, task: Task) -> Task:
        """Persist updates to an existing task."""

        try:
            self._session.commit()
            self._session.refresh(task)
            return task
        except SQLAlchemyError as error:
            self._session.rollback()
            raise DatabaseOperationException("Could not update the task.") from error

    def delete(self, task: Task) -> None:
        """Delete a task from the database."""

        try:
            self._session.delete(task)
            self._session.commit()
        except SQLAlchemyError as error:
            self._session.rollback()
            raise DatabaseOperationException("Could not delete the task.") from error

    @staticmethod
    def _parse_sort_by(sort_by: str):
        """Parse a 'field_name direction' string into a column and direction."""

        _ALLOWED_SORT_COLUMNS = {
            "created_at": Task.created_at,
            "updated_at": Task.updated_at,
            "due_date": Task.due_date,
            "title": Task.title,
        }

        parts = sort_by.strip().split()
        field_name = parts[0] if parts else "created_at"
        direction = parts[1].lower() if len(parts) > 1 else "desc"

        if field_name not in _ALLOWED_SORT_COLUMNS:
            field_name = "created_at"
        if direction not in ("asc", "desc"):
            direction = "desc"

        return _ALLOWED_SORT_COLUMNS[field_name], direction
