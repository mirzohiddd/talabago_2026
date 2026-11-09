"""Sozlamalar faqat muhit o‘zgaruvchilari / backend/.env dan o‘qiladi. Kodda hech qanday maxfiy qiymat yo‘q."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / '.env', env_file_encoding='utf-8', extra='ignore')

    # --- Telegram ---
    BOT_TOKEN: str = ''
    ADMIN_ID: str = ''  # bildirishnoma oladigan Telegram chat ID (vergul bilan bir nechta)
    BOT_WEBHOOK_SECRET: str = ''  # /telegram/webhook/{secret} — bo‘sh bo‘lsa webhook o‘chiq

    # --- Xavfsizlik ---
    JWT_SECRET_KEY: str = ''
    USER_TOKEN_DAYS: int = 30
    ADMIN_TOKEN_HOURS: int = 8
    COOKIE_SECURE: bool = True  # lokal http uchun .env da false
    COOKIE_SAMESITE: str = 'lax'
    INIT_DATA_MAX_AGE: int = 86400  # Telegram initData necha soniya amal qiladi

    # --- URL / CORS ---
    CORS_ORIGINS: str = 'http://localhost:5173,http://localhost:5174'
    CORS_ORIGIN_REGEX: str = ''  # masalan: https://.*\.trycloudflare\.com (Vite proxy ishlatilsa shart emas)
    FRONTEND_URL: str = 'http://localhost:5173'
    SUPPORT_URL: str = 'http://localhost:5174'

    # --- Saqlash ---
    DATA_DIR: Path = BASE_DIR / 'data'
    BACKUP_KEEP: int = 30
    BACKUP_INTERVAL_SECONDS: int = 300

    # --- Birinchi administrator (faqat adminlar ro‘yxati bo‘sh bo‘lsa ishlatiladi) ---
    ADMIN_USERNAME: str = ''
    ADMIN_PASSWORD_HASH: str = ''  # python -m app.cli hash-password bilan olinadi

    # --- Cheklovlar ---
    MAX_IMAGE_MB: int = 5
    MAX_DOC_MB: int = 5
    MAX_VIDEO_MB: int = 60
    RATE_LIMIT_ENABLED: bool = True

    @field_validator('DATA_DIR', mode='before')
    @classmethod
    def _abs(cls, v):
        p = Path(v)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def cors_list(self) -> list[str]:
        return [o.strip().rstrip('/') for o in self.CORS_ORIGINS.split(',') if o.strip()]

    @property
    def admin_chat_ids(self) -> list[str]:
        return [x.strip() for x in self.ADMIN_ID.split(',') if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
