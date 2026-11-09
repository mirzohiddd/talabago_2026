"""Ro‘yxatdan o‘tish va kirish: foydalanuvchilar (telefon+parol yoki Telegram initData) va administratorlar."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import common as C
from .. import ratelimit
from ..config import Settings, get_settings
from ..deps import ADMIN_COOKIE, get_admin, get_current_user, get_store, issue_user_token, platform_settings
from ..schemas import AdminLoginIn, LoginIn, PasswordIn, RegisterIn, TelegramAuthIn
from ..security import create_token, hash_password, verify_password
from ..storage import JsonStore
from ..telegram import InitDataError, verify_init_data

router = APIRouter(tags=['auth'])
LOGIN_FAILS = 5
LOCK_WINDOW = 15 * 60


def _verify_tg(init_data: str, settings: Settings) -> dict:
    try:
        return verify_init_data(init_data, settings.BOT_TOKEN, settings.INIT_DATA_MAX_AGE)
    except InitDataError as e:
        raise HTTPException(401, f'Telegram ma’lumotlari tasdiqlanmadi: {e}') from e


@router.post('/auth/register', status_code=201, dependencies=[Depends(ratelimit.limit('register', 10, 3600))])
def register(body: RegisterIn, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    if not platform_settings(store)['system']['registrationOpen']:
        raise HTTPException(403, 'Ro‘yxatdan o‘tish vaqtincha yopilgan')
    tg = _verify_tg(body.initData, settings) if body.initData else None
    if not tg and not body.password:
        raise HTTPException(422, 'Parol kiriting (kamida 8 belgi)')
    if body.password and len(body.password) < 8:
        raise HTTPException(422, 'Parol kamida 8 belgidan iborat bo‘lsin')
    if body.role == 'employer' and not (body.company and len(body.company) >= 2):
        raise HTTPException(422, 'Kompaniya nomini kiriting')
    profile = body.model_dump(exclude_none=True, exclude={'role', 'password', 'initData'})
    if body.role != 'student':
        for k in ('birthDate', 'university', 'faculty', 'shift', 'course', 'skills', 'cv'):
            profile.pop(k, None)
    if body.role != 'employer':
        for k in ('company', 'industry', 'address', 'position', 'logo'):
            profile.pop(k, None)
    now = C.now_iso()
    with store.tx('users') as db:
        key = C.phone_key(body.phone)
        if any(C.phone_key(u.get('phone')) == key for u in db['users']):
            raise HTTPException(409, 'Bu telefon raqam bilan hisob mavjud. “Kirish” orqali kiring.')
        if tg and any(str(u.get('telegramId')) == str(tg['id']) for u in db['users']):
            raise HTTPException(409, 'Bu Telegram hisobi allaqachon ro‘yxatdan o‘tgan.')
        user = {
            'id': C.new_id('u'), 'role': body.role, 'status': 'active', 'city': 'Toshkent', 'language': 'uz', 'skills': [],
            **profile,
            'passwordHash': hash_password(body.password) if body.password else None,
            'telegramId': tg['id'] if tg else None,
            'createdAt': now, 'updatedAt': now, 'lastActiveAt': now,
        }
        if tg and not user.get('telegram') and tg.get('username'):
            user['telegram'] = '@' + tg['username']
        db['users'].append(user)
    return {'user': C.public_user(user), 'token': issue_user_token(settings, user)}


@router.post('/auth/login', dependencies=[Depends(ratelimit.limit('login', 20, 300))])
def login(body: LoginIn, request: Request, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    key = C.phone_key(body.phone)
    lock_key = f'login-fail:{key}'
    ratelimit.guard_failures(lock_key, LOGIN_FAILS, LOCK_WINDOW)
    user = next((u for u in store.read('users') if C.phone_key(u.get('phone')) == key and len(key) == 9), None)
    if not user or not verify_password(body.password, user.get('passwordHash')):
        ratelimit.record(lock_key)
        raise HTTPException(401, 'Telefon raqam yoki parol noto‘g‘ri')
    if user.get('status') == 'blocked':
        raise HTTPException(403, 'Hisobingiz bloklangan. Texnik yordamga murojaat qiling.')
    with store.tx('users') as db:
        u = next(x for x in db['users'] if x['id'] == user['id'])
        u['lastActiveAt'] = C.now_iso()
    return {'user': C.public_user(u), 'token': issue_user_token(settings, u)}


@router.post('/auth/telegram', dependencies=[Depends(ratelimit.limit('tg-login', 30, 300))])
def telegram_login(body: TelegramAuthIn, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    """Mini App ochilganda: imzolangan initData → mavjud hisob bo‘lsa token. Yo‘q bo‘lsa 404 (ro‘yxatdan o‘tish kerak)."""
    tg = _verify_tg(body.initData, settings)
    with store.tx('users') as db:
        u = next((x for x in db['users'] if str(x.get('telegramId')) == str(tg['id'])), None)
        if not u:
            raise HTTPException(404, 'Ro‘yxatdan o‘tilmagan')
        if u.get('status') == 'blocked':
            raise HTTPException(403, 'Hisobingiz bloklangan. Texnik yordamga murojaat qiling.')
        u['lastActiveAt'] = C.now_iso()
    return {'user': C.public_user(u), 'token': issue_user_token(settings, u)}


@router.post('/auth/telegram/link')
def telegram_link(body: TelegramAuthIn, user: dict = Depends(get_current_user), settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    """Telefon bilan ro‘yxatdan o‘tgan hisobni Telegram’ga bog‘lash (Mini App ichidan)."""
    tg = _verify_tg(body.initData, settings)
    with store.tx('users') as db:
        if any(str(x.get('telegramId')) == str(tg['id']) and x['id'] != user['id'] for x in db['users']):
            raise HTTPException(409, 'Bu Telegram boshqa hisobga bog‘langan')
        u = next(x for x in db['users'] if x['id'] == user['id'])
        u['telegramId'] = tg['id']
        u['updatedAt'] = C.now_iso()
    return C.public_user(u)


@router.post('/users/me/password', status_code=204)
def change_password(body: PasswordIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    if user.get('passwordHash') and not verify_password(body.current, user['passwordHash']):
        raise HTTPException(400, 'Joriy parol noto‘g‘ri')
    with store.tx('users') as db:
        u = next(x for x in db['users'] if x['id'] == user['id'])
        u['passwordHash'] = hash_password(body.next)
        u['updatedAt'] = C.now_iso()


# ======================================================================= administrator
def _set_admin_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(ADMIN_COOKIE, token, max_age=settings.ADMIN_TOKEN_HOURS * 3600, httponly=True,
                        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE, path='/')


def _admin_out(a: dict, exp) -> dict:
    return {'user': {'id': a['id'], 'username': a['username'], 'name': a.get('name') or a['username'], 'role': 'admin'},
            'expiresAt': exp.isoformat() if hasattr(exp, 'isoformat') else exp}


@router.post('/auth/admin/login')
def admin_login(body: AdminLoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    ip = ratelimit.client_ip(request)
    fail_key = f'admin-fail:{ip}:{body.username.lower()}'
    ratelimit.guard_failures(fail_key, LOGIN_FAILS, LOCK_WINDOW)
    admin = next((a for a in store.read('admins') if a['username'].lower() == body.username.lower()), None)
    if not admin or admin.get('status') == 'blocked' or not verify_password(body.password, admin.get('passwordHash')):
        ratelimit.record(fail_key)
        raise HTTPException(401, 'Username yoki parol noto‘g‘ri')
    with store.tx('admins') as db:
        a = next(x for x in db['admins'] if x['id'] == admin['id'])
        a['lastLoginAt'] = C.now_iso()
    token, exp = create_token(settings.JWT_SECRET_KEY, a['id'], 'admin', timedelta(hours=settings.ADMIN_TOKEN_HOURS), ver=a.get('tokenVersion', 0))
    _set_admin_cookie(response, token, settings)
    return _admin_out(a, exp)


@router.get('/auth/admin/me')
def admin_me(admin: dict = Depends(get_admin)):
    from datetime import datetime, timezone
    return _admin_out(admin, datetime.fromtimestamp(admin['expiresAt'], timezone.utc))


@router.post('/auth/admin/logout', status_code=204)
def admin_logout(response: Response, settings: Settings = Depends(get_settings)):
    response.delete_cookie(ADMIN_COOKIE, path='/', secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE)


@router.post('/auth/admin/password', status_code=204)
def admin_password(body: PasswordIn, response: Response, admin: dict = Depends(get_admin), settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    if not verify_password(body.current, admin.get('passwordHash')):
        raise HTTPException(400, 'Joriy parol noto‘g‘ri')
    with store.tx('admins') as db:
        a = next(x for x in db['admins'] if x['id'] == admin['id'])
        a['passwordHash'] = hash_password(body.next)
        a['tokenVersion'] = a.get('tokenVersion', 0) + 1  # boshqa barcha sessiyalar bekor bo‘ladi
        a['updatedAt'] = C.now_iso()
    token, _ = create_token(settings.JWT_SECRET_KEY, a['id'], 'admin', timedelta(hours=settings.ADMIN_TOKEN_HOURS), ver=a['tokenVersion'])
    _set_admin_cookie(response, token, settings)
