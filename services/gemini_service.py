"""
services/gemini_service.py — Улучшение промтов (Gemini опционален, есть бесплатный fallback).
"""

import logging

import aiohttp

import database as db
from config import settings
from models.enums import GenerationKind
from utils.helpers import improve_cache_hash
from utils.http_client import get_http_session
from utils.prompt_enricher import build_local_variants, enrich_prompt

logger = logging.getLogger("jinglelab.gemini")

_INSTRUCTIONS = {
    GenerationKind.MUSIC: (
        "You are a professional music producer. Rewrite the user's request into "
        "a vivid English prompt for MusicGen. Add tempo (BPM), instrumentation, "
        "mood, genre. Under 60 words. Respond with ONLY the improved prompt in English."
    ),
    GenerationKind.SOUND: (
        "You are a Foley sound designer. Rewrite into a detailed English prompt "
        "for AudioLDM. Add texture, environment, dynamics. Under 60 words. "
        "Respond with ONLY the improved prompt in English."
    ),
    GenerationKind.LOGO: (
        "You are a sonic branding expert. Rewrite into an English prompt for a "
        "short 1-3 second audio logo. Emphasize memorability. Under 60 words. "
        "Respond with ONLY the improved prompt in English."
    ),
}


async def _call_gemini(system: str, user: str, temperature: float = 0.8) -> str | None:
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 150},
    }
    url = f"{settings.GEMINI_MODEL_URL}?key={settings.GEMINI_API_KEY}"
    timeout = aiohttp.ClientTimeout(total=20)

    session = get_http_session()
    async with session.post(url, json=payload, timeout=timeout) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.warning("Gemini вернул %s: %s", resp.status, text[:300])
            return None
        data = await resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        return parts[0].get("text", "").strip() or None


async def improve_prompt(
    user_prompt: str, kind: GenerationKind = GenerationKind.MUSIC
) -> str:
    cache_key = improve_cache_hash(user_prompt, kind.value)
    cached = await db.prompt_cache_get(cache_key)
    if cached:
        return cached

    improved: str
    if settings.GEMINI_ENABLED:
        try:
            result = await _call_gemini(
                _INSTRUCTIONS.get(kind, _INSTRUCTIONS[GenerationKind.MUSIC]),
                user_prompt,
            )
            improved = result if result else enrich_prompt(user_prompt, kind)
        except Exception as exc:
            logger.warning("Ошибка Gemini: %s — локальное обогащение", exc)
            improved = enrich_prompt(user_prompt, kind)
    else:
        improved = enrich_prompt(user_prompt, kind)

    await db.prompt_cache_set(cache_key, improved, kind.value)
    return improved


async def build_variant_prompts(
    user_prompt: str,
    kind: GenerationKind,
    count: int,
) -> list[str]:
    """A/B/C только локальными вариациями — без лишних вызовов Gemini."""
    base = await improve_prompt(user_prompt, kind)
    return build_local_variants(base, count)


async def translate_for_display(text: str) -> str:
    """Показываем промт как есть — перевод через Gemini отключён (экономия квоты)."""
    return text
