"""Типизированные callback_data для инлайн-кнопок."""

from aiogram.filters.callback_data import CallbackData


class PostprocessCallback(CallbackData, prefix="pp"):
    action: str
    value: str = ""


class LibraryCallback(CallbackData, prefix="lib"):
    action: str
    sound_id: int = 0
    page: int = 0


class GenerationCallback(CallbackData, prefix="gen"):
    action: str  # pick | regenerate | rate
    batch_id: str = ""
    label: str = ""
    sound_id: int = 0
    rating: int = 0


class PresetCallback(CallbackData, prefix="preset"):
    preset_id: str


class OnboardingCallback(CallbackData, prefix="ob"):
    action: str  # demo | tour | presets | skip
