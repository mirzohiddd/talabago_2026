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
    BOT_WEBHOOK_SECRET: str = ''  # X-Telegram-Bot-Api-Secret-Token — bo‘sh bo‘lsa webhook o‘chiq

    # --- Xavfsizlik ---
    JWT_SECRET_KEY: str = ''
    USER_TOKEN_DAYS: int = 30
    ADMIN_TOKEN_HOURS: int = 8  # faol ishlatilsa sessiya avtomatik uzayadi (sliding); shuncha soat harakatsizlikdan keyin tugaydi
    COOKIE_SECURE: bool = True  # lokal http uchun .env da false
    # lax — panel API bilan bitta sayt orqali (Vercel rewrite / Vite proxy / nginx). Tavsiya etiladi.
    # none — panel va API boshqa-boshqa saytlarda (vercel.app → onrender.com); Secure majburiy, Partitioned (CHIPS) qo‘shiladi.
    COOKIE_SAMESITE: str = 'lax'
    COOKIE_PARTITIONED: bool | None = None  # None → SameSite=None bo‘lsa avtomatik yoqiladi
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

    @field_validator('COOKIE_SAMESITE', mode='before')
    @classmethod
    def _samesite(cls, v):
        v = str(v or 'lax').strip().lower()
        if v not in ('lax', 'strict', 'none'):
            raise ValueError('COOKIE_SAMESITE: lax | strict | none')
        return v

    @field_validator('ADMIN_USERNAME', 'ADMIN_PASSWORD_HASH', 'JWT_SECRET_KEY', mode='before')
    @classmethod
    def _strip(cls, v):
        # Render/Vercel panellariga nusxalashda qo‘shilib qoladigan bo‘sh joy va qo‘shtirnoqlar
        return str(v or '').strip().strip('"\'')

    @property
    def cookie_secure(self) -> bool:
        return True if self.COOKIE_SAMESITE == 'none' else self.COOKIE_SECURE

    @property
    def cookie_partitioned(self) -> bool:
        return self.COOKIE_SAMESITE == 'none' if self.COOKIE_PARTITIONED is None else self.COOKIE_PARTITIONED

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