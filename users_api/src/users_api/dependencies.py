"""FastAPI dependencies for database-backed user operations."""

import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from users_api.auth.jwt import decode_access_token
from users_api.schemas.auth import TokenClaims
from users_api.exceptions import InvalidCredentialsException, UserNotFoundException
from users_api.infrastructure.database import get_session
from users_api.repositories import UserRepository
from users_api.services import UserService


logger = logging.getLogger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(
    session: Session = Depends(get_session),
) -> UserRepository:
    """Build a request-scoped repository."""

    return UserRepository(session)


def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Build the user application service for a route."""

    return UserService(repository)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user_service: UserService = Depends(get_user_service),
):
    """Resolve the current user from a valid local bearer token."""

    if credentials is None:
        raise InvalidCredentialsException("Bearer authentication is required.")
    claims: TokenClaims = decode_access_token(credentials.credentials)
    logger.info("Authenticated user_api request for user_id=%s, username=%s", claims.sub, claims.username)
    try:
        return user_service.get_by_id(claims.sub)
    except UserNotFoundException as error:
        raise InvalidCredentialsException("The access token subject is no longer active.") from error

