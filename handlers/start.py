"""handlers/start.py — /start, /help, приветствие."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import database as db
from texts import messages
from utils.keyboards import BTN_HELP, BTN_SETTINGS, main_menu, welcome_keyboard

logger = logging.getLogger("jinglelab.handlers.start")
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if await db.is_onboarding_done(message.from_user.id):
        await message.answer(messages.WELCOME, reply_markup=main_menu())
        return

    await message.answer(
        messages.WELCOME_NEW,
        reply_markup=welcome_keyboard(),
    )
    await message.answer(messages.WELCOME_MENU_HINT, reply_markup=main_menu())


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(messages.HELP)


@router.message(F.text == BTN_SETTINGS)
async def show_settings(message: Message) -> None:
    await message.answer(messages.settings_text())
