"""Telegram: Mini App initData tekshiruvi (server tomonda) va Bot API orqali xabar yuborish."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl

import httpx

from .config import get_settings

log = logging.getLogger('talabago.telegram')
API = 'https://api.telegram.org/bot{token}/{method}'


class InitDataError(ValueError):
    pass


def verify_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    """
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token); hash = HMAC_SHA256(secret_key, data_check_string)
    """
    if not bot_token:
        raise InitDataError('BOT_TOKEN sozlanmagan')
    if not init_data:
        raise InitDataError('initData yo‘q')
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received = pairs.pop('hash', None)
    if not received:
        raise InitDataError('hash yo‘q')
    check_string = '\n'.join(f'{k}={v}' for k, v in sorted(pairs.items()))
    secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received):
        raise InitDataError('imzo noto‘g‘ri')
    try:
        auth_date = int(pairs.get('auth_date', '0'))
    except ValueError as e:
        raise InitDataError('auth_date noto‘g‘ri') from e
    if max_age and time.time() - auth_date > max_age:
        raise InitDataError('initData muddati o‘tgan')
    user = json.loads(pairs.get('user') or '{}')
    if not user.get('id'):
        raise InitDataError('foydalanuvchi yo‘q')
    return user


def sign_init_data(user: dict, bot_token: str, auth_date: int | None = None) -> str:
    """Testlar uchun: Telegram qanday imzolasa, xuddi shunday initData yasaydi."""
    from urllib.parse import urlencode
    fields = {'auth_date': str(auth_date or int(time.time())), 'query_id': 'AAE-test', 'user': json.dumps(user, separators=(',', ':'))}
    check_string = '\n'.join(f'{k}={v}' for k, v in sorted(fields.items()))
    secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
    fields['hash'] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


# ------------------------------------------------------------------ Bot API
def call(method: str, payload: dict, timeout: float = 8.0) -> dict | None:
    token = get_settings().BOT_TOKEN
    if not token:
        return None
    try:
        r = httpx.post(API.format(token=token, method=method), json=payload, timeout=timeout)
        data = r.json()
        if not data.get('ok'):
            log.warning('Telegram %s: %s', method, data.get('description'))
        return data
    except Exception as exc:  # noqa: BLE001 — bildirishnoma asosiy jarayonni to‘xtatmasligi kerak
        log.warning('Telegram %s yuborilmadi: %s', method, exc)
        return None


_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='tg')
SYNC = False  # testlarda True — xabar darhol yuboriladi


def _dispatch(method: str, payload: dict) -> None:
    """Bot API so‘rovi fon oqimida — Telegram sekin javob bersa ham API javobi kechikmaydi."""
    if SYNC:
        call(method, payload)
    else:
        _pool.submit(lambda: call(method, payload))


def send_message(chat_id: str | int, text: str, buttons: list[list[dict]] | None = None) -> None:
    if not get_settings().BOT_TOKEN:
        return
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    if buttons:
        payload['reply_markup'] = {'inline_keyboard': buttons}
    _dispatch('sendMessage', payload)


def esc(s: str) -> str:
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def notify_admins(text: str, link_path: str = '') -> None:
    s = get_settings()
    buttons = [[{'text': 'TalabaGo Support’da ochish', 'url': s.SUPPORT_URL.rstrip('/') + link_path}]] if s.SUPPORT_URL.startswith('https://') else None
    for chat in s.admin_chat_ids:
        send_message(chat, text, buttons)


def notify_user(telegram_id: int | str | None, text: str, path: str = '') -> None:
    if not telegram_id:
        return
    btn = web_app_button('🚀 Ilovada ochish', path)
    send_message(telegram_id, text, [[btn]] if btn else None)


# ------------------------------------------------------------------ bot: /start va Mini App tugmalari
OPEN_BUTTON = '🚀 TalabaGo’ni ochish'      # /start xabari ostidagi inline tugma (InlineKeyboardMarkup + WebAppInfo)
MENU_BUTTON = '🚀 Ilovani ochish'          # chat pastidagi doimiy menyu tugmasi (MenuButtonWebApp)


def mini_app_url(path: str = '') -> str | None:
    """Mini App manzili (FRONTEND_URL). Telegram web_app tugmalari faqat https bilan ishlaydi."""
    base = get_settings().FRONTEND_URL.strip().rstrip('/')
    if not base.startswith('https://'):
        return None
    return base + ('/#' + path if path else '/')


def web_app_button(text: str, path: str = '') -> dict | None:
    url = mini_app_url(path)
    return {'text': text, 'web_app': {'url': url}} if url else None


def menu_button() -> dict:
    url = mini_app_url()
    return {'type': 'web_app', 'text': MENU_BUTTON, 'web_app': {'url': url}} if url else {'type': 'commands'}


def start_message(chat_id: int | str, first_name: str = '') -> None:
    """
    /start: salomlashish + “🚀 TalabaGo’ni ochish” inline tugmasi (Mini App Telegram ichida ochiladi).
    Telegram foydalanuvchi bosmasdan Mini App’ni o‘zi ochishga ruxsat bermaydi — shu sababli eng qisqa yo‘l:
    xabar ostidagi tugma + chat pastidagi doimiy menyu tugmasi (shu chat uchun ham alohida o‘rnatiladi).
    """
    name = esc(first_name)
    text = (f'Assalomu alaykum{", <b>" + name + "</b>" if name else ""}! 👋\n\n'
            '<b>TalabaGo</b> — talabalar uchun ish, turar joy va bepul rus/ingliz tili kurslari.\n\n'
            '🎓 Talaba — o‘qishga mos ish va turar joy toping\n'
            '💼 Ish beruvchi — yosh xodimlarni toping\n'
            '🏠 Uy egasi — uyingizni talabalarga ijaraga bering\n\n'
            'Ilovani ochish uchun quyidagi tugmani bosing 👇')
    btn = web_app_button(OPEN_BUTTON)
    if not btn:
        text += '\n\n<i>Ilova manzili hali sozlanmagan. Birozdan so‘ng qayta urinib ko‘ring.</i>'
        log.warning('FRONTEND_URL https emas — Mini App tugmasi yuborilmadi')
    send_message(chat_id, text, [[btn]] if btn else None)
    # Shu chat uchun doimiy menyu tugmasi (global sozlama hali yangilanmagan bo‘lsa ham darhol chiqadi)
    _dispatch('setChatMenuButton', {'chat_id': chat_id, 'menu_button': menu_button()})


def handle_update(update: dict) -> None:
    msg = update.get('message') or {}
    text = (msg.get('text') or '').strip()
    chat = msg.get('chat') or {}
    if not chat.get('id') or chat.get('type', 'private') != 'private':
        return
    cmd = text.split()[0].split('@')[0] if text else ''
    if cmd == '/start':
        start_message(chat['id'], (msg.get('from') or {}).get('first_name', ''))
    elif cmd in ('/app', '/open'):
        btn = web_app_button(OPEN_BUTTON)
        send_message(chat['id'], 'TalabaGo ilovasi 👇', [[btn]] if btn else None)
    elif cmd == '/help':
        btn = web_app_button('🛟 Texnik yordam', '/welcome')
        send_message(chat['id'], 'Savol yoki muammo bo‘lsa, ilovadagi <b>Sozlamalar → Texnik yordam</b> bo‘limidan murojaat yuboring.',
                     [[btn]] if btn else None)
    elif text:
        btn = web_app_button(OPEN_BUTTON)
        send_message(chat['id'], 'Barcha imkoniyatlar ilova ichida 👇', [[btn]] if btn else None)


def setup_bot() -> list:
    """Buyruqlar, tavsif va barcha chatlar uchun standart menyu tugmasi (MenuButtonWebApp). CLI: python -m app.cli setup-bot"""
    out = [
        call('setMyCommands', {'commands': [{'command': 'start', 'description': 'Boshlash'},
                                            {'command': 'app', 'description': 'TalabaGo ilovasini ochish'},
                                            {'command': 'help', 'description': 'Yordam'}]}),
        call('setMyShortDescription', {'short_description': 'Talabalar uchun ish, turar joy va bepul til kurslari'}),
        call('setMyDescription', {'description': 'TalabaGo — talabalar uchun ish, turar joy va bepul rus/ingliz tili kurslari. '
                                                 '“Start” ni bosing va ilovani oching.'}),
        call('setChatMenuButton', {'menu_button': menu_button()}),
    ]
    return out


def bot_status() -> dict:
    """Diagnostika: bot, webhook va menyu tugmasi holati (CLI: python -m app.cli bot-check)."""
    me = call('getMe', {}) or {}
    hook = call('getWebhookInfo', {}) or {}
    menu = call('getChatMenuButton', {}) or {}
    return {'bot': (me.get('result') or {}).get('username'), 'ok': me.get('ok', False), 'mini_app_url': mini_app_url(),
            'webhook': (hook.get('result') or {}).get('url') or None, 'webhook_error': (hook.get('result') or {}).get('last_error_message'),
            'menu_button': menu.get('result')}
