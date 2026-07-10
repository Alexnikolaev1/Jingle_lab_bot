"""
config.py — Центральная конфигурация JINGLE LAB AI.

Все чувствительные данные читаются из переменных окружения через Pydantic Settings.
"""

import secrets
import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    ALLOWED_USER_IDS: str = ""

    # Hugging Face
    HF_API_KEY: str
    HF_MUSICGEN_MODEL_URL: str = (
        "https://api-inference.huggingface.co/models/facebook/musicgen-small"
    )
    HF_AUDIOLDM_MODEL_URL: str = (
        "https://api-inference.huggingface.co/models/haoheliu/audioldm"
    )
    HF_REQUEST_TIMEOUT_SECONDS: int = 120
    HF_MAX_RETRIES: int = 5
    HF_RETRY_DELAY_SECONDS: int = 10
    HF_MAX_CONCURRENT_REQUESTS: int = 2

    # Gemini (опционально)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Webhook / сервер
    WEBHOOK_HOST: str = ""
    WEBHOOK_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    ENABLE_HEALTH_SERVER: bool = False

    # Файловая система
    TMP_DIR: str = Field(
        default_factory=lambda: str(Path(tempfile.gettempdir()) / "jinglelab")
    )
    DB_PATH: str = Field(
        default_factory=lambda: str(Path.cwd() / "jinglelab.db")
    )
    TMP_FILE_TTL_SECONDS: int = 1800

    # Лимиты генерации
    MAX_MUSIC_DURATION_SECONDS: float = 30.0
    MAX_EXTENDED_MUSIC_DURATION_SECONDS: float = 90.0
    MAX_SOUND_DURATION_SECONDS: float = 10.0
    MAX_LOGO_DURATION_SECONDS: float = 3.0
    DEFAULT_MUSIC_DURATION_SECONDS: float = 10.0
    DEFAULT_LOGO_DURATION_SECONDS: float = 2.0
    MUSIC_SEGMENT_CROSSFADE_SECONDS: float = 0.5

    # Антиспам
    THROTTLE_RATE_SECONDS: float = 1.0

    # Библиотека
    LIBRARY_PAGE_SIZE: int = 5

    # Redis / observability
    REDIS_URL: str = ""
    SENTRY_DSN: str = ""

    # Генерация
    GENERATION_VARIANTS: int = 3
    AUTO_MASTER_POLISH: bool = True
    POLISH_FADE_IN_SECONDS: float = 0.3
    POLISH_FADE_OUT_SECONDS: float = 0.5
    SHOW_IMPROVED_PROMPT: bool = True
    DAILY_GENERATION_LIMIT: int = 30

    @field_validator("TELEGRAM_BOT_TOKEN", "HF_API_KEY")
    @classmethod
    def _required_non_empty(cls, value: str, info) -> str:
        if not value or not value.strip():
            field = info.field_name
            hints = {
                "TELEGRAM_BOT_TOKEN": "Добавьте TELEGRAM_BOT_TOKEN в переменные окружения.",
                "HF_API_KEY": (
                    "Получите токен на https://huggingface.co/settings/tokens "
                    "и добавьте HF_API_KEY."
                ),
            }
            raise ValueError(hints.get(field, f"{field} обязателен."))
        return value.strip()

    @field_validator("ALLOWED_USER_IDS")
    @classmethod
    def _validate_allowed_user_ids(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        for part in value.split(","):
            part = part.strip()
            if part:
                int(part)
        return value

    @property
    def allowed_user_ids(self) -> frozenset[int]:
        if not self.ALLOWED_USER_IDS:
            return frozenset()
        return frozenset(
            int(part.strip())
            for part in self.ALLOWED_USER_IDS.split(",")
            if part.strip()
        )

    @property
    def access_restricted(self) -> bool:
        return bool(self.allowed_user_ids)

    @property
    def GEMINI_ENABLED(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def GEMINI_MODEL_URL(self) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.GEMINI_MODEL}:generateContent"
        )

    @property
    def WEBHOOK_PATH(self) -> str:
        return f"/webhook/{self.WEBHOOK_SECRET}"

    @property
    def WEBHOOK_URL(self) -> str:
        if not self.WEBHOOK_HOST:
            return ""
        host = self.WEBHOOK_HOST.rstrip("/")
        return f"{host}{self.WEBHOOK_PATH}"

    @property
    def USE_WEBHOOK(self) -> bool:
        return bool(self.WEBHOOK_HOST)


DISCLAIMER_TEXT = (
    "⚠️ JINGLE LAB AI генерирует музыку и звуки на основе открытых моделей. "
    "Вы получаете неограниченное право использовать их в своих проектах, "
    "но помните, что уникальность не гарантируется, и бот не несёт "
    "ответственности за совпадения с существующими произведениями."
)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Обратная совместимость для импортов вида `from config import X`
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
HF_API_KEY = settings.HF_API_KEY
HF_MUSICGEN_MODEL_URL = settings.HF_MUSICGEN_MODEL_URL
HF_AUDIOLDM_MODEL_URL = settings.HF_AUDIOLDM_MODEL_URL
HF_REQUEST_TIMEOUT_SECONDS = settings.HF_REQUEST_TIMEOUT_SECONDS
HF_MAX_RETRIES = settings.HF_MAX_RETRIES
HF_RETRY_DELAY_SECONDS = settings.HF_RETRY_DELAY_SECONDS
HF_MAX_CONCURRENT_REQUESTS = settings.HF_MAX_CONCURRENT_REQUESTS
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_ENABLED = settings.GEMINI_ENABLED
GEMINI_MODEL_URL = settings.GEMINI_MODEL_URL
WEBHOOK_HOST = settings.WEBHOOK_HOST
WEBHOOK_SECRET = settings.WEBHOOK_SECRET
WEBHOOK_PATH = settings.WEBHOOK_PATH
WEBHOOK_URL = settings.WEBHOOK_URL
PORT = settings.PORT
HOST = settings.HOST
USE_WEBHOOK = settings.USE_WEBHOOK
TMP_DIR = settings.TMP_DIR
DB_PATH = settings.DB_PATH
TMP_FILE_TTL_SECONDS = settings.TMP_FILE_TTL_SECONDS
MAX_MUSIC_DURATION_SECONDS = settings.MAX_MUSIC_DURATION_SECONDS
MAX_EXTENDED_MUSIC_DURATION_SECONDS = settings.MAX_EXTENDED_MUSIC_DURATION_SECONDS
MAX_SOUND_DURATION_SECONDS = settings.MAX_SOUND_DURATION_SECONDS
MAX_LOGO_DURATION_SECONDS = settings.MAX_LOGO_DURATION_SECONDS
DEFAULT_MUSIC_DURATION_SECONDS = settings.DEFAULT_MUSIC_DURATION_SECONDS
DEFAULT_LOGO_DURATION_SECONDS = settings.DEFAULT_LOGO_DURATION_SECONDS
