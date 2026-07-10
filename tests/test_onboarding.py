"""Тесты онбординга."""

import pytest

from utils.onboarding import pop_pending, send_followup, set_pending


@pytest.mark.asyncio
async def test_pending_stage_roundtrip():
    set_pending(1001, "demo")
    assert pop_pending(1001) == "demo"
    assert pop_pending(1001) is None


@pytest.mark.asyncio
async def test_send_followup_marks_onboarding_done(monkeypatch):
    import database as db

    await db.init_db()
    user_id = 880_002
    await db.ensure_user(user_id, "onboard_test")

    sent: list[str] = []

    class FakeMessage:
        async def answer(self, text: str) -> None:
            sent.append(text)

    set_pending(user_id, "tour")
    await send_followup(FakeMessage(), user_id)

    assert len(sent) == 2
    assert await db.is_onboarding_done(user_id)
    assert pop_pending(user_id) is None
