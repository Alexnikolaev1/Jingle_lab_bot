"""Общие фикстуры для тестов."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Изолированное окружение: temp DB/TMP и тестовые токены."""
    db_path = tmp_path / "test.db"
    tmp_dir = tmp_path / "jinglelab_tmp"
    tmp_dir.mkdir()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:telegram_token")
    monkeypatch.setenv("HF_API_KEY", "hf_test_key")
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("TMP_DIR", str(tmp_dir))
    monkeypatch.setenv("WEBHOOK_HOST", "")

    import config

    config.get_settings.cache_clear()

    yield tmp_path

    config.get_settings.cache_clear()
