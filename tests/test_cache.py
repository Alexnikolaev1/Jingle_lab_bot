import pytest

from utils.cache import LastGeneration, session_cache


@pytest.mark.asyncio
async def test_set_last_stores_previous(tmp_path):
    await session_cache.clear(99)
    p1 = tmp_path / "1.wav"
    p2 = tmp_path / "2.wav"
    p1.write_bytes(b"1")
    p2.write_bytes(b"2")

    await session_cache.set_last(
        99, LastGeneration(str(p1), "a", "m", 1.0, "music")
    )
    await session_cache.set_last(
        99, LastGeneration(str(p2), "b", "m", 2.0, "music")
    )

    last = await session_cache.get_last(99)
    prev = await session_cache.get_previous(99)
    assert last.prompt == "b"
    assert prev.prompt == "a"
    await session_cache.clear(99)
