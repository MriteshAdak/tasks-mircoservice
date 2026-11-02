"""User registration, lookup, authentication, and deletion business logic."""

from uuid import UUID

from users_api.auth.hashing import hash_password, verify_password
from users_api.exceptions import InvalidCredentialsException, UserNotFoundException
from users_api.models import User
from users_api.repositories import UserRepository
from users_api.schemas import LoginRequest, UserCreate, UserResponse
from users_api.validators import validate_display_name, validate_password, validate_username


class UserService:
    """Coordinate validation, credential handling, and user persistence."""

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def register(self, payload: UserCreate) -> UserResponse:
        """Validate and create a user with a securely stored password hash."""

        validate_username(payload.username)
        validate_display_name(payload.display_name)
        validate_password(payload.password)
        user = self._repository.create(
            User(username=payload.username, display_name=payload.display_name.strip()),
            hash_password(payload.password),
        )
        return UserResponse.model_validate(user)

    def get_by_username(self, username: str) -> UserResponse:
        """Return a public user representation by username."""

        return UserResponse.model_validate(self._repository.get_by_username(username))

    def get_by_id(self, user_id: UUID) -> UserResponse:
        """Return a public user representation by UUID."""

        return UserResponse.model_validate(self._repository.get_by_id(user_id))

    def authenticate(self, payload: LoginRequest) -> UserResponse:
        """Verify a username/password pair without exposing which value failed."""

        try:
            user = self._repository.get_by_username(payload.username)
        except UserNotFoundException as error:
            raise InvalidCredentialsException() from error

        credentials = self._repository.get_credentials(user.id)
        if credentials is None or not verify_password(payload.password, credentials.password_hash):
            raise InvalidCredentialsException()
        return UserResponse.model_validate(user)

    def delete(self, username: str) -> None:
        """Delete a user and its credentials without contacting task_api."""

        self._repository.delete(self._repository.get_by_username(username))
