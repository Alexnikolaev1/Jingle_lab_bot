"""Планирование сегментов для длинных музыкальных генераций."""

from config import settings


def plan_music_segments(
    total_duration: float,
    segment_max: float | None = None,
) -> list[float]:
    """
    Разбивает запрошенную длительность на сегменты ≤ segment_max секунд.
    Например: 65 сек при max=30 → [30, 30, 5].
    """
    segment_max = segment_max or settings.MAX_MUSIC_DURATION_SECONDS
    if total_duration <= segment_max:
        return [total_duration]

    segments: list[float] = []
    remaining = total_duration
    while remaining > 0:
        chunk = min(remaining, segment_max)
        segments.append(chunk)
        remaining -= chunk
    return segments


def segment_prompt(base_prompt: str, index: int, total: int) -> str:
    """Вариация промта для продолжения длинного трека."""
    if total <= 1:
        return base_prompt
    if index == 0:
        return f"{base_prompt}, opening section, establish theme"
    if index == total - 1:
        return f"{base_prompt}, final section, natural ending, resolve"
    return f"{base_prompt}, continuation part {index + 1}, seamless flow, same style"
