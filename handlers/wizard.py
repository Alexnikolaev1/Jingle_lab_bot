"""handlers/wizard.py — Пошаговый мастер создания джингла."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.generate import _handle_request
from models.enums import GenerationKind
from states.wizard import WizardStates
from texts import messages
from utils.filters import FreeTextFilter
from utils.keyboards import BTN_WIZARD

router = Router(name="wizard")


@router.message(F.text == BTN_WIZARD)
async def start_wizard(message: Message, state: FSMContext) -> None:
    await state.set_state(WizardStates.mood)
    await message.answer(messages.WIZARD_MOOD)


@router.message(WizardStates.mood, FreeTextFilter)
async def wizard_mood(message: Message, state: FSMContext) -> None:
    await state.update_data(mood=message.text.strip())
    await state.set_state(WizardStates.duration)
    await message.answer(messages.WIZARD_DURATION)


@router.message(WizardStates.duration, FreeTextFilter)
async def wizard_duration(message: Message, state: FSMContext) -> None:
    await state.update_data(duration=message.text.strip())
    await state.set_state(WizardStates.style)
    await message.answer(messages.WIZARD_STYLE)


@router.message(WizardStates.style, FreeTextFilter)
async def wizard_style(message: Message, state: FSMContext) -> None:
    await state.update_data(style=message.text.strip())
    data = await state.get_data()
    prompt = (
        f"{data['mood']} {data['duration']} {data['style']}, "
        "professional jingle for content creator"
    )
    await state.set_state(WizardStates.confirm)
    await state.update_data(prompt=prompt)
    await message.answer(messages.WIZARD_CONFIRM.format(prompt=prompt))


@router.message(WizardStates.confirm, F.text.in_({"✅ Да", "да", "yes", "Yes"}))
async def wizard_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    prompt = data.get("prompt", "")
    await state.clear()
    await _handle_request(message, message.bot, prompt, GenerationKind.MUSIC)


@router.message(WizardStates.confirm, F.text.in_({"❌ Нет", "нет", "no", "No"}))
async def wizard_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(messages.WIZARD_CANCELLED)


@router.message(WizardStates.confirm)
async def wizard_confirm_hint(message: Message) -> None:
    await message.answer("Напиши «✅ Да» для генерации или «❌ Нет» для отмены.")
