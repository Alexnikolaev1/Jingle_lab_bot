"""handlers/generate.py — Генерация джинглов, звуков и аудиологотипов."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import database as db
from config import settings
from models.enums import GenerationKind
from services.generation_service import (
    CreditsExhaustedError,
    HuggingFaceError,
    ModelLoadingError,
    RateLimitError,
    generation_service,
)
from states import GenerationStates
from texts import messages
from utils.filters import FreeTextFilter
from utils.keyboards import BTN_JINGLE, BTN_LOGO, BTN_SOUND
from utils.onboarding import send_followup
from utils.prompt_parser import detect_kind
from utils.queue_service import generation_queue

logger = logging.getLogger("jinglelab.handlers.generate")
router = Router(name="generate")

_KIND_BY_BUTTON = {
    BTN_JINGLE: GenerationKind.MUSIC,
    BTN_SOUND: GenerationKind.SOUND,
    BTN_LOGO: GenerationKind.LOGO,
}


async def _check_quota(message: Message) -> bool:
    if settings.DAILY_GENERATION_LIMIT <= 0:
        return True
    count = await db.count_generations_today(message.from_user.id)
    if count >= settings.DAILY_GENERATION_LIMIT:
        await message.answer(
            messages.DAILY_LIMIT_REACHED.format(limit=settings.DAILY_GENERATION_LIMIT)
        )
        return False
    return True


async def _do_generate(
    message: Message,
    bot: Bot,
    prompt: str,
    kind: GenerationKind,
    *,
    generation_prompt: str | None = None,
    variant_count: int | None = None,
) -> None:
    user_id = message.from_user.id
    status_message = await message.answer(messages.GENERATING)

    async def on_progress(text: str) -> None:
        try:
            await status_message.edit_text(text)
        except Exception:
            pass

    try:
        if variant_count is None:
            remaining = (
                settings.DAILY_GENERATION_LIMIT - await db.count_generations_today(user_id)
                if settings.DAILY_GENERATION_LIMIT > 0
                else 99
            )
            variant_count = generation_service.effective_variant_count(max(remaining, 1))

        if await generation_service.generate_with_variants(
            message,
            prompt,
            kind,
            on_progress=on_progress,
            variant_count=variant_count,
            generation_prompt=generation_prompt,
        ):
            await status_message.delete()
            return

        result, duration, improved = await generation_service.generate(
            prompt,
            kind,
            on_progress=on_progress,
            variant_prompt=generation_prompt,
        )
        await generation_service.deliver_single(
            message, prompt, kind, result, duration, improved
        )
        await status_message.delete()
        await send_followup(message, user_id)

    except ModelLoadingError:
        await status_message.edit_text(messages.MODEL_LOADING)
    except RateLimitError:
        await status_message.edit_text(messages.RATE_LIMIT)
    except CreditsExhaustedError:
        await status_message.edit_text(messages.HF_CREDITS_EXHAUSTED)
    except HuggingFaceError as exc:
        logger.exception("Ошибка генерации для user_id=%s", user_id)
        await status_message.edit_text(messages.GENERATION_FAILED.format(error=exc))
    except Exception:
        logger.exception("Неожиданная ошибка генерации для user_id=%s", user_id)
        await status_message.edit_text(messages.UNEXPECTED_ERROR)


async def _handle_request(
    message: Message,
    bot: Bot,
    prompt: str,
    kind: GenerationKind,
    *,
    generation_prompt: str | None = None,
    variant_count: int | None = None,
    skip_cache: bool = False,
) -> None:
    prompt = prompt.strip()
    if not prompt:
        await message.answer(messages.EMPTY_PROMPT)
        return

    if not await _check_quota(message):
        return

    user_id = message.from_user.id

    if generation_queue.is_user_busy(user_id):
        await message.answer(messages.USER_BUSY)
        return

    if not skip_cache and await generation_service.try_cached(message, bot, prompt, kind):
        return

    position = await generation_queue.enqueue(
        user_id,
        lambda: _do_generate(
            message,
            bot,
            prompt,
            kind,
            generation_prompt=generation_prompt,
            variant_count=variant_count,
        ),
    )
    if position > 1:
        await message.answer(messages.QUEUE_POSITION.format(position=position))


@router.message(Command("jingle"))
async def cmd_jingle(message: Message, bot: Bot, command: CommandObject) -> None:
    await _handle_request(message, bot, command.args or "", GenerationKind.MUSIC)


@router.message(Command("sound"))
async def cmd_sound(message: Message, bot: Bot, command: CommandObject) -> None:
    await _handle_request(message, bot, command.args or "", GenerationKind.SOUND)


@router.message(Command("logo"))
async def cmd_logo(message: Message, bot: Bot, command: CommandObject) -> None:
    await _handle_request(message, bot, command.args or "", GenerationKind.LOGO)


@router.message(F.text.in_(_KIND_BY_BUTTON.keys()))
async def menu_select_kind(message: Message, state: FSMContext) -> None:
    kind = _KIND_BY_BUTTON[message.text]
    await state.set_state(GenerationStates.waiting_prompt)
    await state.update_data(kind=kind.value)
    await message.answer(messages.PROMPT_HINTS[kind.value])


@router.message(GenerationStates.waiting_prompt, FreeTextFilter)
async def fsm_prompt(message: Message, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    kind = GenerationKind(data.get("kind", GenerationKind.MUSIC.value))
    await state.clear()
    await _handle_request(message, bot, message.text, kind)


@router.message(FreeTextFilter)
async def free_text_request(message: Message, bot: Bot, state: FSMContext) -> None:
    current = await state.get_state()
    if current == GenerationStates.waiting_prompt:
        return
    kind = detect_kind(message.text)
    await _handle_request(message, bot, message.text, kind)
