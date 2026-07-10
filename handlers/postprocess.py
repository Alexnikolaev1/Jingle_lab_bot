"""handlers/postprocess.py — Постобработка последнего сгенерированного аудио."""

import logging
import os

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from services import ffmpeg_service
from services.ffmpeg_service import FFmpegError
from utils.cache import LastGeneration, session_cache
from utils.callbacks import PostprocessCallback
from utils.keyboards import postprocess_keyboard
from texts import messages
from utils.helpers import truncate_text

logger = logging.getLogger("jinglelab.handlers.postprocess")
router = Router(name="postprocess")


async def _get_active(user_id: int) -> LastGeneration | None:
    last = await session_cache.get_last(user_id)
    if last is None or not last.file_path or not os.path.isfile(last.file_path):
        return None
    return last


async def _update_last(user_id: int, new_path: str, base: LastGeneration) -> None:
    await session_cache.set_last(
        user_id,
        LastGeneration(
            file_path=new_path,
            prompt=base.prompt,
            model_used=base.model_used,
            duration=base.duration,
            kind=base.kind,
            sound_id=base.sound_id,
            improved_prompt=base.improved_prompt,
        ),
    )


async def _send_processed(message: Message, path: str, caption: str) -> None:
    with open(path, "rb") as f:
        data = f.read()
    await message.answer_audio(
        audio=BufferedInputFile(data, filename=os.path.basename(path)),
        caption=caption,
        reply_markup=postprocess_keyboard(),
    )


async def _apply_normalize(message: Message, user_id: int, last: LastGeneration) -> None:
    new_path = await ffmpeg_service.normalize(last.file_path)
    await _update_last(user_id, new_path, last)
    await _send_processed(message, new_path, "📈 Громкость нормализована (EBU R128)")


async def _apply_format_mp3(message: Message, user_id: int, last: LastGeneration) -> None:
    new_path = await ffmpeg_service.convert_format(last.file_path, "mp3")
    await _update_last(user_id, new_path, last)
    await _send_processed(message, new_path, "🔁 Конвертировано в MP3 (320 кбит/с)")


async def _apply_format_ogg(message: Message, user_id: int, last: LastGeneration) -> None:
    new_path = await ffmpeg_service.convert_format(last.file_path, "ogg")
    await _update_last(user_id, new_path, last)
    with open(new_path, "rb") as f:
        data = f.read()
    await message.answer_voice(
        voice=BufferedInputFile(data, filename=os.path.basename(new_path)),
        caption="🎙 Готово как голосовое",
    )


async def _apply_trim(
    message: Message, user_id: int, last: LastGeneration, start: float, end: float
) -> None:
    new_path = await ffmpeg_service.trim(last.file_path, start, end)
    await _update_last(user_id, new_path, last)
    await _send_processed(message, new_path, f"✂️ Обрезано: {start:.1f}–{end:.1f} сек")


async def _apply_fade(
    message: Message, user_id: int, last: LastGeneration, fade_in: float, fade_out: float
) -> None:
    actual_duration = await ffmpeg_service.get_duration(last.file_path)
    new_path = await ffmpeg_service.fade(
        last.file_path, fade_in, fade_out, actual_duration or last.duration
    )
    await _update_last(user_id, new_path, last)
    await _send_processed(
        message, new_path, f"🎚 Фейд-ин {fade_in:.1f}с / фейд-аут {fade_out:.1f}с"
    )


