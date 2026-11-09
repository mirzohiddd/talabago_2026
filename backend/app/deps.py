"""FastAPI dependency’lari: ombor, joriy foydalanuvchi / administrator, rollar."""
from __future__ import annotations

from datetime import timedelta
from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings
from .security import create_token, decode_token
from .storage import JsonStore

ADMIN_COOKIE = 'tg_support_session'
UNSAFE = {'POST', 'PUT', 'PATCH', 'DELETE'}


@lru_cache
def _store(data_dir: str, keep: int, interval: int) -> JsonStore:
    return JsonStore(data_dir, keep, interval)


def get_store(settings: Settings = Depends(get_settings)) -> JsonStore:
    return _store(str(settings.DATA_DIR), settings.BACKUP_KEEP, settings.BACKUP_INTERVAL_SECONDS)


def platform_settings(store: JsonStore) -> dict:
    s = store.read('settings')
    system = {'maintenance': False, 'registrationOpen': True, 'moderation': True, 'adsEnabled': True, **(s.get('system') or {})}
    return {**s, 'system': system}


def issue_user_token(settings: Settings, user: dict) -> str:
    token, _ = create_token(settings.JWT_SECRET_KEY, user['id'], 'user', timedelta(days=settings.USER_TOKEN_DAYS), role=user['role'])
    return token


def _bearer(request: Request) -> str | None:
    h = request.headers.get('authorization', '')
    return h[7:].strip() if h.lower().startswith('bearer ') else None


def get_current_user(request: Request, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)) -> dict:
    token = _bearer(request)
    data = decode_token(settings.JWT_SECRET_KEY, token, 'user') if token else None
    if not data:
        raise HTTPException(401, 'Avtorizatsiya talab qilinadi')
    user = next((u for u in store.read('users') if u['id'] == data['sub']), None)
    if not user:
        raise HTTPException(401, 'Hisob topilmadi')
    if user.get('status') == 'blocked':
        raise HTTPException(403, 'Hisobingiz bloklangan. Texnik yordamga murojaat qiling.')
    if platform_settings(store)['system']['maintenance']:
        raise HTTPException(503, 'Platformada texnik ishlar olib borilmoqda. Birozdan so‘ng qayta urinib ko‘ring.')
    return user


def require_role(*roles: str):
    def dep(user: dict = Depends(get_current_user)) -> dict:
        if user['role'] not in roles:
            raise HTTPException(403, 'Bu amal sizning rolingiz uchun emas')
        return user
    return dep


def get_admin(request: Request, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)) -> dict:
    token = request.cookies.get(ADMIN_COOKIE) or _bearer(request)
    data = decode_token(settings.JWT_SECRET_KEY, token, 'admin') if token else None
    if not data:
        raise HTTPException(401, 'Administrator sifatida kiring')
    admin = next((a for a in store.read('admins') if a['id'] == data['sub']), None)
    if not admin or admin.get('status') == 'blocked' or admin.get('tokenVersion', 0) != data.get('ver', 0):
        raise HTTPException(401, 'Sessiya bekor qilingan')
    # CSRF: cookie bilan kelgan o‘zgartiruvchi so‘rovlarda maxsus sarlavha majburiy (boshqa saytdan yuborib bo‘lmaydi)
    if request.method in UNSAFE and request.cookies.get(ADMIN_COOKIE) and request.headers.get('x-requested-with') != 'TalabaGo':
        raise HTTPException(403, 'CSRF tekshiruvidan o‘tmadi')
    return {**admin, 'expiresAt': data['exp']}
