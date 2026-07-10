"""Тесты callback_data клавиатур."""

from utils.callbacks import PostprocessCallback
from utils.keyboards import result_keyboard


def test_result_keyboard_builds_without_pack_error():
    kb = result_keyboard(sound_id=0)
    assert len(kb.inline_keyboard) >= 5


def test_postprocess_preset_values_pack():
    trim = PostprocessCallback(action="trim_preset", value="0-5").pack()
    fade = PostprocessCallback(action="fade_preset", value="0.5-1.0").pack()
    assert PostprocessCallback.unpack(trim).value == "0-5"
    assert PostprocessCallback.unpack(fade).value == "0.5-1.0"
