import pytest

from models.enums import GenerationKind
from services.generation_service import GenerationService
from services.huggingface_service import GenerationResult
from utils.cache import LastGeneration, session_cache


@pytest.mark.asyncio
async def test_generate_short_music():
    from unittest.mock import AsyncMock, patch

    service = GenerationService()
    fake = GenerationResult(audio_bytes=b"wav", model_used="musicgen-small", duration=10.0)

    with (
        patch("services.generation_service.gemini_service.improve_prompt", new_callable=AsyncMock) as mock_gemini,
        patch("services.generation_service.huggingface_service.generate_music", new_callable=AsyncMock) as mock_hf,
    ):
        mock_gemini.return_value = "improved"
        mock_hf.return_value = fake

        result, duration, improved = await service.generate("test", GenerationKind.MUSIC)

    assert duration == 10.0
    assert result.audio_bytes == b"wav"
    assert improved == "improved"
    mock_hf.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_stitched_music(tmp_path):
    service = GenerationService()
    segment = GenerationResult(audio_bytes=b"seg", model_used="musicgen-small", duration=30.0)

    seg_paths: list[str] = []

    async def fake_concat(paths, crossfade):
        seg_paths.extend(paths)
        out = tmp_path / "final.wav"
        out.write_bytes(b"stitched")
        return str(out)

    from unittest.mock import AsyncMock, patch

    with (
        patch("services.generation_service.gemini_service.improve_prompt", new_callable=AsyncMock, return_value="improved"),
        patch("services.generation_service.huggingface_service.generate_music", new_callable=AsyncMock, return_value=segment),
        patch("services.generation_service.ffmpeg_service.concat_with_crossfade", side_effect=fake_concat),
        patch("services.generation_service.audio_polish.master_polish", side_effect=lambda p, d: p),
    ):
        counter = {"n": 0}

        def mock_tmp(suffix=".wav"):
            counter["n"] += 1
            return str(tmp_path / f"seg{counter['n']}{suffix}")

        with patch("services.generation_service.new_tmp_path", side_effect=mock_tmp):
            result, duration, _ = await service.generate(
                "60 секундный джингл", GenerationKind.MUSIC
            )

    assert duration == 60.0
    assert result.model_used == "musicgen-small-stitched"
    assert result.audio_bytes == b"stitched"
    assert len(seg_paths) == 2


@pytest.mark.asyncio
async def test_session_cache_keeps_previous(tmp_path):
    await session_cache.clear(1)
    f1 = tmp_path / "a.wav"
    f2 = tmp_path / "b.wav"
    f1.write_bytes(b"a")
    f2.write_bytes(b"b")

    await session_cache.set_last(
        1, LastGeneration(str(f1), "first", "m", 1.0, "music")
    )
    await session_cache.set_last(
        1, LastGeneration(str(f2), "second", "m", 2.0, "music")
    )

    prev = await session_cache.get_previous(1)
    assert prev is not None
    assert prev.prompt == "first"
    await session_cache.clear(1)
