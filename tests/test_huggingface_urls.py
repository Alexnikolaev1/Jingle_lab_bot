"""Тесты миграции URL Hugging Face Inference API."""

from services.huggingface_service import normalize_hf_model_url


def test_normalize_legacy_hf_url():
    legacy = (
        "https://api-inference.huggingface.co/models/facebook/musicgen-small"
    )
    expected = (
        "https://router.huggingface.co/hf-inference/models/facebook/musicgen-small"
    )
    assert normalize_hf_model_url(legacy) == expected


def test_router_url_unchanged():
    url = "https://router.huggingface.co/hf-inference/models/haoheliu/audioldm"
    assert normalize_hf_model_url(url) == url
