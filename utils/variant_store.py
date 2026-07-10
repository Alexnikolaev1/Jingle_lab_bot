"""Хранилище вариантов генерации (A/B/C) — Redis или in-memory."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import asdict, dataclass

from utils.redis_client import get_redis, redis_delete, redis_get_json, redis_set_json

logger = logging.getLogger("jinglelab.variant_store")

_memory: dict[str, dict] = {}


@dataclass
class AudioVariant:
    label: str
    file_path: str
    prompt: str
    kind: str
    duration: float
    model_used: str
    improved_prompt: str = ""


@dataclass
class VariantBatch:
    batch_id: str
    user_id: int
    original_prompt: str
    kind: str
    variants: list[AudioVariant]


def _batch_key(user_id: int, batch_id: str) -> str:
    return f"jinglelab:variants:{user_id}:{batch_id}"


async def create_batch(
    user_id: int,
    original_prompt: str,
    kind: str,
    variants: list[AudioVariant],
) -> VariantBatch:
    batch_id = uuid.uuid4().hex[:10]
    payload = {
        "batch_id": batch_id,
        "user_id": user_id,
        "original_prompt": original_prompt,
        "kind": kind,
        "variants": [asdict(v) for v in variants],
    }
    key = _batch_key(user_id, batch_id)
    if await get_redis():
        await redis_set_json(key, payload)
    else:
        _memory[key] = payload

    return VariantBatch(
        batch_id=batch_id,
        user_id=user_id,
        original_prompt=original_prompt,
        kind=kind,
        variants=variants,
    )


async def get_batch(user_id: int, batch_id: str) -> VariantBatch | None:
    key = _batch_key(user_id, batch_id)
    data = await redis_get_json(key)
    if data is None:
        data = _memory.get(key)
    if not data:
        return None

    variants = [AudioVariant(**v) for v in data["variants"]]
    return VariantBatch(
        batch_id=data["batch_id"],
        user_id=data["user_id"],
        original_prompt=data["original_prompt"],
        kind=data["kind"],
        variants=variants,
    )


async def delete_batch(user_id: int, batch_id: str, keep_label: str | None = None) -> None:
    batch = await get_batch(user_id, batch_id)
    if batch is None:
        return

    for variant in batch.variants:
        if keep_label and variant.label == keep_label:
            continue
        try:
            if variant.file_path and os.path.isfile(variant.file_path):
                os.remove(variant.file_path)
        except OSError:
            pass

    key = _batch_key(user_id, batch_id)
    await redis_delete(key)
    _memory.pop(key, None)


async def pick_variant(user_id: int, batch_id: str, label: str) -> AudioVariant | None:
    batch = await get_batch(user_id, batch_id)
    if batch is None:
        return None
    chosen = next((v for v in batch.variants if v.label == label), None)
    if chosen is None:
        return None
    await delete_batch(user_id, batch_id, keep_label=label)
    return chosen
