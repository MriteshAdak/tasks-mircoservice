"""User API exceptions."""
"""Domain exception types for :mod:`user_api`."""

from .domain import (
    DatabaseOperationException,
    DomainException,
    ForbiddenException,
    InvalidCredentialsException,
    NotFoundException,
    UserConflictException,
    UserNotFoundException,
    ValidationException,
)

__all__ = [
    "DatabaseOperationException",
    "DomainException",
    "ForbiddenException",
    "InvalidCredentialsException",
    "NotFoundException",
    "UserConflictException",
    "UserNotFoundException",
    "ValidationException",
]
