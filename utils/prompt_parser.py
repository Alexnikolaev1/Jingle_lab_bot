"""Разбор промтов: длительность и автоопределение типа генерации."""

import re

from config import settings
from models.enums import GenerationKind

_DURATION_PATTERN = re.compile(
    r"(\d{1,2})\s*(?:сек|секунд|s|sec)", re.IGNORECASE
)

_SOUND_KEYWORDS = (
    "звук", "эффект", "шум", "sfx", "foley", "удар", "взрыв", "шаги",
)
_LOGO_KEYWORDS = (
    "логотип", "бренд", "sound logo", "brand", "стинг", "sting", "джингл бренда",
)


def extract_duration(
    text: str, default: float, maximum: float
) -> float:
    match = _DURATION_PATTERN.search(text)
    if not match:
        return default
    value = float(match.group(1))
    return min(max(value, 1.0), maximum)


def duration_for_kind(text: str, kind: GenerationKind) -> float:
    if kind == GenerationKind.MUSIC:
        return extract_duration(
            text,
            settings.DEFAULT_MUSIC_DURATION_SECONDS,
            settings.MAX_EXTENDED_MUSIC_DURATION_SECONDS,
        )
    if kind == GenerationKind.LOGO:
        return extract_duration(
            text,
            settings.DEFAULT_LOGO_DURATION_SECONDS,
            settings.MAX_LOGO_DURATION_SECONDS,
        )
    return settings.MAX_SOUND_DURATION_SECONDS


def detect_kind(text: str) -> GenerationKind:
    text_lower = text.lower()
    if any(k in text_lower for k in _LOGO_KEYWORDS):
        return GenerationKind.LOGO
    if any(k in text_lower for k in _SOUND_KEYWORDS):
        return GenerationKind.SOUND
    return GenerationKind.MUSIC
