"""handlers/variants.py — Выбор варианта A/B/C, regenerate, рейтинг."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

import database as db
from models.enums import GenerationKind
from services.generation_service import generation_service
from texts import messages
from utils.callbacks import GenerationCallback
from utils.keyboards import result_keyboard
from utils.onboarding import send_followup
from utils.queue_service import generation_queue
from utils.variant_store import pick_variant

logger = logging.getLogger("jinglelab.handlers.variants")
router = Router(name="variants")


@router.callback_query(GenerationCallback.filter(F.action == "pick"))
async def cb_pick_variant(
    callback: CallbackQuery, callback_data: GenerationCallback, bot: Bot
) -> None:
    user_id = callback.from_user.id
    variant = await pick_variant(user_id, callback_data.batch_id, callback_data.label)
    if variant is None:
        await callback.answer("Вариант не найден.", show_alert=True)
        return

    await callback.answer(f"Выбран вариант {variant.label} ✅")
    kind = GenerationKind(variant.kind)
    sound_id = await generation_service.finalize_delivery(
        callback.message,
        variant.prompt,
        kind,
        variant.file_path,
        variant.duration,
        variant.model_used,
        variant.improved_prompt,
    )
    await callback.message.edit_reply_markup(reply_markup=result_keyboard(sound_id))
    await send_followup(callback.message, user_id)


@router.callback_query(GenerationCallback.filter(F.action == "regenerate"))
async def cb_regenerate(callback: CallbackQuery, bot: Bot) -> None:
    from handlers.generate import _do_generate
    from utils.cache import session_cache

    user_id = callback.from_user.id
    req = await session_cache.get_last_request(user_id)
    if req is None:
        await callback.answer("Нет запроса для повтора.", show_alert=True)
        return

    if generation_queue.is_user_busy(user_id):
        await callback.answer("Дождись текущей генерации.", show_alert=True)
        return

    await callback.answer("Генерирую новые варианты…")
    kind = GenerationKind(req.kind)
    await generation_queue.enqueue(
        user_id,
        lambda: _do_generate(callback.message, bot, req.prompt, kind),
    )


@router.callback_query(GenerationCallback.filter(F.action == "rate"))
async def cb_rate(callback: CallbackQuery, callback_data: GenerationCallback) -> None:
    user_id = callback.from_user.id
    rating = callback_data.rating
    if rating not in (1, -1):
        await callback.answer()
        return

    sound_id = callback_data.sound_id or None
    await db.save_feedback(user_id, sound_id, rating)
    emoji = "👍" if rating > 0 else "👎"
    await callback.answer(f"Спасибо за оценку {emoji}")