@router.message(Command("trim"))
async def cmd_trim(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return

    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer("Использование: /trim НАЧАЛО КОНЕЦ, например: /trim 0 5")
        return

    try:
        start, end = float(args[0]), float(args[1])
    except ValueError:
        await message.answer("Начало и конец должны быть числами (в секундах).")
        return

    if start < 0 or end <= start:
        await message.answer("Конец должен быть больше начала, оба значения ≥ 0.")
        return

    try:
        await _apply_trim(message, user_id, last, start, end)
    except FFmpegError as exc:
        await message.answer(f"❌ Не удалось обрезать: {exc}")


@router.message(Command("fade"))
async def cmd_fade(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return

    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer(
            "Использование: /fade ВХОД ВЫХОД (в секундах), например: /fade 0.5 1.0"
        )
        return

    try:
        fade_in, fade_out = float(args[0]), float(args[1])
    except ValueError:
        await message.answer("Значения фейдов должны быть числами (в секундах).")
        return

    try:
        await _apply_fade(message, user_id, last, fade_in, fade_out)
    except FFmpegError as exc:
        await message.answer(f"❌ Не удалось применить фейды: {exc}")


@router.message(Command("normalize"))
async def cmd_normalize(message: Message) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return
    try:
        await _apply_normalize(message, user_id, last)
    except FFmpegError as exc:
        await message.answer(f"❌ Не удалось нормализовать громкость: {exc}")


@router.message(Command("format"))
async def cmd_format(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return

    target_format = (command.args or "").strip().lower()
    if target_format not in {"mp3", "ogg"}:
        await message.answer("Использование: /format mp3 или /format ogg")
        return

    try:
        if target_format == "ogg":
            await _apply_format_ogg(message, user_id, last)
        else:
            await _apply_format_mp3(message, user_id, last)
    except FFmpegError as exc:
        await message.answer(f"❌ Не удалось конвертировать: {exc}")


@router.message(Command("download"))
async def cmd_download(message: Message) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return

    with open(last.file_path, "rb") as f:
        data = f.read()
    filename = os.path.basename(last.file_path)
    await message.answer_document(
        document=BufferedInputFile(data, filename=filename),
        caption=f"📥 {truncate_text(last.prompt, 100)}",
    )


@router.message(Command("mix"))
async def cmd_mix(message: Message) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    previous = await session_cache.get_previous(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return
    if previous is None:
        await message.answer(messages.NO_PREVIOUS_FILE)
        return

    try:
        new_path = await ffmpeg_service.mix([previous.file_path, last.file_path])
    except FFmpegError as exc:
        await message.answer(f"❌ Не удалось смикшировать: {exc}")
        return

    await _update_last(user_id, new_path, last)
    await _send_processed(message, new_path, "🎛 Смикшировано с предыдущим результатом")


@router.message(Command("speed"))
async def cmd_speed(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await message.answer(messages.NO_ACTIVE_FILE)
        return

    arg = (command.args or "").strip().replace(",", ".")
    if not arg:
        await message.answer("Использование: /speed 1.25 (диапазон 0.5–2.0)")
        return

    try:
        speed = float(arg)
    except ValueError:
        await message.answer("Скорость должна быть числом, например: 1.25")
        return

    if not 0.5 <= speed <= 2.0:
        await message.answer("Скорость должна быть от 0.5 до 2.0.")
        return

    try:
        new_path = await ffmpeg_service.change_speed(last.file_path, speed)
    except FFmpegError as exc:
        await message.answer(f"❌ Не удалось изменить скорость: {exc}")
        return

    await _update_last(user_id, new_path, last)
    await _send_processed(message, new_path, f"⏩ Скорость: ×{speed:.2f}")


@router.callback_query(PostprocessCallback.filter())
async def cb_postprocess(
    callback: CallbackQuery, callback_data: PostprocessCallback
) -> None:
    user_id = callback.from_user.id
    last = await _get_active(user_id)
    if last is None:
        await callback.answer("Нет активного аудио.", show_alert=True)
        return

    action = callback_data.action
    target_message = callback.message

    try:
        if action == "normalize":
            await callback.answer("Нормализую…")
            await _apply_normalize(target_message, user_id, last)

        elif action == "format_mp3":
            await callback.answer("Конвертирую в MP3…")
            await _apply_format_mp3(target_message, user_id, last)

        elif action == "format_ogg":
            await callback.answer("Конвертирую в OGG…")
            await _apply_format_ogg(target_message, user_id, last)

        elif action == "trim":
            await callback.answer()
            await target_message.answer(
                "Отправь команду вида: /trim 0 5 — обрежет с 0 по 5 секунду."
            )

        elif action == "fade":
            await callback.answer()
            await target_message.answer(
                "Отправь команду вида: /fade 0.5 1.0 — фейд-ин 0.5с, фейд-аут 1.0с."
            )

        elif action == "trim_preset" and callback_data.value:
            start_s, end_s = callback_data.value.split(":")
            await callback.answer("Обрезаю…")
            await _apply_trim(
                target_message, user_id, last, float(start_s), float(end_s)
            )

        elif action == "fade_preset" and callback_data.value:
            fade_in_s, fade_out_s = callback_data.value.split(":")
            await callback.answer("Применяю фейды…")
            await _apply_fade(
                target_message, user_id, last, float(fade_in_s), float(fade_out_s)
            )

        elif action == "download":
            await callback.answer("Отправляю файл…")
            with open(last.file_path, "rb") as f:
                data = f.read()
            await target_message.answer_document(
                document=BufferedInputFile(
                    data, filename=os.path.basename(last.file_path)
                ),
                caption=f"📥 {truncate_text(last.prompt, 100)}",
            )

        elif action == "mix":
            previous = await session_cache.get_previous(user_id)
            if previous is None:
                await callback.answer("Нет предыдущего трека.", show_alert=True)
                return
            await callback.answer("Микширую…")
            new_path = await ffmpeg_service.mix(
                [previous.file_path, last.file_path]
            )
            await _update_last(user_id, new_path, last)
            await _send_processed(
                target_message, new_path, "🎛 Смикшировано с предыдущим результатом"
            )

    except FFmpegError as exc:
        await target_message.answer(f"❌ Ошибка: {exc}")
