"""FastAPI dependencies for database-backed task operations."""

from fastapi import Depends
from sqlalchemy.orm import Session

from tasks_api.infrastructure.database import get_session
from tasks_api.repositories import TaskRepository
from tasks_api.services import TaskService


def get_task_repository(
    session: Session = Depends(get_session),
) -> TaskRepository:
    """Build a request-scoped repository."""

    return TaskRepository(session)


def get_task_service(
    repository: TaskRepository = Depends(get_task_repository),
) -> TaskService:
    """Build the task application service for a route."""

    return TaskService(repository)
