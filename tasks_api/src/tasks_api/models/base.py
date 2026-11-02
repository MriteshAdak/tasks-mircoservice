"""SQLAlchemy declarative base for task-owned tables."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from tasks_api.infrastructure import get_settings


class Base(DeclarativeBase):
    """Bind all task API models to the configured service schema."""

    metadata = MetaData(schema=get_settings().database_schema)
