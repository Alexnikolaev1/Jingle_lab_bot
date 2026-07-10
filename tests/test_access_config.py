"""Тесты ALLOWED_USER_IDS."""

import pytest
from pydantic import ValidationError

from config import Settings


def test_allowed_user_ids_empty_means_open_access():
    s = Settings(
        TELEGRAM_BOT_TOKEN="test:token",
        HF_API_KEY="hf_test",
        ALLOWED_USER_IDS="",
    )
    assert s.allowed_user_ids == frozenset()
    assert not s.access_restricted


def test_allowed_user_ids_parsed():
    s = Settings(
        TELEGRAM_BOT_TOKEN="test:token",
        HF_API_KEY="hf_test",
        ALLOWED_USER_IDS=" 123, 456 ,789 ",
    )
    assert s.allowed_user_ids == frozenset({123, 456, 789})
    assert s.access_restricted


def test_allowed_user_ids_invalid_raises():
    with pytest.raises(ValidationError):
        Settings(
            TELEGRAM_BOT_TOKEN="test:token",
            HF_API_KEY="hf_test",
            ALLOWED_USER_IDS="123,abc",
        )
