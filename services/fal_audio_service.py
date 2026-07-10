"""Генерация аудио через fal.ai (маршрутизация Hugging Face Inference Providers)."""

from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import aiohttp

from config import settings
from services.huggingface_service import HuggingFaceError, RateLimitError
from utils.http_client import get_http_session

logger = logging.getLogger("jinglelab.fal_audio")

_FAL_ROUTER_BASE = "https://router.huggingface.co/fal-ai"
_POLL_INTERVAL_SECONDS = 2.0
_FALLBACK_PROVIDER_MODEL = "fal-ai/stable-audio-3/medium/text-to-audio"


@lru_cache
def _resolve_fal_provider_model_id() -> str:
    """Hub model id → fal provider_id (из inferenceProviderMapping)."""
    try:
        from huggingface_hub import HfApi

        info = HfApi(token=settings.HF_API_KEY).model_info(
            settings.FAL_HUB_AUDIO_MODEL,
            expand=["inferenceProviderMapping"],
        )
        for mapping in info.inference_provider_mapping or []:
            if mapping.provider == "fal-ai" and mapping.task == "text-to-audio":
                logger.info(
                    "fal provider: %s → %s",
                    settings.FAL_HUB_AUDIO_MODEL,
                    mapping.provider_id,
                )
                return mapping.provider_id
    except Exception:
        logger.exception("Не удалось получить mapping с Hub, используем fallback")

    return _FALLBACK_PROVIDER_MODEL


def _base_payload(prompt: str, duration: float) -> dict[str, Any]:
    seconds = max(1, min(int(round(duration)), 30))
    return {
        "prompt": prompt,
        "duration": float(seconds),
        "num_inference_steps": 8,
        "guidance_scale": 1.0,
        "output_format": "wav",
    }


def _music_payload(prompt: str, duration: float) -> dict[str, Any]:
    return _base_payload(prompt, duration)


def _sound_payload(prompt: str, duration: float) -> dict[str, Any]:
    enriched = f"Sound effect, foley, isolated sound, no music: {prompt.strip()}"
    seconds = max(1, min(int(round(duration)), 10))
    return {
        "prompt": enriched,
        "duration": float(seconds),
        "num_inference_steps": 8,
        "guidance_scale": 1.0,
        "output_format": "wav",
    }


def _logo_payload(prompt: str, duration: float) -> dict[str, Any]:
    enriched = (
        f"{prompt.strip()}, short brand sound logo sting, punchy, memorable, "
        "no long musical development"
    )
    seconds = max(1, min(int(round(duration)), 5))
    return {
        "prompt": enriched,
        "duration": float(seconds),
        "num_inference_steps": 8,
        "guidance_scale": 1.0,
        "output_format": "wav",
    }


def _extract_audio_url(result: dict[str, Any]) -> str:
    for key in ("audio", "audio_file"):
        value = result.get(key)
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])
        if isinstance(value, str) and value.startswith("http"):
            return value
    raise HuggingFaceError(
        "fal.ai вернул ответ без URL аудио. Попробуйте другой промт."
    )


def _queue_urls(submit_url: str, response_url: str) -> tuple[str, str]:
    parsed_submit = urlparse(submit_url)
    base_url = (
        f"{parsed_submit.scheme}://{parsed_submit.netloc}/fal-ai"
        if parsed_submit.netloc == "router.huggingface.co"
        else f"{parsed_submit.scheme}://{parsed_submit.netloc}"
    )
    query_param = f"?{parsed_submit.query}" if parsed_submit.query else ""
    model_path = urlparse(response_url).path
    status_url = f"{base_url}{model_path}/status{query_param}"
    result_url = f"{base_url}{model_path}{query_param}"
    return status_url, result_url


async def _download_url(session: aiohttp.ClientSession, url: str) -> bytes:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise HuggingFaceError(
                f"Не удалось скачать аудио ({resp.status}): {body[:200]}"
            )
        return await resp.read()


async def generate_via_fal(payload: dict[str, Any]) -> bytes:
    """Отправляет задачу в fal.ai через HF Router и возвращает байты аудио."""
    model_id = await asyncio.to_thread(_resolve_fal_provider_model_id)
    submit_url = f"{_FAL_ROUTER_BASE}/{model_id}?_subdomain=queue"
    headers = {
        "Authorization": f"Bearer {settings.HF_API_KEY}",
        "Content-Type": "application/json",
    }
    session = get_http_session()
    timeout = aiohttp.ClientTimeout(total=settings.HF_REQUEST_TIMEOUT_SECONDS)

    logger.info("fal.ai %s — %s", model_id, payload.get("prompt", "")[:120])

    async with session.post(submit_url, json=payload, headers=headers, timeout=timeout) as resp:
        body_text = await resp.text()
        if resp.status == 429:
            raise RateLimitError(
                "Достигнут лимит Hugging Face Inference Providers. Попробуйте позже."
            )
        if resp.status in (401, 403):
            raise HuggingFaceError(
                "Нет доступа к Inference Providers. Создайте токен HF с правом "
                "«Make calls to Inference Providers» (не только Read) на "
                "huggingface.co/settings/tokens"
            )
        if resp.status >= 400:
            logger.error("fal submit %s: %s", resp.status, body_text[:500])
            if "Model not supported by provider" in body_text:
                raise HuggingFaceError(
                    "Модель не зарегистрирована на HF Inference Providers. "
                    f"Используйте FAL_HUB_AUDIO_MODEL={settings.FAL_HUB_AUDIO_MODEL}."
                )
            raise HuggingFaceError(
                f"fal.ai вернул ошибку {resp.status}: {body_text[:300]}"
            )
        try:
            queued = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise HuggingFaceError("Некорректный ответ fal.ai при постановке в очередь.") from exc

    response_url = queued.get("response_url")
    if not response_url:
        raise HuggingFaceError("fal.ai не вернул response_url для очереди.")

    status_url, result_url = _queue_urls(submit_url, response_url)
    deadline = asyncio.get_running_loop().time() + settings.HF_REQUEST_TIMEOUT_SECONDS

    while asyncio.get_running_loop().time() < deadline:
        async with session.get(status_url, headers=headers, timeout=timeout) as status_resp:
            status_body = await status_resp.json()
        status = status_body.get("status")
        if status == "COMPLETED":
            break
        if status in ("FAILED", "CANCELLED"):
            raise HuggingFaceError(f"fal.ai: генерация не удалась (status={status}).")
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    else:
        raise HuggingFaceError("Превышено время ожидания генерации на fal.ai.")

    async with session.get(result_url, headers=headers, timeout=timeout) as result_resp:
        if result_resp.status >= 400:
            body = await result_resp.text()
            raise HuggingFaceError(f"fal.ai result error {result_resp.status}: {body[:300]}")
        result_data = await result_resp.json()

    audio_url = _extract_audio_url(result_data)
    return await _download_url(session, audio_url)


async def generate_music(prompt: str, duration: float) -> bytes:
    return await generate_via_fal(_music_payload(prompt, duration))


async def generate_sound(prompt: str, duration: float = 10.0) -> bytes:
    return await generate_via_fal(_sound_payload(prompt, duration))


async def generate_logo(prompt: str, duration: float) -> bytes:
    return await generate_via_fal(_logo_payload(prompt, duration))
