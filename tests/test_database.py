import pytest

import database as db


@pytest.mark.asyncio
async def test_user_and_sound_lifecycle():
    await db.init_db()
    await db.ensure_user(42, "tester")

    sound_id = await db.save_sound(
        user_id=42,
        prompt="test jingle",
        file_id="file123",
        duration=10.0,
        model_used="musicgen-small",
        kind="music",
    )
    assert sound_id > 0

    sounds = await db.get_user_sounds(42, limit=10)
    assert len(sounds) == 1
    assert sounds[0]["prompt"] == "test jingle"

    found = await db.get_sound_by_id(sound_id, 42)
    assert found is not None
    assert found["file_id"] == "file123"

    stats = await db.get_user_stats(42)
    assert stats["total"] == 1
    assert stats["by_kind"]["music"] == 1

    deleted = await db.delete_sound(sound_id, 42)
    assert deleted is True
    assert await db.count_user_sounds(42) == 0


@pytest.mark.asyncio
async def test_onboarding_flag():
    await db.init_db()
    user_id = 880_001
    await db.ensure_user(user_id, "newbie")
    await db.set_onboarding_done(user_id)
    assert await db.is_onboarding_done(user_id)


@pytest.mark.asyncio
async def test_cache_roundtrip():
    await db.init_db()
    await db.cache_set("hash123", "cached_file_id")
    assert await db.cache_get("hash123") == "cached_file_id"
    assert await db.cache_get("missing") is None
