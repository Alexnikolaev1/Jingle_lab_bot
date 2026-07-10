"""
services/huggingface_service.py — Клиент Hugging Face Inference API.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

from config import settings
from utils.http_client import get_http_session

logger = logging.getLogger("jinglelab.huggingface")

_HEADERS = {"Authorization": f"Bearer {settings.HF_API_KEY}"}
_semaphore = asyncio.Semaphore(settings.HF_MAX_CONCURRENT_REQUESTS)


class HuggingFaceError(Exception):
    """Ошибка при обращении к Hugging Face Inference API."""


class ModelLoadingError(HuggingFaceError):
    """Модель ещё загружается на стороне HF."""


class RateLimitError(HuggingFaceError):
    """Превышен лимит бесплатного тарифа Hugging Face."""


@dataclass
class GenerationResult:
    audio_bytes: bytes
    model_used: str
    duration: float


async def _post_to_hf(url: str, payload: dict) -> bytes:
    timeout = aiohttp.ClientTimeout(total=settings.HF_REQUEST_TIMEOUT_SECONDS)
    session = get_http_session()

    async with _semaphore:
        last_error: Optional[str] = None

        for attempt in range(1, settings.HF_MAX_RETRIES + 1):
            try:
                async with session.post(
                    url, json=payload, headers=_HEADERS, timeout=timeout
                ) as resp:
                    content_type = resp.headers.get("content-type", "")

                    if resp.status == 200 and "audio" in content_type:
                        return await resp.read()

                    if resp.status == 503:
                        body_text = await resp.text()
                        try:
                            body = json.loads(body_text)
                            wait_time = body.get(
                                "estimated_time", settings.HF_RETRY_DELAY_SECONDS
                            )
                        except (json.JSONDecodeError, TypeError):
                            wait_time = settings.HF_RETRY_DELAY_SECONDS
                        logger.info(
                            "HF модель загружается (%s/%s), ждём %.0f сек",
                            attempt,
                            settings.HF_MAX_RETRIES,
                            wait_time,
                        )
                        await asyncio.sleep(min(wait_time, 30))
                        last_error = "Модель загружается на сервере Hugging Face."
                        continue

                    if resp.status == 429:
                        logger.warning("HF: превышен лимит запросов (429)")
                        await asyncio.sleep(settings.HF_RETRY_DELAY_SECONDS)
                        last_error = "Превышен лимит бесплатных запросов Hugging Face."
                        continue

                    body_text = await resp.text()
                    logger.error("HF ошибка %s: %s", resp.status, body_text[:500])
                    raise HuggingFaceError(
                        f"Hugging Face вернул ошибку {resp.status}: {body_text[:300]}"
                    )

            except asyncio.TimeoutError:
                logger.warning(
                    "Таймаут HF (%s/%s)", attempt, settings.HF_MAX_RETRIES
                )
                last_error = "Превышено время ожидания ответа от Hugging Face."
                continue

        if last_error and "загружается" in last_error:
            raise ModelLoadingError(
                "Модель на Hugging Face всё ещё загружается. "
                "Попробуйте повторить запрос через минуту."
            )
        if last_error and "лимит" in last_error:
            raise RateLimitError(
                "Достигнут лимит бесплатных запросов Hugging Face. "
                "Попробуйте немного позже."
            )
        raise HuggingFaceError(last_error or "Неизвестная ошибка Hugging Face API.")


def _build_music_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    if len(prompt.split()) < 4:
        prompt = (
            f"{prompt}, high quality studio production, clear mix, professional jingle"
        )
    return prompt


async def generate_music(prompt: str, duration: float = 10.0) -> GenerationResult:
    enriched_prompt = _build_music_prompt(prompt)
    payload = {
        "inputs": enriched_prompt,
        "parameters": {
            "max_new_tokens": min(int(duration * 51.2), 1536),
            "duration": duration,
        },
    }
    logger.info("Генерация музыки: %s (%.1f сек)", enriched_prompt, duration)
    audio_bytes = await _post_to_hf(settings.HF_MUSICGEN_MODEL_URL, payload)
    return GenerationResult(
        audio_bytes=audio_bytes, model_used="musicgen-small", duration=duration
    )


async def generate_sound(prompt: str) -> GenerationResult:
    enriched_prompt = prompt.strip()
    payload = {"inputs": enriched_prompt}
    logger.info("Генерация звукового эффекта: %s", enriched_prompt)
    audio_bytes = await _post_to_hf(settings.HF_AUDIOLDM_MODEL_URL, payload)
    return GenerationResult(
        audio_bytes=audio_bytes, model_used="audioldm", duration=10.0
    )


async def generate_logo(prompt: str, duration: float = 2.0) -> GenerationResult:
    branded_prompt = (
        f"{prompt.strip()}, short sound logo, brand identity sound, "
        f"punchy, memorable, {duration:.1f} seconds sting"
    )
    payload = {
        "inputs": branded_prompt,
        "parameters": {
            "max_new_tokens": min(int(duration * 51.2), 256),
            "duration": duration,
        },
    }
    logger.info("Генерация аудиологотипа: %s (%.1f сек)", branded_prompt, duration)
    audio_bytes = await _post_to_hf(settings.HF_MUSICGEN_MODEL_URL, payload)
    return GenerationResult(
        audio_bytes=audio_bytes, model_used="musicgen-small-logo", duration=duration
    )
