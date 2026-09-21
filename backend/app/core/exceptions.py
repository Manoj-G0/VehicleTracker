"""Application exceptions and FastAPI exception handlers."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        field: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.field = field
        self.extra = extra or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Vehicle not found") -> None:
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, field=field)


class ValidationAppError(AppError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, field=field)


class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "File exceeds configured limit") -> None:
        super().__init__(message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)


def _detail_from_app_error(exc: AppError) -> dict[str, Any]:
    if exc.field:
        return {"detail": [{"field": exc.field, "message": exc.message}]}
    return {"detail": exc.message, **exc.extra}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("application_error", message=exc.message, status_code=exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=_detail_from_app_error(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, str]] = []
        for error in exc.errors():
            loc = error.get("loc", ())
            field = ".".join(str(part) for part in loc if part not in {"body", "query", "path"})
            details.append(
                {
                    "field": field or "request",
                    "message": str(error.get("msg", "Invalid value")),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": details},
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_error", error=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred. Please try again."},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", error=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."},
        )
