"""Тесты payload для fal.ai."""

from services.fal_audio_service import _logo_payload, _music_payload, _sound_payload


def test_music_payload_caps_duration():
    payload = _music_payload("test jingle", 45.0)
    assert payload["seconds_total"] == 30
    assert "prompt" in payload


def test_sound_payload_duration():
    payload = _sound_payload("explosion", 10.0)
    assert payload == {"prompt": "explosion", "duration": 10}


def test_logo_payload_short():
    payload = _logo_payload("warm logo", 2.0)
    assert payload["seconds_total"] == 2
    assert "brand sound logo" in payload["prompt"]
