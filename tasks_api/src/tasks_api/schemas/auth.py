"""Authenticated-principal schema kept alongside JWT handling."""

from uuid import UUID

from pydantic import BaseModel


class TokenClaims(BaseModel):
    """Claims required from a validated local access token."""

    sub: UUID
    username: str | None = None
