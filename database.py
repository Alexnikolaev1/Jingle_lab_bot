"""
database.py — Слой работы с SQLite для JINGLE LAB AI.

Блокирующие вызовы оборачиваются в asyncio.to_thread(), чтобы не блокировать
event loop aiogram.
"""

import asyncio
import sqlite3
from datetime import UTC, datetime
from typing import Any, Optional

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    onboarding_done INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sounds (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    prompt       TEXT NOT NULL,
    file_id      TEXT,
    duration     REAL,
    model_used   TEXT,
    kind         TEXT DEFAULT 'music',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS cache (
    prompt_hash  TEXT PRIMARY KEY,
    file_id      TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sounds_user_id ON sounds(user_id);
CREATE INDEX IF NOT EXISTS idx_sounds_created_at ON sounds(created_at DESC);

CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    sound_id    INTEGER,
    rating      INTEGER NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_sound ON feedback(sound_id);

CREATE TABLE IF NOT EXISTS prompt_cache (
    prompt_hash  TEXT PRIMARY KEY,
    improved     TEXT NOT NULL,
    kind         TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _init_db_sync() -> None:
    conn = _get_connection()
    try:
        conn.executescript(SCHEMA)
        _migrate_sync(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate_sync(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "onboarding_done" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN onboarding_done INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute("UPDATE users SET onboarding_done = 1")


async def init_db() -> None:
    await asyncio.to_thread(_init_db_sync)


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------
def _ensure_user_sync(user_id: int, username: Optional[str]) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, created_at) "
            "VALUES (?, ?, ?)",
            (user_id, username, datetime.now(UTC).isoformat()),
        )
        conn.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id),
        )
        conn.commit()
    finally:
        conn.close()


async def ensure_user(user_id: int, username: Optional[str]) -> None:
    await asyncio.to_thread(_ensure_user_sync, user_id, username)


def _is_onboarding_done_sync(user_id: int) -> bool:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT onboarding_done FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row["onboarding_done"])
    finally:
        conn.close()


async def is_onboarding_done(user_id: int) -> bool:
    return await asyncio.to_thread(_is_onboarding_done_sync, user_id)


def _set_onboarding_done_sync(user_id: int) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE users SET onboarding_done = 1 WHERE user_id = ?", (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


async def set_onboarding_done(user_id: int) -> None:
    await asyncio.to_thread(_set_onboarding_done_sync, user_id)


# ---------------------------------------------------------------------------
# Звуки
# ---------------------------------------------------------------------------
def _save_sound_sync(
    user_id: int,
    prompt: str,
    file_id: str,
    duration: float,
    model_used: str,
    kind: str,
) -> int:
    conn = _get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO sounds (user_id, prompt, file_id, duration, model_used, kind) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, prompt, file_id, duration, model_used, kind),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


async def save_sound(
    user_id: int,
    prompt: str,
    file_id: str,
    duration: float,
    model_used: str,
    kind: str = "music",
) -> int:
    return await asyncio.to_thread(
        _save_sound_sync, user_id, prompt, file_id, duration, model_used, kind
    )


def _get_user_sounds_sync(user_id: int, limit: int, offset: int) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT id, prompt, file_id, duration, model_used, kind, created_at "
            "FROM sounds WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


async def get_user_sounds(
    user_id: int, limit: int = 10, offset: int = 0
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_get_user_sounds_sync, user_id, limit, offset)


def _get_sound_by_id_sync(sound_id: int, user_id: int) -> Optional[dict[str, Any]]:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, prompt, file_id, duration, model_used, kind, created_at "
            "FROM sounds WHERE id = ? AND user_id = ?",
            (sound_id, user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


async def get_sound_by_id(sound_id: int, user_id: int) -> Optional[dict[str, Any]]:
    return await asyncio.to_thread(_get_sound_by_id_sync, sound_id, user_id)


def _count_user_sounds_sync(user_id: int) -> int:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sounds WHERE user_id = ?", (user_id,)
        ).fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        conn.close()


async def count_user_sounds(user_id: int) -> int:
    return await asyncio.to_thread(_count_user_sounds_sync, user_id)


