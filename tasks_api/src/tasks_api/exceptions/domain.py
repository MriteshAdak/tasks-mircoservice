"""Domain exception types for :mod:`task_api`."""


class DomainException(Exception):
    """Base class for expected business and persistence failures."""


class NotFoundException(DomainException):
    """Raised when a requested domain record is absent."""


class TaskNotFoundException(NotFoundException):
    """Raised when a task ID does not resolve to a task owned by the caller."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task '{task_id}' was not found.")


class ValidationException(DomainException):
    """Raised when a value violates a task-domain business rule."""


class AuthenticationException(DomainException):
    """Raised when bearer token verification fails."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message)


class DatabaseOperationException(DomainException):
    """Raised when a database operation fails unexpectedly."""
