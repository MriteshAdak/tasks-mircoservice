"""HTTP endpoints for local login and current-user lookup."""

from fastapi import APIRouter, Depends

from users_api.auth.jwt import create_access_token
from users_api.dependencies import get_current_user, get_user_service
from users_api.infrastructure import get_settings
from users_api.schemas import LoginRequest, TokenResponse, UserResponse
from users_api.services import UserService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    """Verify credentials and return a short-lived local JWT."""

    user = user_service.authenticate(payload)
    return TokenResponse(
        access_token=create_access_token(user_id=user.id, username=user.username),
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Return the user identified by the validated bearer token."""

    return current_user