def _get_user_stats_sync(user_id: int) -> dict[str, Any]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS cnt FROM sounds WHERE user_id = ? GROUP BY kind",
            (user_id,),
        ).fetchall()
        by_kind = {row["kind"]: row["cnt"] for row in rows}
        total = sum(by_kind.values())
        return {"total": total, "by_kind": by_kind}
    finally:
        conn.close()


async def get_user_stats(user_id: int) -> dict[str, Any]:
    return await asyncio.to_thread(_get_user_stats_sync, user_id)


def _delete_sound_sync(sound_id: int, user_id: int) -> bool:
    conn = _get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM sounds WHERE id = ? AND user_id = ?", (sound_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


async def delete_sound(sound_id: int, user_id: int) -> bool:
    return await asyncio.to_thread(_delete_sound_sync, sound_id, user_id)


# ---------------------------------------------------------------------------
# Кэш
# ---------------------------------------------------------------------------
def _cache_get_sync(prompt_hash: str) -> Optional[str]:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT file_id FROM cache WHERE prompt_hash = ?", (prompt_hash,)
        ).fetchone()
        return row["file_id"] if row else None
    finally:
        conn.close()


async def cache_get(prompt_hash: str) -> Optional[str]:
    return await asyncio.to_thread(_cache_get_sync, prompt_hash)


def _cache_set_sync(prompt_hash: str, file_id: str) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cache (prompt_hash, file_id, created_at) "
            "VALUES (?, ?, ?)",
            (prompt_hash, file_id, datetime.now(UTC).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


async def cache_set(prompt_hash: str, file_id: str) -> None:
    await asyncio.to_thread(_cache_set_sync, prompt_hash, file_id)


# ---------------------------------------------------------------------------
# Feedback & квоты
# ---------------------------------------------------------------------------
def _save_feedback_sync(user_id: int, sound_id: int | None, rating: int) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO feedback (user_id, sound_id, rating) VALUES (?, ?, ?)",
            (user_id, sound_id, rating),
        )
        conn.commit()
    finally:
        conn.close()


async def save_feedback(user_id: int, sound_id: int | None, rating: int) -> None:
    await asyncio.to_thread(_save_feedback_sync, user_id, sound_id, rating)


def _count_generations_today_sync(user_id: int) -> int:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sounds "
            "WHERE user_id = ? AND date(created_at) = date('now')",
            (user_id,),
        ).fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        conn.close()


async def count_generations_today(user_id: int) -> int:
    return await asyncio.to_thread(_count_generations_today_sync, user_id)


# ---------------------------------------------------------------------------
# Кэш улучшенных промтов (экономия Gemini)
# ---------------------------------------------------------------------------
def _prompt_cache_get_sync(prompt_hash: str) -> Optional[str]:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT improved FROM prompt_cache WHERE prompt_hash = ?", (prompt_hash,)
        ).fetchone()
        return row["improved"] if row else None
    finally:
        conn.close()


async def prompt_cache_get(prompt_hash: str) -> Optional[str]:
    return await asyncio.to_thread(_prompt_cache_get_sync, prompt_hash)


def _prompt_cache_set_sync(prompt_hash: str, improved: str, kind: str) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO prompt_cache (prompt_hash, improved, kind, created_at) "
            "VALUES (?, ?, ?, ?)",
            (prompt_hash, improved, kind, datetime.now(UTC).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


async def prompt_cache_set(prompt_hash: str, improved: str, kind: str) -> None:
    await asyncio.to_thread(_prompt_cache_set_sync, prompt_hash, improved, kind)


# ---------------------------------------------------------------------------
# Поиск в библиотеке
# ---------------------------------------------------------------------------
def _search_sounds_sync(
    user_id: int, query: str, limit: int = 10
) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        pattern = f"%{query.strip().lower()}%"
        rows = conn.execute(
            "SELECT id, prompt, file_id, duration, model_used, kind, created_at "
            "FROM sounds WHERE user_id = ? AND lower(prompt) LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, pattern, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


async def search_sounds(
    user_id: int, query: str, limit: int = 10
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_search_sounds_sync, user_id, query, limit)


