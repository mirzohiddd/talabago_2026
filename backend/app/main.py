"""TalabaGo API — FastAPI ilovasi. Ishga tushirish: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations

import json
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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


def bootstrap(settings: Settings) -> None:
    """Birinchi ishga tushish: administrator (.env dagi xeshdan) va boshlang‘ich kurs kontenti."""
    store = get_store(settings)
    with store.tx('admins', 'courses', 'meta') as db:
        if not db['admins'] and settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD_HASH.startswith('scrypt$'):
            db['admins'].append({'id': C.new_id('adm'), 'username': settings.ADMIN_USERNAME, 'name': settings.ADMIN_USERNAME,
                                 'passwordHash': settings.ADMIN_PASSWORD_HASH, 'status': 'active', 'tokenVersion': 0, 'createdAt': C.now_iso()})
            log.info('Administrator yaratildi: %s', settings.ADMIN_USERNAME)
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

    app = FastAPI(title='TalabaGo API', version='1.0.0', lifespan=lifespan, docs_url='/api/docs', openapi_url='/api/openapi.json', redoc_url=None)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_list, allow_origin_regex=settings.CORS_ORIGIN_REGEX or None, allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-Requested-With', 'X-Telegram-Init-Data'], max_age=600,
    )

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
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
        errors = [{'field': '.'.join(str(p) for p in e['loc'][1:]), 'message': e['msg'].replace('Value error, ', '')} for e in exc.errors()]
        first = errors[0] if errors else {'field': '', 'message': 'Ma’lumot noto‘g‘ri'}
        return JSONResponse({'detail': f'{first["field"]}: {first["message"]}' if first['field'] else first['message'], 'errors': errors}, status_code=422)

    for r in (auth.router, users.router, listings.router, content.router, admin.router):
        app.include_router(r, prefix=API_PREFIX)

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
