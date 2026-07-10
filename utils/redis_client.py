"""Redis-клиент (опционально). Без REDIS_URL — in-memory fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from config import settings

logger = logging.getLogger("jinglelab.redis")

_redis: Any | None = None
_redis_checked = False


async def get_redis():
    """Возвращает redis.asyncio.Redis или None."""
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True

    if not settings.REDIS_URL:
        logger.info("REDIS_URL не задан — используется in-memory хранилище")
        return None

    try:
        from redis.asyncio import Redis

        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        logger.info("Подключено к Redis")
        return _redis
    except Exception:
        logger.exception("Redis недоступен — fallback на in-memory")
        _redis = None
        return None


async def close_redis() -> None:
    global _redis, _redis_checked
    if _redis is not None:
        await _redis.close()
    _redis = None
    _redis_checked = False


async def redis_get_json(key: str) -> Any | None:
    client = await get_redis()
    if client is None:
        return None
    raw = await client.get(key)
    if not raw:
        return None
    return json.loads(raw)


async def redis_set_json(key: str, value: Any, ttl: int = 86400) -> None:
    client = await get_redis()
    if client is None:
        return
    await client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)


async def redis_delete(key: str) -> None:
    client = await get_redis()
    if client is None:
        return
    await client.delete(key)
