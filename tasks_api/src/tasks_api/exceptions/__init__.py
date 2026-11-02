"""Domain exception types for :mod:`task_api`."""

from .domain import (
    AuthenticationException,
    DatabaseOperationException,
    DomainException,
    NotFoundException,
    TaskNotFoundException,
    ValidationException,
)

__all__ = [
    "AuthenticationException",
    "DatabaseOperationException",
    "DomainException",
    "NotFoundException",
    "TaskNotFoundException",
    "ValidationException",
]
