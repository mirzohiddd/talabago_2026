"""FastAPI dependency’lari: ombor, joriy foydalanuvchi / administrator, rollar."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from http.cookies import SimpleCookie

from fastapi import Depends, HTTPException, Request, Response

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
    # ver — parol almashganda eski (o‘g‘irlangan bo‘lishi mumkin) tokenlar bekor bo‘ladi
    token, _ = create_token(settings.JWT_SECRET_KEY, user['id'], 'user', timedelta(days=settings.USER_TOKEN_DAYS), role=user['role'], ver=user.get('tokenVersion', 0))
    return token


def _cookie_header(settings: Settings, value: str, max_age: int) -> str:
    """Admin sessiya cookie’si. Domain qo‘yilmaydi (host-only) — Vercel rewrite orqali panel domenida saqlanadi."""
    c = SimpleCookie()
    c[ADMIN_COOKIE] = value
    m = c[ADMIN_COOKIE]
    m['path'] = '/'
    m['max-age'] = max_age
    m['httponly'] = True
    m['samesite'] = settings.COOKIE_SAMESITE.capitalize()
    if settings.cookie_secure:
        m['secure'] = True
    if max_age <= 0:
        m['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    out = m.OutputString()
    # Partitioned (CHIPS): brauzer uchinchi tomon cookie’larini bloklaganda ham (Chrome) shu panel uchun ishlaydi
    return out + '; Partitioned' if settings.cookie_partitioned and settings.cookie_secure else out


def set_admin_cookie(response: Response, token: str, settings: Settings) -> None:
    response.headers.append('set-cookie', _cookie_header(settings, token, settings.ADMIN_TOKEN_HOURS * 3600))


def clear_admin_cookie(response: Response, settings: Settings) -> None:
    response.headers.append('set-cookie', _cookie_header(settings, '', 0))


def issue_admin_token(settings: Settings, admin: dict) -> tuple[str, datetime]:
    return create_token(settings.JWT_SECRET_KEY, admin['id'], 'admin', timedelta(hours=settings.ADMIN_TOKEN_HOURS), ver=admin.get('tokenVersion', 0))


def _bearer(request: Request) -> str | None:
    h = request.headers.get('authorization', '')
    return h[7:].strip() if h.lower().startswith('bearer ') else None


def get_current_user(request: Request, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)) -> dict:
    token = _bearer(request)
    data = decode_token(settings.JWT_SECRET_KEY, token, 'user') if token else None
    if not data:
        raise HTTPException(401, 'Avtorizatsiya talab qilinadi')
    user = store.get('users', data['sub'])
    if not user:
        raise HTTPException(401, 'Hisob topilmadi')
    if user.get('tokenVersion', 0) != data.get('ver', 0):
        raise HTTPException(401, 'Sessiya tugagan. Qayta kiring.')
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


def get_admin(request: Request, response: Response, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)) -> dict:
    from_cookie = request.cookies.get(ADMIN_COOKIE)
    token = from_cookie or _bearer(request)
    data = decode_token(settings.JWT_SECRET_KEY, token, 'admin') if token else None
    if not data:
        raise HTTPException(401, 'Administrator sifatida kiring')
    admin = store.get('admins', data['sub'])
    if not admin or admin.get('status') == 'blocked' or admin.get('tokenVersion', 0) != data.get('ver', 0):
        raise HTTPException(401, 'Sessiya bekor qilingan')
    # CSRF: cookie bilan kelgan o‘zgartiruvchi so‘rovlarda maxsus sarlavha majburiy (boshqa saytdan yuborib bo‘lmaydi)
    if request.method in UNSAFE and request.cookies.get(ADMIN_COOKIE) and request.headers.get('x-requested-with') != 'TalabaGo':
        raise HTTPException(403, 'CSRF tekshiruvidan o‘tmadi')
    exp = data['exp']
    # Sliding sessiya: muddatning yarmi o‘tgan bo‘lsa — yangi cookie (faol ishlayotgan administrator chiqarib yuborilmaydi)
    if from_cookie and exp - time.time() < settings.ADMIN_TOKEN_HOURS * 1800:
        token, new_exp = issue_admin_token(settings, admin)
        set_admin_cookie(response, token, settings)
        exp = new_exp.timestamp()
    response.headers['X-Session-Expires'] = datetime.fromtimestamp(exp, timezone.utc).isoformat()
    return {**admin, 'expiresAt': exp}