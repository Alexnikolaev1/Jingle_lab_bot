"""Загрузка звука из библиотеки в рабочую сессию для постобработки."""

import logging

from aiogram import Bot

from services import audio_polish
from utils.cache import LastGeneration, session_cache
from utils.keyboards import result_keyboard
from utils.telegram_files import download_telegram_file

logger = logging.getLogger("jinglelab.library_loader")


async def activate_sound_for_editing(
    bot: Bot, user_id: int, sound: dict
) -> str | None:
    """
    Скачивает file_id во temp и ставит как активный файл.
    Возвращает путь или None при ошибке.
    """
    if not sound.get("file_id"):
        return None
    try:
        path = await download_telegram_file(bot, sound["file_id"])
        path = await audio_polish.master_polish(path, sound.get("duration") or 10.0)
        await session_cache.set_last(
            user_id,
            LastGeneration(
                file_path=path,
                prompt=sound["prompt"],
                model_used=sound.get("model_used", "library"),
                duration=sound.get("duration") or 0.0,
                kind=sound.get("kind", "music"),
                sound_id=sound.get("id", 0),
            ),
        )
        return path
    except Exception:
        logger.exception("Не удалось загрузить sound_id=%s", sound.get("id"))
        return None
