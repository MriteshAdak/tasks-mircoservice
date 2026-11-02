"""Domain exceptions translated into HTTP responses by the application."""


class DomainException(Exception):
    """Base class for expected business and persistence failures."""


class NotFoundException(DomainException):
    """Raised when a requested domain record is absent."""


class UserNotFoundException(NotFoundException):
    """Raised when a username or user ID does not resolve to a user."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"User '{identifier}' was not found.")


class UserConflictException(DomainException):
    """Raised when a username is already registered."""

    def __init__(self, username: str) -> None:
        super().__init__(f"User with username '{username}' already exists.")


class ValidationException(DomainException):
    """Raised when a value violates a user-domain business rule."""


class InvalidCredentialsException(DomainException):
    """Raised when login credentials or a bearer token are invalid."""

    def __init__(self, message: str = "Invalid credentials.") -> None:
        super().__init__(message)


class ForbiddenException(DomainException):
    """Raised when an authenticated caller lacks permission."""


class DatabaseOperationException(DomainException):
    """Raised when a database operation fails unexpectedly."""
