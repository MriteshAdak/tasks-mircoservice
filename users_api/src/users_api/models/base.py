"""SQLAlchemy declarative base for user-owned tables."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from users_api.infrastructure import get_settings


class Base(DeclarativeBase):
    """Bind all user API models to the configured service schema."""

    metadata = MetaData(schema=get_settings().database_schema)
