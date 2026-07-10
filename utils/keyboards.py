"""
utils/keyboards.py — Клавиатуры интерфейса JINGLE LAB AI.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from models.presets import FEATURED_PRESETS, PRESETS
from utils.callbacks import (
    GenerationCallback,
    LibraryCallback,
    OnboardingCallback,
    PostprocessCallback,
    PresetCallback,
)

BTN_JINGLE = "🎼 Джингл"
BTN_SOUND = "🔊 Звук"
BTN_LOGO = "🏷️ Аудиологотип"
BTN_LIBRARY = "📚 Библиотека"
BTN_SETTINGS = "⚙️ Настройки"
BTN_HELP = "❓ Помощь"
BTN_PRESETS = "✨ Пресеты"
BTN_WIZARD = "🪄 Мастер"

MENU_BUTTONS = {
    BTN_JINGLE, BTN_SOUND, BTN_LOGO, BTN_LIBRARY,
    BTN_SETTINGS, BTN_HELP, BTN_PRESETS, BTN_WIZARD,
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_JINGLE), KeyboardButton(text=BTN_SOUND)],
            [KeyboardButton(text=BTN_LOGO), KeyboardButton(text=BTN_PRESETS)],
            [KeyboardButton(text=BTN_WIZARD), KeyboardButton(text=BTN_LIBRARY)],
            [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Опиши звук или выбери режим…",
    )


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎧 Пример",
                    callback_data=OnboardingCallback(action="demo").pack(),
                ),
                InlineKeyboardButton(
                    text="🚀 Тур",
                    callback_data=OnboardingCallback(action="tour").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✨ Пресеты",
                    callback_data=OnboardingCallback(action="presets").pack(),
                ),
                InlineKeyboardButton(
                    text="⏭ Пропустить",
                    callback_data=OnboardingCallback(action="skip").pack(),
                ),
            ],
        ]
    )


def postprocess_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_postprocess_rows())


def result_keyboard(sound_id: int = 0) -> InlineKeyboardMarkup:
    rows = _postprocess_rows()
    rows.append(
        [
            InlineKeyboardButton(
                text="🔄 Ещё варианты",
                callback_data=GenerationCallback(action="regenerate").pack(),
            ),
        ]
    )
    if sound_id:
        rows.append(
            [
                InlineKeyboardButton(
                    text="👍",
                    callback_data=GenerationCallback(
                        action="rate", sound_id=sound_id, rating=1
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="👎",
                    callback_data=GenerationCallback(
                        action="rate", sound_id=sound_id, rating=-1
                    ).pack(),
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def variant_pick_keyboard(batch_id: str, labels: list[str]) -> InlineKeyboardMarkup:
    pick_row = [
        InlineKeyboardButton(
            text=f"✅ {label}",
            callback_data=GenerationCallback(
                action="pick", batch_id=batch_id, label=label
            ).pack(),
        )
        for label in labels
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            pick_row,
            [
                InlineKeyboardButton(
                    text="🔄 Другие варианты",
                    callback_data=GenerationCallback(action="regenerate").pack(),
                )
            ],
        ]
    )


def _preset_button(preset) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"{preset.emoji} {preset.title}",
        callback_data=PresetCallback(preset_id=preset.id).pack(),
    )


def _append_preset_rows(
    rows: list[list[InlineKeyboardButton]], presets: tuple
) -> None:
    row: list[InlineKeyboardButton] = []
    for preset in presets:
        row.append(_preset_button(preset))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)


def presets_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    featured_ids = {p.id for p in FEATURED_PRESETS}
    _append_preset_rows(rows, FEATURED_PRESETS)
    rest = tuple(p for p in PRESETS if p.id not in featured_ids)
    if rest:
        _append_preset_rows(rows, rest)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _postprocess_rows() -> list[list[InlineKeyboardButton]]:
    return [
            [
                InlineKeyboardButton(
                    text="✂️ Обрезать",
                    callback_data=PostprocessCallback(action="trim").pack(),
                ),
                InlineKeyboardButton(
                    text="🎚 Фейды",
                    callback_data=PostprocessCallback(action="fade").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📈 Нормализовать",
                    callback_data=PostprocessCallback(action="normalize").pack(),
                ),
                InlineKeyboardButton(
                    text="🔁 В MP3",
                    callback_data=PostprocessCallback(action="format_mp3").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎙 Как голосовое (OGG)",
                    callback_data=PostprocessCallback(action="format_ogg").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📥 Скачать",
                    callback_data=PostprocessCallback(action="download").pack(),
                ),
                InlineKeyboardButton(
                    text="🎛 Mix",
                    callback_data=PostprocessCallback(action="mix").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✂️ 0–5 сек",
                    callback_data=PostprocessCallback(
                        action="trim_preset", value="0-5"
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="🎚 Фейд 0.5/1",
                    callback_data=PostprocessCallback(
                        action="fade_preset", value="0.5-1.0"
                    ).pack(),
                ),
            ],
    ]


def library_item_keyboard(sound_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ В редактирование",
                    callback_data=LibraryCallback(action="edit", sound_id=sound_id).pack(),
                ),
                InlineKeyboardButton(
                    text="📤 Отправить",
                    callback_data=LibraryCallback(action="send", sound_id=sound_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=LibraryCallback(action="del", sound_id=sound_id).pack(),
                ),
            ],
        ]
    )


def library_pagination_keyboard(page: int, has_next: bool) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=LibraryCallback(action="page", page=page - 1).pack(),
            )
        )
    if has_next:
        buttons.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=LibraryCallback(action="page", page=page + 1).pack(),
            )
        )
    if not buttons:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(inline_keyboard=[buttons])
