"""TalabaGo API — FastAPI ilovasi. Ishga tushirish: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import common as C
from .config import Settings, get_settings
from .deps import get_store
from .routers import admin, auth, content, listings, users
from .storage import StorageError
from .telegram import handle_update

log = logging.getLogger('talabago')
SEED_DIR = Path(__file__).parent / 'seed'
API_PREFIX = '/api/v1'


# Validatsiya xatolari — foydalanuvchiga o‘zbek tilida (pydantic’ning inglizcha matni o‘rniga)
FIELD_LABELS = {
    'firstName': 'Ism', 'lastName': 'Familiya', 'phone': 'Telefon', 'password': 'Parol', 'next': 'Yangi parol', 'current': 'Joriy parol',
    'company': 'Kompaniya nomi', 'telegram': 'Telegram', 'birthDate': 'Tug‘ilgan sana', 'university': 'O‘quv yurti', 'faculty': 'Yo‘nalish',
    'course': 'Kurs', 'shift': 'Smena', 'city': 'Shahar', 'district': 'Tuman', 'title': 'Sarlavha', 'description': 'Tavsif',
    'salary': 'Maosh', 'price': 'Narx', 'address': 'Manzil', 'photos': 'Rasmlar', 'role': 'Rol', 'username': 'Login', 'text': 'Matn',
    'subject': 'Mavzu', 'message': 'Xabar', 'moveIn': 'Ko‘chish sanasi', 'rooms': 'Xonalar', 'capacity': 'Sig‘im', 'link': 'Havola',
}


def uz_error(e: dict) -> str:
    t, ctx = e.get('type', ''), e.get('ctx') or {}
    if t == 'value_error':
        return str(ctx.get('error') or e['msg']).replace('Value error, ', '')
    return {
        'missing': 'Majburiy maydon',
        'string_too_short': f'Kamida {ctx.get("min_length")} ta belgi',
        'string_too_long': f'Ko‘pi bilan {ctx.get("max_length")} ta belgi',
        'too_short': f'Kamida {ctx.get("min_length")} ta element',
        'too_long': f'Ko‘pi bilan {ctx.get("max_length")} ta element',
        'string_type': 'Matn kiriting', 'int_parsing': 'Butun son kiriting', 'int_type': 'Butun son kiriting',
        'float_parsing': 'Son kiriting', 'bool_type': 'Ha/yo‘q qiymati kutilgan', 'bool_parsing': 'Ha/yo‘q qiymati kutilgan',
        'greater_than': f'{ctx.get("gt")} dan katta bo‘lsin', 'greater_than_equal': f'Kamida {ctx.get("ge")}',
        'less_than': f'{ctx.get("lt")} dan kichik bo‘lsin', 'less_than_equal': f'Ko‘pi bilan {ctx.get("le")}',
        'literal_error': 'Ruxsat etilmagan qiymat', 'enum': 'Ruxsat etilmagan qiymat',
        'extra_forbidden': 'Noma’lum maydon', 'json_invalid': 'JSON noto‘g‘ri', 'list_type': 'Ro‘yxat kutilgan',
        'dict_type': 'Obyekt kutilgan', 'model_attributes_type': 'Obyekt kutilgan', 'url_parsing': 'Havola noto‘g‘ri',
    }.get(t, 'Qiymat noto‘g‘ri')


class ApiGZip:
    """GZip faqat /api/ uchun (fayllar va media’ga CPU sarflanmaydi)."""

    def __init__(self, app, **kw):
        self.app = app
        self.gzip = GZipMiddleware(app, **kw)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope.get('path', '').startswith(API_PREFIX):
            return await self.gzip(scope, receive, send)
        return await self.app(scope, receive, send)


def env_admin_id(username: str) -> str:
    """Muhitdan yaratiladigan administrator ID’si doimiy (login’dan hosil qilinadi): disk tozalansa (Render qayta ishga tushishi)
    va admin qayta yaratilsa ham ID o‘zgarmaydi — brauzerdagi sessiya “Sessiya bekor qilingan” bo‘lib qolmaydi."""
    return 'adm_' + hashlib.sha256(username.strip().lower().encode()).hexdigest()[:16]


def sync_env_admin(settings: Settings, db: dict) -> str | None:
    """
    ADMIN_USERNAME + ADMIN_PASSWORD_HASH (muhit o‘zgaruvchilari) bo‘yicha administrator:
      * bunday login yo‘q bo‘lsa — yaratiladi;
      * ADMIN_PASSWORD_HASH yangi qiymatga o‘zgartirilgan bo‘lsa — parol yangilanadi va eski sessiyalar bekor qilinadi.
    Bir xil xesh bilan qayta ishga tushganda hech narsa o‘zgarmaydi (panelda o‘zgartirilgan parol saqlanib qoladi).
    Ochiq parol hech qayerda saqlanmaydi va logga yozilmaydi.
    """
    username, phash = settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD_HASH
    if not username:
        return None
    if not phash.startswith('scrypt$'):
        if phash:
            log.warning('ADMIN_PASSWORD_HASH noto‘g‘ri formatda (scrypt$...). Yaratish: python -m app.cli hash-password')
        return None
    fingerprint = hashlib.sha256(phash.encode()).hexdigest()[:16]  # xeshning o‘zi emas — faqat “o‘zgarganmi” belgisi
    admin = next((a for a in db['admins'] if a['username'].lower() == username.lower()), None)
    now = C.now_iso()
    if not admin:
        aid = env_admin_id(username)
        if any(a['id'] == aid for a in db['admins']):
            aid = C.new_id('adm')
        db['admins'].append({'id': aid, 'username': username, 'name': username, 'passwordHash': phash, 'status': 'active',
                             'tokenVersion': 0, 'envHashApplied': fingerprint, 'createdAt': now})
        return 'created'
    if admin.get('envHashApplied') != fingerprint:
        changed = admin.get('passwordHash') != phash
        admin['passwordHash'] = phash
        admin['envHashApplied'] = fingerprint
        admin['status'] = 'active'
        if changed:
            admin['tokenVersion'] = admin.get('tokenVersion', 0) + 1  # eski parol bilan ochilgan sessiyalar bekor
            admin['updatedAt'] = now
            return 'password-updated'
    return None


def bootstrap(settings: Settings) -> None:
    """Ishga tushish: administrator (muhitdagi xeshdan) va boshlang‘ich kurs kontenti."""
    store = get_store(settings)
    with store.tx('admins', 'courses', 'meta') as db:
        result = sync_env_admin(settings, db)
        if result == 'created':
            log.info('Administrator yaratildi: %s', settings.ADMIN_USERNAME)
        elif result == 'password-updated':
            log.info('Administrator paroli ADMIN_PASSWORD_HASH bo‘yicha yangilandi: %s (eski sessiyalar bekor qilindi)', settings.ADMIN_USERNAME)
        if not db['meta'].get('coursesSeeded'):
            # Rus va ingliz tili kurslarining boshlang‘ich darslari (haqiqiy o‘quv kontenti; Support panelidan tahrirlanadi)
            if not db['courses']:
                now = C.now_iso()
                db['courses'] = [{**c, 'createdAt': now, 'updatedAt': now} for c in json.loads((SEED_DIR / 'courses.json').read_text(encoding='utf-8'))]
                target = store.media_dir / 'courses'
                target.mkdir(parents=True, exist_ok=True)
                for f in (SEED_DIR / 'media' / 'courses').glob('*'):
                    if not (target / f.name).exists():
                        shutil.copy2(f, target / f.name)
            db['meta']['coursesSeeded'] = C.now_iso()
    if not store.read('admins'):
        log.warning('Administrator yo‘q. Yaratish: python -m app.cli create-admin --username <login>')


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    if len(settings.JWT_SECRET_KEY) < 32:
        raise RuntimeError('JWT_SECRET_KEY kamida 32 belgi bo‘lishi kerak (backend/.env). Yaratish: python -m app.cli secret')

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bootstrap(settings)
        yield

    docs = settings.API_DOCS
    app = FastAPI(title='TalabaGo API', version='1.0.0', lifespan=lifespan, docs_url='/api/docs' if docs else None,
                  openapi_url='/api/openapi.json' if docs else None, redoc_url=None)
    upload_limit = max(settings.MAX_VIDEO_MB, settings.MAX_IMAGE_MB, settings.MAX_DOC_MB) * 1024 * 1024 + 1024 * 1024
    json_limit = settings.MAX_JSON_KB * 1024
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_list, allow_origin_regex=settings.CORS_ORIGIN_REGEX or None, allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-Requested-With', 'X-Telegram-Init-Data'], max_age=600,
        expose_headers=['X-Session-Expires', 'Retry-After'],
    )

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        # So‘rov hajmi: katta JSON bilan xotirani to‘ldirishga qarshi (fayl yuklash — multipart — alohida, kattaroq chegara)
        size = request.headers.get('content-length')
        if size and size.isdigit():
            multipart = request.headers.get('content-type', '').startswith('multipart/form-data')
            if int(size) > (upload_limit if multipart else json_limit):
                return JSONResponse({'detail': 'So‘rov hajmi juda katta'}, status_code=413)
        resp = await call_next(request)
        resp.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()')
        if settings.cookie_secure:
            resp.headers.setdefault('Strict-Transport-Security', 'max-age=15552000')
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        if request.url.path.startswith('/media/'):
            resp.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'"
            resp.headers.setdefault('Cache-Control', 'public, max-age=604800')
        elif request.url.path.startswith(API_PREFIX):
            resp.headers.setdefault('Cache-Control', 'no-store')
        return resp

    @app.exception_handler(StorageError)
    async def storage_error(_: Request, exc: StorageError):
        log.exception('Ombor xatosi: %s', exc)
        return JSONResponse({'detail': 'Ma’lumotlar omborida xatolik. Administrator xabardor qilindi.'}, status_code=500)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errors = [{'field': '.'.join(str(p) for p in e['loc'][1:]), 'message': uz_error(e)} for e in exc.errors()]
        first = errors[0] if errors else {'field': '', 'message': 'Ma’lumot noto‘g‘ri'}
        label = FIELD_LABELS.get(first['field'].split('.')[0], '')
        return JSONResponse({'detail': f'{label}: {first["message"]}' if label else first['message'], 'errors': errors}, status_code=422)

    for r in (auth.router, users.router, listings.router, content.router, admin.router):
        app.include_router(r, prefix=API_PREFIX)

    # JSON javoblarni siqish (≈10× kichik; mobil internetda ro‘yxatlar tez ochiladi). /media (rasm/video) siqilmaydi — ular allaqachon siqilgan.
    app.add_middleware(ApiGZip, minimum_size=1024, compresslevel=5)

    @app.get(API_PREFIX + '/health', tags=['system'])
    def health():
        get_store(settings).read('meta')  # ombor o‘qilishini tekshirish
        return {'ok': True, 'time': C.now_iso()}

    @app.post(API_PREFIX + '/telegram/webhook', include_in_schema=False)
    async def telegram_webhook(request: Request):
        """Telegram webhook. Maxfiy kalit faqat X-Telegram-Bot-Api-Secret-Token sarlavhasida — URL’da emas (access log’ga tushmaydi)."""
        import hmac
        header = request.headers.get('x-telegram-bot-api-secret-token', '')
        if not settings.BOT_WEBHOOK_SECRET or not header or not hmac.compare_digest(header, settings.BOT_WEBHOOK_SECRET):
            raise HTTPException(404)
        handle_update(await request.json())
        return {'ok': True}

    @app.post(API_PREFIX + '/telegram/webhook/{secret}', include_in_schema=False)
    async def telegram_webhook_legacy(secret: str, request: Request):
        """Eski manzil (moslik uchun). Yangi o‘rnatishda `python -m app.cli set-webhook` yuqoridagi manzilni ishlatadi."""
        import hmac
        if not settings.BOT_WEBHOOK_SECRET or not hmac.compare_digest(secret, settings.BOT_WEBHOOK_SECRET):
            raise HTTPException(404)
        header = request.headers.get('x-telegram-bot-api-secret-token', '')
        if header and not hmac.compare_digest(header, settings.BOT_WEBHOOK_SECRET):
            raise HTTPException(403)
        handle_update(await request.json())
        return {'ok': True}

    media = get_store(settings).media_dir
    app.mount('/media', StaticFiles(directory=media, check_dir=True), name='media')
    return app


try:
    app = create_app()
except RuntimeError as _e:  # .env sozlanmagan bo‘lsa — tushunarli xabar bilan to‘xtaydi
    if __name__ != '__main__':
        logging.basicConfig()
        log.error(str(_e))
    raise