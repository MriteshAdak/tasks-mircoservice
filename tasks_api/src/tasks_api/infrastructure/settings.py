"""Runtime configuration owned by :mod:`task_api`."""

import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv

_SCHEMA_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class Settings:
    """Settings required by the task API runtime."""

    database_url: str
    database_schema: str
    jwt_secret: str | None
    jwt_algorithm: str
    cors_origins: tuple[str, ...]
    log_level: str

    @classmethod
    def from_environment(cls) -> Settings:
        """Load and validate runtime configuration from environment variables."""

        # Load environment variables from .env files
        load_dotenv(find_dotenv(".env.local"), override=True)
        load_dotenv(find_dotenv(".env"))

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL must be set to a PostgreSQL connection URL"
            )
        if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise RuntimeError("DATABASE_URL must use a PostgreSQL SQLAlchemy URL")

        database_schema = os.environ.get("TASK_API_DB_SCHEMA", "task_api")
        if not _SCHEMA_NAME.fullmatch(database_schema):
            raise RuntimeError(
                "TASK_API_DB_SCHEMA must be a valid PostgreSQL schema name"
            )

        jwt_secret = os.environ.get("JWT_SECRET")

        jwt_algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
        if jwt_algorithm != "HS256":
            raise RuntimeError("JWT_ALGORITHM must be HS256 for local authentication")

        cors_origins = tuple(
            origin.strip()
            for origin in os.environ.get("CORS_ORIGINS", "").split(",")
            if origin.strip()
        )
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

        return cls(
            database_url=database_url,
            database_schema=database_schema,
            jwt_secret=jwt_secret,
            jwt_algorithm=jwt_algorithm,
            cors_origins=cors_origins,
            log_level=log_level,
        )

    def require_jwt_secret(self) -> str:
        """Return verification secret, failing only when the API runtime needs it."""

        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET must be set")
        return self.jwt_secret


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings.from_environment()
