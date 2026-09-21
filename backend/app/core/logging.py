"""Structured application logging. Secrets are never logged."""

import logging
import sys
from typing import Any

import structlog

from app.core.config import Settings


SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "authorization",
        "database_url",
        "dsn",
        "api_key",
        "credentials",
    }
)


def _drop_secrets(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in event_dict.items():
        lowered = str(key).lower()
        if lowered in SENSITIVE_KEYS or any(part in lowered for part in SENSITIVE_KEYS):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            _drop_secrets,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
