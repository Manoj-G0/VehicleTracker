"""Best-effort Redis cache for repeat vehicle reads."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_client: Redis | None = None
_VERSION_KEY = "vehicle-cache:version"
_CACHE_PREFIX = "vehicle-cache:v"
_GET_SCRIPT = """
local version = redis.call('GET', KEYS[1]) or '0'
local value = redis.call('GET', ARGV[1] .. version .. ':' .. ARGV[2])
return {version, value or ''}
"""


async def initialize_cache() -> None:
    global _client
    candidate = Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        await candidate.ping()
    except RedisError as exc:
        logger.warning("redis_cache_unavailable", error=str(exc))
        await candidate.aclose()
        return
    _client = candidate
    logger.info("redis_cache_ready")


async def close_cache() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_json(suffix: str) -> tuple[Any | None, str | None]:
    if _client is None:
        return None, None
    try:
        version, value = await _client.eval(_GET_SCRIPT, 1, _VERSION_KEY, _CACHE_PREFIX, suffix)
        return (json.loads(value) if value else None), str(version)
    except (RedisError, ValueError, TypeError) as exc:
        logger.warning("redis_cache_read_failed", error=str(exc))
        return None, None


async def set_json(suffix: str, value: Any, ttl_seconds: int, version: str | None) -> None:
    if _client is None or version is None:
        return
    try:
        key = f"{_CACHE_PREFIX}{version}:{suffix}"
        await _client.set(key, json.dumps(value, separators=(",", ":")), ex=ttl_seconds)
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("redis_cache_write_failed", error=str(exc))


async def invalidate_vehicle_cache() -> None:
    if _client is None:
        return
    try:
        await _client.incr(_VERSION_KEY)
    except RedisError as exc:
        logger.warning("redis_cache_invalidation_failed", error=str(exc))


def mark_vehicle_cache_dirty(session: AsyncSession) -> None:
    session.info["vehicle_cache_dirty"] = True


async def invalidate_session_cache(session: AsyncSession) -> None:
    if session.info.pop("vehicle_cache_dirty", False):
        await invalidate_vehicle_cache()