from utils.helpers import hash_prompt, truncate_text


def test_hash_prompt_stable():
    h1 = hash_prompt("Hello", "music", 10.0)
    h2 = hash_prompt("hello", "music", 10.0)
    h3 = hash_prompt("Hello", "sound", 10.0)
    assert h1 == h2
    assert h1 != h3


def test_truncate_text():
    assert truncate_text("short", 10) == "short"
    assert truncate_text("a" * 20, 10).endswith("…")
    assert len(truncate_text("a" * 20, 10)) == 10
