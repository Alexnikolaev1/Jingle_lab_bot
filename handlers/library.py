"""handlers/library.py — Библиотека, поиск, редактирование."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import database as db
from config import settings
from models.enums import GenerationKind
from texts import messages
from utils.callbacks import LibraryCallback
from utils.helpers import format_duration, truncate_text
from utils.keyboards import BTN_LIBRARY, library_item_keyboard, library_pagination_keyboard, result_keyboard
from utils.library_loader import activate_sound_for_editing

logger = logging.getLogger("jinglelab.handlers.library")
router = Router(name="library")

PAGE_SIZE = settings.LIBRARY_PAGE_SIZE


async def _render_sound_item(message: Message, sound: dict) -> None:
    try:
        kind = GenerationKind(sound["kind"])
    except ValueError:
        kind = GenerationKind.MUSIC
    text = (
        f"{kind.emoji} {truncate_text(sound['prompt'], 100)}\n"
        f"⏱ {format_duration(sound['duration'])} · "
        f"🧠 {sound['model_used']} · "
        f"🕒 {sound['created_at']}"
    )
    await message.answer(text, reply_markup=library_item_keyboard(sound["id"]))


async def _render_library(message: Message, user_id: int, page: int = 0) -> None:
    offset = page * PAGE_SIZE
    sounds = await db.get_user_sounds(user_id, limit=PAGE_SIZE + 1, offset=offset)

    if not sounds:
        if page == 0:
            await message.answer(messages.LIBRARY_EMPTY)
        else:
            await message.answer(messages.LIBRARY_END)
        return

    has_next = len(sounds) > PAGE_SIZE
    sounds = sounds[:PAGE_SIZE]

    start = offset + 1
    end = offset + len(sounds)
    await message.answer(messages.LIBRARY_HEADER.format(start=start, end=end))

    for sound in sounds:
        await _render_sound_item(message, sound)

    pagination = library_pagination_keyboard(page, has_next)
    if pagination.inline_keyboard:
        await message.answer("Навигация:", reply_markup=pagination)


@router.message(Command("library"))
@router.message(F.text == BTN_LIBRARY)
async def cmd_library(message: Message) -> None:
    await _render_library(message, message.from_user.id)


@router.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer(messages.SEARCH_USAGE)
        return

    sounds = await db.search_sounds(message.from_user.id, query, limit=10)
    if not sounds:
        await message.answer(messages.SEARCH_EMPTY.format(query=query))
        return

    await message.answer(messages.SEARCH_RESULTS.format(query=query, count=len(sounds)))
    for sound in sounds:
        await _render_sound_item(message, sound)


@router.callback_query(LibraryCallback.filter(F.action == "page"))
async def cb_library_page(
    callback: CallbackQuery, callback_data: LibraryCallback
) -> None:
    await callback.answer()
    if callback.message:
        await _render_library(callback.message, callback.from_user.id, callback_data.page)


@router.callback_query(LibraryCallback.filter(F.action == "edit"))
async def cb_library_edit(
    callback: CallbackQuery, callback_data: LibraryCallback
) -> None:
    user_id = callback.from_user.id
    target = await db.get_sound_by_id(callback_data.sound_id, user_id)
    if target is None or not target["file_id"]:
        await callback.answer("Файл недоступен.", show_alert=True)
        return

    await callback.answer("Загружаю в редактор…")
    path = await activate_sound_for_editing(callback.bot, user_id, target)
    if path is None:
        await callback.message.answer(messages.LIBRARY_EDIT_FAILED)
        return

    await callback.message.answer(
        messages.LIBRARY_EDIT_READY.format(prompt=truncate_text(target["prompt"], 100)),
        reply_markup=result_keyboard(target["id"]),
    )


@router.callback_query(LibraryCallback.filter(F.action == "send"))
async def cb_library_send(
    callback: CallbackQuery, callback_data: LibraryCallback
) -> None:
    user_id = callback.from_user.id
    target = await db.get_sound_by_id(callback_data.sound_id, user_id)

    if target is None or not target["file_id"]:
        await callback.answer("Файл не найден.", show_alert=True)
        return

    await callback.answer("Отправляю…")
    try:
        await callback.message.answer_audio(
            audio=target["file_id"],
            caption=truncate_text(target["prompt"], 200),
        )
    except Exception:
        logger.exception("Не удалось повторно отправить sound_id=%s", callback_data.sound_id)
        await callback.message.answer(messages.LIBRARY_SEND_FAILED)


@router.callback_query(LibraryCallback.filter(F.action == "del"))
async def cb_library_delete(
    callback: CallbackQuery, callback_data: LibraryCallback
) -> None:
    user_id = callback.from_user.id
    deleted = await db.delete_sound(callback_data.sound_id, user_id)
    if deleted:
        await callback.answer("Удалено 🗑")
        await callback.message.edit_text("🗑 Запись удалена из библиотеки.")
    else:
        await callback.answer("Не удалось найти запись.", show_alert=True)
