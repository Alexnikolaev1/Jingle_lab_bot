"""Локальное обогащение промтов без внешних API (когда Gemini выключен)."""

from models.enums import GenerationKind

# Частые русские слова → английские термины для MusicGen/AudioLDM
_RU_EN = {
    "энергичн": "energetic",
    "спокойн": "calm peaceful",
    "драматичн": "dramatic cinematic",
    "тёпл": "warm",
    "тепл": "warm",
    "уютн": "cozy",
    "эпичн": "epic orchestral",
    "лоу-фай": "lo-fi",
    "lofi": "lo-fi",
    "lo-fi": "lo-fi",
    "электрон": "electronic",
    "джаз": "jazz",
    "рок": "rock",
    "поп": "pop",
    "кино": "cinematic film",
    "подкаст": "podcast intro",
    "стрим": "stream broadcast",
    "игр": "game",
    "фэнтези": "fantasy",
    "маг": "magical",
    "взрыв": "explosion",
    "шаг": "footsteps",
    "дожд": "rain",
    "ветер": "wind",
    "лес": "forest",
    "город": "urban city",
    "склад": "warehouse",
    "эхо": "reverb echo",
    "быстр": "fast upbeat",
    "медлен": "slow tempo",
    "коротк": "short",
    "длинн": "long",
}

_KIND_SUFFIX = {
    GenerationKind.MUSIC: (
        "high quality studio production, clear mix, professional jingle, 44.1kHz"
    ),
    GenerationKind.SOUND: (
        "high fidelity foley, realistic texture, clean recording, no music"
    ),
    GenerationKind.LOGO: (
        "short sound logo, brand sting, punchy memorable, studio quality"
    ),
}

_VARIANT_LOCAL = (
    ", emphasize rhythm and percussion, driving groove",
    ", emphasize melody and harmony, emotional lift",
    ", emphasize atmosphere and space, cinematic depth",
)


def enrich_prompt(user_prompt: str, kind: GenerationKind) -> str:
    """Бесплатная альтернатива Gemini: ключевые слова + профессиональные суффиксы."""
    text = user_prompt.strip()
    lower = text.lower()
    extras: list[str] = []

    for ru_prefix, en in _RU_EN.items():
        if ru_prefix in lower:
            extras.append(en)

    parts = [text]
    if extras:
        parts.append(", ".join(dict.fromkeys(extras)))
    parts.append(_KIND_SUFFIX.get(kind, _KIND_SUFFIX[GenerationKind.MUSIC]))
    return ", ".join(parts)


def build_local_variants(base_prompt: str, count: int) -> list[str]:
    """Варианты A/B/C без дополнительных API-вызовов."""
    return [
        f"{base_prompt}{_VARIANT_LOCAL[i % len(_VARIANT_LOCAL)]}"
        for i in range(count)
    ]
