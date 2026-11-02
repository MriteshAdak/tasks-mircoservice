"""FastAPI application factory and Lambda-importable app instance."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from users_api.exceptions import (
    DatabaseOperationException,
    ForbiddenException,
    InvalidCredentialsException,
    NotFoundException,
    UserConflictException,
    ValidationException,
)
from users_api.infrastructure import get_settings
from users_api.infrastructure.database import engine
from users_api.routers import auth, system, users


logger = logging.getLogger(__name__)


def _error_response(status_code: int, detail: str) -> JSONResponse:
    """Return the standard error body used by all application handlers."""

    return JSONResponse(status_code=status_code, content={"detail": detail})


def create_app() -> FastAPI:
    """Build the independently runnable user API without running migrations."""

    settings = get_settings()
    settings.require_jwt_secret()
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        engine.dispose()

    application = FastAPI(
        title="User API",
        description="User records and local-development authentication.",
        version="0.1.0",
        lifespan=lifespan,
    )
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @application.exception_handler(NotFoundException)
    async def handle_not_found(_: Request, error: NotFoundException) -> JSONResponse:
        return _error_response(404, str(error))

    @application.exception_handler(UserConflictException)
    async def handle_conflict(_: Request, error: UserConflictException) -> JSONResponse:
        return _error_response(409, str(error))

    @application.exception_handler(ValidationException)
    async def handle_domain_validation(_: Request, error: ValidationException) -> JSONResponse:
        return _error_response(400, str(error))

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation(
        _: Request, error: RequestValidationError
    ) -> JSONResponse:
        return _error_response(422, "Request validation failed.")

    @application.exception_handler(InvalidCredentialsException)
    async def handle_invalid_credentials(
        _: Request, error: InvalidCredentialsException
    ) -> JSONResponse:
        return _error_response(401, str(error))

    @application.exception_handler(ForbiddenException)
    async def handle_forbidden(_: Request, error: ForbiddenException) -> JSONResponse:
        return _error_response(403, str(error))

    @application.exception_handler(DatabaseOperationException)
    async def handle_database_error(
        _: Request, error: DatabaseOperationException
    ) -> JSONResponse:
        logger.exception("Database operation failed", exc_info=error)
        return _error_response(500, "Database operation failed.")

    @application.exception_handler(Exception)
    async def handle_unexpected(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unexpected application error", exc_info=error)
        return _error_response(500, "Unexpected server error.")

    application.include_router(users.router)
    application.include_router(auth.router)
    application.include_router(system.router)
    return application


app = create_app()
