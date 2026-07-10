"""Скачивание файлов из Telegram Bot API во временную директорию."""

import logging
import os

from aiogram import Bot

from utils.helpers import new_tmp_path

logger = logging.getLogger("jinglelab.telegram_files")


async def download_telegram_file(bot: Bot, file_id: str, suffix: str = ".wav") -> str:
    """Скачивает file_id во временный файл и возвращает путь."""
    tg_file = await bot.get_file(file_id)
    if tg_file.file_path is None:
        raise FileNotFoundError(f"Telegram не вернул путь для file_id={file_id}")

    dest = new_tmp_path(suffix=suffix)
    await bot.download_file(tg_file.file_path, dest)
    if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
        raise FileNotFoundError(f"Пустой файл после скачивания: {file_id}")
    return dest
