"""HS256 JWT verification for tasks_api (verification only, no token creation)."""

from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError

from tasks_api.exceptions import AuthenticationException
from tasks_api.infrastructure import get_settings
from tasks_api.schemas.auth import TokenClaims


def verify_access_token(token: str) -> TokenClaims:
    """Validate a bearer token and return its claims.

    Verifies signature, algorithm, and expiration. Extracts ``sub`` as the
    authenticated user ID and validates it is a valid UUIDv4. Optionally
    extracts ``username`` for logging/debug context.
    """

    settings = get_settings()
    try:
        claims = jwt.decode(  # type: ignore
            token,
            settings.require_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except InvalidTokenError as error:
        raise AuthenticationException("Invalid or expired access token.") from error

    try:
        token_claims = TokenClaims.model_validate(claims)
    except (KeyError, ValueError, TypeError, ValidationError) as error:
        raise AuthenticationException("Access token has an invalid subject.") from error

    # Validate that sub is a valid UUIDv4
    try:
        parsed = UUID(str(token_claims.sub))
        if parsed.version != 4:
            raise AuthenticationException(
                "Access token subject must be a valid UUIDv4."
            )
    except (ValueError, AttributeError) as error:
        raise AuthenticationException(
            "Access token subject must be a valid UUIDv4."
        ) from error

    return token_claims
