"""Отслеживание онбординга и пост-генерационные подсказки."""

from __future__ import annotations

import logging

from aiogram.types import Message

logger = logging.getLogger("jinglelab.onboarding")

_pending: dict[int, str] = {}


def set_pending(user_id: int, stage: str) -> None:
    _pending[user_id] = stage


def pop_pending(user_id: int) -> str | None:
    return _pending.pop(user_id, None)


async def send_followup(message: Message, user_id: int) -> None:
    import database as db
    from texts import messages

    stage = pop_pending(user_id)
    if stage is None:
        return

    if stage in ("demo", "tour"):
        await message.answer(messages.ONBOARDING_AFTER_DEMO)
        if stage == "tour":
            await message.answer(messages.ONBOARDING_TOUR_STEP_3)
        await db.set_onboarding_done(user_id)
