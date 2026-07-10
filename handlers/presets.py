"""handlers/presets.py — Быстрые пресеты генерации."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from handlers.generate import _handle_request
from models.presets import PRESET_BY_ID
from texts import messages
from utils.callbacks import PresetCallback
from utils.keyboards import BTN_PRESETS, presets_keyboard

router = Router(name="presets")


@router.message(F.text == BTN_PRESETS)
async def show_presets(message: Message) -> None:
    await message.answer(messages.PRESETS_INTRO, reply_markup=presets_keyboard())


@router.callback_query(PresetCallback.filter())
async def cb_preset(callback: CallbackQuery, callback_data: PresetCallback) -> None:
    preset = PRESET_BY_ID.get(callback_data.preset_id)
    if preset is None:
        await callback.answer("Пресет не найден.", show_alert=True)
        return

    await callback.answer(f"{preset.emoji} {preset.title}")
    tip_line = f"\n\n💡 {preset.tip}" if preset.tip else ""
    await callback.message.answer(
        messages.PRESET_SELECTED.format(
            title=preset.title, prompt=preset.prompt, tip_line=tip_line
        )
    )
    await _handle_request(
        callback.message,
        callback.bot,
        preset.prompt,
        preset.kind,
        generation_prompt=preset.calibrated_prompt,
    )
