"""FastAPI dependency for extracting the authenticated user from a bearer token."""

import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tasks_api.auth.jwt import verify_access_token
from tasks_api.exceptions import AuthenticationException
from tasks_api.schemas.auth import TokenClaims

logger = logging.getLogger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenClaims:
    """Resolve the authenticated user from a valid local bearer token.

    task_api does not validate that the token subject still exists in
    user_api.users during normal request handling. This preserves the
    service boundary.
    """

    if credentials is None:
        raise AuthenticationException("Bearer authentication is required.")
    claims = verify_access_token(credentials.credentials)
    logger.info(
        "Authenticated task_api request for user_id=%s, username=%s",
        claims.sub,
        claims.username,
    )
    return claims
