"""
Boshqaruv buyruqlari:
  python -m app.cli secret                      — JWT_SECRET_KEY uchun tasodifiy qiymat
  python -m app.cli hash-password               — parol xeshi (ADMIN_PASSWORD_HASH uchun)
  python -m app.cli create-admin --username X   — administrator qo‘shish (parol so‘raladi)
  python -m app.cli set-admin-password --username X   — parolni almashtirish (parol so‘raladi; barcha sessiyalar bekor)
  python -m app.cli admin-status                — administratorlar ro‘yxati va muhit sozlamalari tekshiruvi (xesh/parol chiqmaydi)
  python -m app.cli backup                      — barcha JSON’larning to‘liq nusxasi
  python -m app.cli setup-bot                   — bot menyusi (Mini App tugmasi) va buyruqlari
  python -m app.cli set-webhook                 — Telegram webhook’ni API_PUBLIC_URL ga o‘rnatish
  python -m app.cli bot-check                   — bot, webhook va menyu tugmasi holati
  python -m app.cli set-env FRONTEND_URL=https://...  — .env dagi URL’larni yangilash
"""
import argparse
import getpass
import os
import secrets
import sys

from . import common as C
from .config import get_settings
from .deps import get_store
from .security import hash_password


def _ask_password() -> str:
    pw = os.environ.get('NEW_PASSWORD') or getpass.getpass('Parol (kamida 8 belgi): ')
    if len(pw) < 8:
        sys.exit('Parol juda qisqa')
    if not os.environ.get('NEW_PASSWORD') and getpass.getpass('Parolni takrorlang: ') != pw:
        sys.exit('Parollar mos emas')
    return pw


ALLOWED_ENV = {'FRONTEND_URL', 'SUPPORT_URL', 'CORS_ORIGINS', 'COOKIE_SECURE'}


def set_env(pairs: list[str]) -> None:
    """backend/.env dagi URL qiymatlarini yangilash (start.sh tunnel manzilini shu orqali yozadi). Maxfiy kalitlarni o‘zgartirmaydi."""
    from .config import BASE_DIR
    path = BASE_DIR / '.env'
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    for pair in pairs:
        key, _, val = pair.partition('=')
        if key not in ALLOWED_ENV or not val or '\n' in val:
            sys.exit(f'Ruxsat etilmagan: {key}')
        for i, line in enumerate(lines):
            if line.split('=', 1)[0].strip() == key:
                lines[i] = f'{key}={val}'
                break
        else:
            lines.append(f'{key}={val}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('.env yangilandi:', ', '.join(p.split('=', 1)[0] for p in pairs))


def main() -> None:
    p = argparse.ArgumentParser(prog='python -m app.cli')
    p.add_argument('cmd', choices=['secret', 'hash-password', 'create-admin', 'set-admin-password', 'admin-status', 'backup', 'setup-bot', 'set-webhook', 'bot-check', 'set-env'])
    p.add_argument('--username')
    p.add_argument('pairs', nargs='*', help='set-env uchun KEY=VALUE')
    a = p.parse_args()
    if a.cmd == 'secret':
        print(secrets.token_urlsafe(48))
        return
    if a.cmd == 'set-env':
        set_env(a.pairs)
        return
    if a.cmd == 'hash-password':
        print(hash_password(_ask_password()))
        return
    s = get_settings()
    store = get_store(s)
    if a.cmd in ('create-admin', 'set-admin-password'):
        if not a.username:
            sys.exit('--username kerak')
        pw = _ask_password()
        with store.tx('admins') as db:
            ex = next((x for x in db['admins'] if x['username'].lower() == a.username.lower()), None)
            if a.cmd == 'create-admin':
                if ex:
                    sys.exit('Bunday administrator bor')
                db['admins'].append({'id': C.new_id('adm'), 'username': a.username, 'name': a.username, 'passwordHash': hash_password(pw),
                                     'status': 'active', 'tokenVersion': 0, 'createdAt': C.now_iso()})
            else:
                if not ex:
                    sys.exit('Administrator topilmadi')
                ex['passwordHash'] = hash_password(pw)
                ex['tokenVersion'] = ex.get('tokenVersion', 0) + 1
        print('Tayyor')
    elif a.cmd == 'admin-status':
        import hashlib
        fp = hashlib.sha256(s.ADMIN_PASSWORD_HASH.encode()).hexdigest()[:16] if s.ADMIN_PASSWORD_HASH else None
        print(f'ADMIN_USERNAME: {s.ADMIN_USERNAME or "(bo‘sh)"}')
        print(f'ADMIN_PASSWORD_HASH: {"to‘g‘ri formatda (scrypt$)" if s.ADMIN_PASSWORD_HASH.startswith("scrypt$") else "YO‘Q yoki noto‘g‘ri"}')
        print(f'COOKIE_SAMESITE={s.COOKIE_SAMESITE} · Secure={s.cookie_secure} · Partitioned={s.cookie_partitioned} · ADMIN_TOKEN_HOURS={s.ADMIN_TOKEN_HOURS}')
        print(f'DATA_DIR: {s.DATA_DIR}')
        for x in store.read('admins'):
            applied = 'ha' if fp and x.get('envHashApplied') == fp else 'yo‘q'
            print(f'  - {x["username"]} · {x.get("status", "active")} · id={x["id"]} · muhit xeshi qo‘llangan: {applied} · oxirgi kirish: {x.get("lastLoginAt") or "—"}')
    elif a.cmd == 'backup':
        print(store.snapshot())
    elif a.cmd == 'bot-check':
        import json
        from .telegram import bot_status
        print(json.dumps(bot_status(), ensure_ascii=False, indent=2))
    elif a.cmd == 'setup-bot':
        from .telegram import setup_bot
        print(setup_bot())
    elif a.cmd == 'set-webhook':
        from .telegram import call
        base = os.environ.get('API_PUBLIC_URL', '').rstrip('/')
        if not base.startswith('https://') or not s.BOT_WEBHOOK_SECRET:
            sys.exit('API_PUBLIC_URL (https://...) va BOT_WEBHOOK_SECRET kerak')
        print(call('setWebhook', {'url': f'{base}/api/v1/telegram/webhook', 'secret_token': s.BOT_WEBHOOK_SECRET,
                                  'allowed_updates': ['message']}))


if __name__ == '__main__':
    main()