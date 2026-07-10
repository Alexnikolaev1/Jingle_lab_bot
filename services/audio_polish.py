"""Автоматическая студийная полировка после генерации."""

import logging

from config import settings
from services import ffmpeg_service

logger = logging.getLogger("jinglelab.audio_polish")


async def master_polish(input_path: str, duration: float) -> str:
    """
    Normalize + мягкие фейды на входе/выходе.
    Возвращает путь к обработанному файлу.
    """
    if not settings.AUTO_MASTER_POLISH:
        return input_path

    fade_in = min(settings.POLISH_FADE_IN_SECONDS, duration / 4)
    fade_out = min(settings.POLISH_FADE_OUT_SECONDS, duration / 4)

    try:
        actual = await ffmpeg_service.get_duration(input_path) or duration
        normalized = await ffmpeg_service.normalize(input_path)
        polished = await ffmpeg_service.fade(normalized, fade_in, fade_out, actual)
        compressed = await ffmpeg_service.light_compress(polished)
        return compressed
    except Exception:
        logger.exception("Master polish не удался, возвращаем исходник")
        return input_path
