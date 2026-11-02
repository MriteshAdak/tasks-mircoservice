"""HS256 JWT creation and verification for local development."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError

from users_api.infrastructure.settings import Settings
from users_api.schemas.auth import TokenClaims
from users_api.exceptions import InvalidCredentialsException
from users_api.infrastructure import get_settings


def create_access_token(*, user_id: UUID, username: str) -> str:
    """Issue a short-lived token with the required subject and expiry claims."""

    settings: Settings = get_settings()
    expires_at: datetime = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode( # type: ignore[no-any-return]
        {"sub": str(user_id), "username": username, "exp": expires_at},
        settings.require_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenClaims:
    """Validate a bearer token and return its claims."""

    settings: Settings = get_settings()
    try:
        claims = jwt.decode( # type: ignore[no-any-return]
            token,
            settings.require_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except InvalidTokenError as error:
        raise InvalidCredentialsException("Invalid or expired access token.") from error

    try:
        return TokenClaims.model_validate(claims)
    except (KeyError, ValueError, TypeError, ValidationError) as error:
        raise InvalidCredentialsException("Access token has an invalid subject.") from error
