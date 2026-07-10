from models.enums import GenerationKind
from utils.prompt_parser import detect_kind, duration_for_kind, extract_duration


def test_extract_duration_from_text():
    assert extract_duration("10 секундный джингл", 5.0, 30.0) == 10.0
    assert extract_duration("без длительности", 8.0, 30.0) == 8.0


def test_extract_duration_clamped():
    assert extract_duration("99 сек", 5.0, 30.0) == 30.0
    assert extract_duration("0 сек", 5.0, 30.0) == 1.0


def test_duration_for_music_allows_extended():
    text = "60 секундный эпичный джингл"
    duration = duration_for_kind(text, GenerationKind.MUSIC)
    assert duration == 60.0


def test_detect_kind_logo():
    assert detect_kind("звуковой логотип для кофейни") == GenerationKind.LOGO


def test_detect_kind_sound():
    assert detect_kind("звук взрыва в пещере") == GenerationKind.SOUND


def test_detect_kind_music_default():
    assert detect_kind("энергичное интро для подкаста") == GenerationKind.MUSIC
