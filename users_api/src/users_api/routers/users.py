"""HTTP endpoints for user registration, lookup, and deletion."""

from fastapi import APIRouter, Depends, Response, status

from users_api.dependencies import get_user_service
from users_api.schemas import UserCreate, UserResponse
from users_api.services import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Register a user and create their locally owned credential record."""

    return user_service.register(payload)


@router.get("/{username}", response_model=UserResponse)
def get_user(
    username: str,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Look up a user by username."""

    return user_service.get_by_username(username)


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    username: str,
    user_service: UserService = Depends(get_user_service),
) -> Response:
    """Delete user records and credentials without attempting task cleanup."""

    user_service.delete(username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
