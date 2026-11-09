"""
Telegram bot — long polling (webhook o‘rnatilmagan muhit uchun): python -m app.bot
/start → "TalabaGo’ni ochish" Mini App tugmasi. Webhook ishlatilsa bu jarayon kerak emas.
"""
import logging
import time

import httpx

from .config import get_settings
from .telegram import API, handle_update, setup_bot

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('talabago.bot')


def main() -> None:
    s = get_settings()
    if not s.BOT_TOKEN:
        raise SystemExit('BOT_TOKEN sozlanmagan (backend/.env)')
    httpx.post(API.format(token=s.BOT_TOKEN, method='deleteWebhook'), timeout=10)
    setup_bot()
    from .telegram import mini_app_url
    log.info('Mini App manzili: %s', mini_app_url() or 'YO‘Q — FRONTEND_URL https bo‘lishi kerak')
    offset = 0
    log.info('Bot ishga tushdi (polling)')
    while True:
        try:
            r = httpx.get(API.format(token=s.BOT_TOKEN, method='getUpdates'), params={'offset': offset, 'timeout': 50, 'allowed_updates': '["message"]'}, timeout=60).json()
            if not r.get('ok'):
                # 409: bot boshqa joyda ishlayapti yoki webhook o‘rnatilgan; 401: token noto‘g‘ri
                log.error('getUpdates: %s %s', r.get('error_code'), r.get('description'))
                if r.get('error_code') == 401:
                    raise SystemExit('BOT_TOKEN noto‘g‘ri')
                time.sleep(10)
                continue
            for u in r.get('result', []):
                offset = u['update_id'] + 1
                handle_update(u)
        except Exception as exc:  # noqa: BLE001
            log.warning('polling xatosi: %s', exc)
            time.sleep(5)


if __name__ == '__main__':
    main()
