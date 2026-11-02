"""Persistence operations for users and their locally owned credentials."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from users_api.exceptions import (
    DatabaseOperationException,
    UserConflictException,
    UserNotFoundException,
)
from users_api.models import User, UserCredentials


class UserRepository:
    """Keep user-schema SQLAlchemy queries out of services and routers."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_username(self, username: str) -> User:
        """Return one user identified by username."""

        try:
            user = self._session.scalar(select(User).where(User.username == username))
        except SQLAlchemyError as error:
            raise DatabaseOperationException("Could not retrieve the user.") from error
        if user is None:
            raise UserNotFoundException(username)
        return user

    def get_by_id(self, user_id: UUID) -> User:
        """Return one user identified by UUID."""

        try:
            user = self._session.get(User, user_id)
        except SQLAlchemyError as error:
            raise DatabaseOperationException("Could not retrieve the user.") from error
        if user is None:
            raise UserNotFoundException(str(user_id))
        return user

    def create(self, user: User, password_hash: str) -> User:
        """Atomically persist a user and exactly one credential record."""

        try:
            self._session.add(user)
            self._session.flush()
            self._session.add(UserCredentials(user_id=user.id, password_hash=password_hash))
            self._session.commit()
            self._session.refresh(user)
            return user
        except IntegrityError as error:
            self._session.rollback()
            raise UserConflictException(user.username) from error
        except SQLAlchemyError as error:
            self._session.rollback()
            raise DatabaseOperationException("Could not create the user.") from error

    def get_credentials(self, user_id: UUID) -> UserCredentials | None:
        """Return the credential record for a user, if present."""

        try:
            return self._session.scalar(
                select(UserCredentials).where(UserCredentials.user_id == user_id)
            )
        except SQLAlchemyError as error:
            raise DatabaseOperationException("Could not retrieve user credentials.") from error

    def delete(self, user: User) -> None:
        """Delete credentials first, then the user, in one committed transaction."""

        try:
            self._session.execute(
                delete(UserCredentials).where(UserCredentials.user_id == user.id)
            )
            self._session.delete(user)
            self._session.commit()
        except SQLAlchemyError as error:
            self._session.rollback()
            raise DatabaseOperationException("Could not delete the user.") from error
