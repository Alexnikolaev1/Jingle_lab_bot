import pytest

import database as db


@pytest.mark.asyncio
async def test_feedback_saved():
    await db.init_db()
    await db.ensure_user(7, "rater")
    sid = await db.save_sound(7, "p", "f", 1.0, "m", "music")
    await db.save_feedback(7, sid, 1)
    # no exception = success
