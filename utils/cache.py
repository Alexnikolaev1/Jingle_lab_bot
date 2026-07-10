"""
utils/cache.py — Сессия пользователя с опциональным Redis-бэкендом.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from typing import Optional

from utils.redis_client import get_redis, redis_delete, redis_get_json, redis_set_json

logger = logging.getLogger("jinglelab.session_cache")

_SESSION_TTL = 86400


@dataclass
class LastGeneration:
    file_path: str
    prompt: str
    model_used: str
    duration: float
    kind: str
    sound_id: int = 0
    improved_prompt: str = ""


@dataclass
class LastRequest:
    prompt: str
    kind: str


class SessionCache:
    def __init__(self) -> None:
        self._store: dict[int, LastGeneration] = {}
        self._previous: dict[int, LastGeneration] = {}
        self._requests: dict[int, LastRequest] = {}
        self._loaded_from_redis: set[int] = set()

    def _session_key(self, user_id: int) -> str:
        return f"jinglelab:session:{user_id}"

    async def _hydrate(self, user_id: int) -> None:
        if user_id in self._loaded_from_redis:
            return
        self._loaded_from_redis.add(user_id)
        data = await redis_get_json(self._session_key(user_id))
        if not data:
            return
        if data.get("last"):
            self._store[user_id] = LastGeneration(**data["last"])
        if data.get("previous"):
            self._previous[user_id] = LastGeneration(**data["previous"])
        if data.get("request"):
            self._requests[user_id] = LastRequest(**data["request"])

    async def _persist(self, user_id: int) -> None:
        if not await get_redis():
            return
        payload = {
            "last": asdict(self._store[user_id]) if user_id in self._store else None,
            "previous": asdict(self._previous[user_id])
            if user_id in self._previous
            else None,
            "request": asdict(self._requests[user_id])
            if user_id in self._requests
            else None,
        }
        await redis_set_json(self._session_key(user_id), payload, ttl=_SESSION_TTL)

    async def set_last(self, user_id: int, generation: LastGeneration) -> None:
        await self._hydrate(user_id)
        current = self._store.get(user_id)
        if (
            current is not None
            and current.file_path
            and os.path.isfile(current.file_path)
            and current.file_path != generation.file_path
        ):
            self._previous[user_id] = current
        self._store[user_id] = generation
        await self._persist(user_id)

    async def get_last(self, user_id: int) -> Optional[LastGeneration]:
        await self._hydrate(user_id)
        return self._store.get(user_id)

    async def get_previous(self, user_id: int) -> Optional[LastGeneration]:
        await self._hydrate(user_id)
        prev = self._previous.get(user_id)
        if prev is None or not prev.file_path or not os.path.isfile(prev.file_path):
            return None
        return prev

    async def set_last_request(self, user_id: int, prompt: str, kind: str) -> None:
        await self._hydrate(user_id)
        self._requests[user_id] = LastRequest(prompt=prompt, kind=kind)
        await self._persist(user_id)

    async def get_last_request(self, user_id: int) -> Optional[LastRequest]:
        await self._hydrate(user_id)
        return self._requests.get(user_id)

    async def clear(self, user_id: int) -> None:
        self._store.pop(user_id, None)
        self._previous.pop(user_id, None)
        self._requests.pop(user_id, None)
        self._loaded_from_redis.discard(user_id)
        await redis_delete(self._session_key(user_id))


session_cache = SessionCache()
