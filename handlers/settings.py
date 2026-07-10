"""handlers/settings.py — Настройки и служебные команды."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import database as db
from models.enums import GenerationKind
from texts import messages
from utils.cache import session_cache
from utils.helpers import truncate_text
from utils.keyboards import result_keyboard

logger = logging.getLogger("jinglelab.handlers.settings")
router = Router(name="settings")


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    await session_cache.clear(message.from_user.id)
    await message.answer(
        "🔄 Рабочая сессия сброшена. Активного файла для постобработки больше нет."
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    user_id = message.from_user.id
    stats = await db.get_user_stats(user_id)
    total = stats["total"]
    by_kind = stats["by_kind"]

    if total == 0:
        await message.answer("📊 У тебя пока нет сгенерированных звуков.")
        return

    lines = [f"📊 <b>Статистика</b>\n\nВсего генераций: <b>{total}</b>\n"]
    for kind in GenerationKind:
        count = by_kind.get(kind.value, 0)
        if count:
            lines.append(f"{kind.emoji} {kind.label}: {count}")

    await message.answer("\n".join(lines))


@router.message(Command("last"))
async def cmd_last(message: Message) -> None:
    last = await session_cache.get_last(message.from_user.id)
    if last is None or not last.file_path:
        await message.answer(messages.NO_ACTIVE_FILE)
        return

    try:
        from aiogram.types import BufferedInputFile

        with open(last.file_path, "rb") as f:
            data = f.read()
        await message.answer_audio(
            audio=BufferedInputFile(data, filename="last.wav"),
            caption=truncate_text(last.prompt, 200),
            reply_markup=result_keyboard(last.sound_id),
        )
    except OSError:
        await message.answer(messages.LAST_FILE_MISSING)
