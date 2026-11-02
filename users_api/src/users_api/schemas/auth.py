"""Pydantic schemas for local authentication requests and responses."""

from pydantic import BaseModel, Field
from uuid import UUID

class LoginRequest(BaseModel):
    """Username and password submitted to obtain an access token."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Bearer token issued by the local authentication provider."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenClaims(BaseModel):
    """Claims required from a validated local access token."""

    sub: UUID
    username: str | None = None