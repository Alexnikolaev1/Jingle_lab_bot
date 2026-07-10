"""handlers/onboarding.py — Демо, тур, первый запуск."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from handlers.generate import _handle_request
from models.presets import DEMO_PRESET_ID, PRESET_BY_ID
from texts import messages
from utils.callbacks import OnboardingCallback
from utils.keyboards import presets_keyboard
from utils.onboarding import set_pending

logger = logging.getLogger("jinglelab.handlers.onboarding")
router = Router(name="onboarding")


async def _run_demo(message: Message, stage: str) -> None:
    preset = PRESET_BY_ID[DEMO_PRESET_ID]
    set_pending(message.from_user.id, stage)
    await message.answer(messages.DEMO_INTRO.format(title=preset.title))
    await _handle_request(
        message,
        message.bot,
        preset.prompt,
        preset.kind,
        generation_prompt=preset.calibrated_prompt,
        variant_count=1,
        skip_cache=True,
    )


@router.callback_query(OnboardingCallback.filter(F.action == "demo"))
async def cb_demo(callback: CallbackQuery) -> None:
    await callback.answer()
    await _run_demo(callback.message, "demo")


@router.callback_query(OnboardingCallback.filter(F.action == "tour"))
async def cb_tour(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(messages.ONBOARDING_TOUR_INTRO)
    await _run_demo(callback.message, "tour")


@router.callback_query(OnboardingCallback.filter(F.action == "presets"))
async def cb_show_presets(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        messages.PRESETS_INTRO, reply_markup=presets_keyboard()
    )


@router.callback_query(OnboardingCallback.filter(F.action == "skip"))
async def cb_skip(callback: CallbackQuery) -> None:
    await callback.answer("Ок!")
    await db.set_onboarding_done(callback.from_user.id)
    await callback.message.answer(messages.ONBOARDING_SKIPPED)


@router.message(Command("demo"))
async def cmd_demo(message: Message) -> None:
    await _run_demo(message, "demo")
