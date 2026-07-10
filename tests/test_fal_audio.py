"""Тесты payload для fal.ai."""

from services.fal_audio_service import (
    _FALLBACK_PROVIDER_MODEL,
    _logo_payload,
    _music_payload,
    _resolve_fal_provider_model_id,
    _sound_payload,
)


def test_music_payload_uses_duration_and_wav():
    payload = _music_payload("test jingle", 12.0)
    assert payload["duration"] == 12.0
    assert payload["output_format"] == "wav"
    assert payload["prompt"] == "test jingle"


def test_sound_payload_prefix_and_cap():
    payload = _sound_payload("explosion", 15.0)
    assert payload["duration"] == 10.0
    assert "Sound effect" in payload["prompt"]
    assert "explosion" in payload["prompt"]


def test_logo_payload_short():
    payload = _logo_payload("warm logo", 2.0)
    assert payload["duration"] == 2.0
    assert "brand sound logo" in payload["prompt"]


def test_fallback_provider_model_id():
    assert _resolve_fal_provider_model_id() == _FALLBACK_PROVIDER_MODEL


def test_extract_audio_url_nested_response():
    from services.fal_audio_service import _extract_audio_url

    wrapped = {
        "response": {
            "audio": {"url": "https://example.com/audio.wav"},
        }
    }
    assert _extract_audio_url(wrapped) == "https://example.com/audio.wav"
