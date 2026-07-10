"""
utils/helpers.py — Мелкие вспомогательные функции, используемые в разных
частях бота (хэширование промтов, работа с временными файлами и т.д.).
"""

import hashlib
import os
import time
import uuid

from config import settings, TMP_FILE_TTL_SECONDS


def ensure_tmp_dir() -> None:
    """Создаёт директорию для временных файлов, если её ещё нет."""
    os.makedirs(settings.TMP_DIR, exist_ok=True)


def improve_cache_hash(prompt: str, kind: str) -> str:
    raw = f"improve::{kind}::{prompt.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_prompt(prompt: str, kind: str, duration: float | None = None) -> str:
    """
    Строит стабильный хэш для промта, чтобы использовать его как ключ кэша.
    kind — тип генерации (music/sound/logo), duration — длительность,
    т.к. один и тот же текст с разной длительностью — разные результаты.
    """
    raw = f"{kind}::{duration}::{prompt.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_tmp_path(suffix: str = ".wav") -> str:
    """Генерирует уникальный путь во временной директории."""
    ensure_tmp_dir()
    filename = f"{uuid.uuid4().hex}{suffix}"
    return os.path.join(settings.TMP_DIR, filename)


def cleanup_old_tmp_files(ttl_seconds: int = TMP_FILE_TTL_SECONDS) -> int:
    """
    Удаляет временные файлы старше ttl_seconds из TMP_DIR.
    Вызывается периодически планировщиком (см. bot.py).
    Возвращает количество удалённых файлов.
    """
    ensure_tmp_dir()
    removed = 0
    now = time.time()
    for name in os.listdir(settings.TMP_DIR):
        path = os.path.join(settings.TMP_DIR, name)
        try:
            if os.path.isfile(path) and (now - os.path.getmtime(path)) > ttl_seconds:
                os.remove(path)
                removed += 1
        except OSError:
            # Файл мог быть удалён параллельно — не критично
            continue
    return removed


def format_duration(seconds: float) -> str:
    """Человекочитаемое представление длительности: 7.5 -> '7.5 сек'."""
    if seconds is None:
        return "неизвестно"
    return f"{seconds:.1f} сек"


def truncate_text(text: str, max_len: int = 60) -> str:
    """Обрезает длинный текст для компактного отображения в списках/кнопках."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"
