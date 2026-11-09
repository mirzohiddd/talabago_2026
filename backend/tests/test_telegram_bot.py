"""Telegram bot: /start, Mini App tugmalari (InlineKeyboardMarkup + WebAppInfo, MenuButtonWebApp), webhook, tunnel/proxy sozlamalari."""
import subprocess
import sys
from pathlib import Path

from fastapi import Request

from app import ratelimit, telegram
from app.config import get_settings

from conftest import SENT

API = '/api/v1'


def _start_update(text='/start', chat_type='private'):
    return {'update_id': 1, 'message': {'message_id': 5, 'text': text, 'chat': {'id': 4242, 'type': chat_type}, 'from': {'id': 4242, 'first_name': 'Ali<b>'}}}


def test_start_sends_greeting_with_web_app_button_and_chat_menu(client):
    r = client.post(API + '/telegram/webhook/hook-secret-123', json=_start_update(), headers={'X-Telegram-Bot-Api-Secret-Token': 'hook-secret-123'})
    assert r.status_code == 200
    msg = next(p for m, p in SENT if m == 'sendMessage')
    assert msg['chat_id'] == 4242 and 'Assalomu alaykum' in msg['text'] and 'Ali&lt;b&gt;' in msg['text'], 'ism HTML-escape qilinadi'
    btn = msg['reply_markup']['inline_keyboard'][0][0]
    assert btn['text'] == '🚀 TalabaGo’ni ochish'
    assert btn['web_app']['url'] == 'https://app.example.uz/', 'Mini App Telegram ichida ochiladi (web_app, url emas)'
    assert 'url' not in btn, 'oddiy url tugma tashqi brauzerni ochadi'
    menu = next(p for m, p in SENT if m == 'setChatMenuButton')
    assert menu == {'chat_id': 4242, 'menu_button': {'type': 'web_app', 'text': '🚀 Ilovani ochish', 'web_app': {'url': 'https://app.example.uz/'}}}


def test_webhook_rejects_wrong_secret(client):
    assert client.post(API + '/telegram/webhook/xato', json=_start_update()).status_code == 404
    r = client.post(API + '/telegram/webhook/hook-secret-123', json=_start_update(), headers={'X-Telegram-Bot-Api-Secret-Token': 'xato'})
    assert r.status_code == 403 and not SENT
    # yangi manzil: kalit faqat sarlavhada (URL’da yo‘q → access log’ga tushmaydi)
    assert client.post(API + '/telegram/webhook', json=_start_update()).status_code == 404
    assert client.post(API + '/telegram/webhook', json=_start_update(), headers={'X-Telegram-Bot-Api-Secret-Token': 'xato'}).status_code == 404
    assert not SENT
    r = client.post(API + '/telegram/webhook', json=_start_update(), headers={'X-Telegram-Bot-Api-Secret-Token': 'hook-secret-123'})
    assert r.status_code == 200 and SENT and SENT[0][0] == 'sendMessage'


def test_other_commands_and_groups():
    telegram.handle_update(_start_update('/app'))
    assert SENT[-1][1]['reply_markup']['inline_keyboard'][0][0]['web_app']['url'].startswith('https://')
    telegram.handle_update(_start_update('salom'))
    assert 'web_app' in SENT[-1][1]['reply_markup']['inline_keyboard'][0][0]
    n = len(SENT)
    telegram.handle_update(_start_update('/start', chat_type='group'))
    assert len(SENT) == n, 'guruhlarda javob bermaydi'


def test_setup_bot_sets_default_menu_button_and_commands():
    telegram.setup_bot()
    methods = {m: p for m, p in SENT}
    assert methods['setChatMenuButton'] == {'menu_button': {'type': 'web_app', 'text': '🚀 Ilovani ochish', 'web_app': {'url': 'https://app.example.uz/'}}}
    assert [c['command'] for c in methods['setMyCommands']['commands']] == ['start', 'app', 'help']
    assert 'setMyDescription' in methods


def test_no_web_app_button_without_https(monkeypatch):
    monkeypatch.setattr(get_settings(), 'FRONTEND_URL', 'http://localhost:5173')
    telegram.handle_update(_start_update())
    msg = next(p for m, p in SENT if m == 'sendMessage')
    assert 'reply_markup' not in msg and 'sozlanmagan' in msg['text'], 'Telegram http web_app tugmasini rad etadi — yuborilmaydi'
    assert next(p for m, p in SENT if m == 'setChatMenuButton')['menu_button'] == {'type': 'commands'}


def test_user_notifications_open_inside_telegram(client):
    telegram.notify_user(777, 'Test', '/student/applications')
    btn = SENT[-1][1]['reply_markup']['inline_keyboard'][0][0]
    assert btn['web_app']['url'] == 'https://app.example.uz/#/student/applications'


def _req(host, headers=None):
    return Request({'type': 'http', 'client': (host, 1), 'headers': [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]})


def test_client_ip_behind_local_proxy_only():
    assert ratelimit.client_ip(_req('127.0.0.1', {'CF-Connecting-IP': '5.6.7.8'})) == '5.6.7.8'
    assert ratelimit.client_ip(_req('127.0.0.1', {'X-Forwarded-For': '9.9.9.9, 127.0.0.1'})) == '9.9.9.9'
    assert ratelimit.client_ip(_req('8.8.8.8', {'CF-Connecting-IP': '1.1.1.1'})) == '8.8.8.8', 'tashqi so‘rovda sarlavhaga ishonilmaydi'


def test_cors_allows_tunnel_origin_and_blocks_others(client):
    ok = client.options(API + '/health', headers={'Origin': 'https://abc-def.trycloudflare.com', 'Access-Control-Request-Method': 'GET'})
    assert ok.headers.get('access-control-allow-origin') == 'https://abc-def.trycloudflare.com'
    bad = client.options(API + '/health', headers={'Origin': 'https://evil.example.com', 'Access-Control-Request-Method': 'GET'})
    assert 'access-control-allow-origin' not in bad.headers


def test_cli_set_env_only_urls(tmp_path):
    root = Path(__file__).resolve().parent.parent
    env = tmp_path / '.env'
    env.write_text('JWT_SECRET_KEY=keep\nFRONTEND_URL=http://old\n')
    code = ('import sys, app.config as c, pathlib; c.BASE_DIR = pathlib.Path(sys.argv[1]); '
            'sys.argv = ["cli", "set-env"] + sys.argv[2:]; from app.cli import main; main()')
    r = subprocess.run([sys.executable, '-c', code, str(tmp_path), 'FRONTEND_URL=https://new.trycloudflare.com', 'SUPPORT_URL=https://s.trycloudflare.com'],
                       cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    text = env.read_text()
    assert 'FRONTEND_URL=https://new.trycloudflare.com' in text and 'SUPPORT_URL=https://s.trycloudflare.com' in text and 'JWT_SECRET_KEY=keep' in text
    r = subprocess.run([sys.executable, '-c', code, str(tmp_path), 'JWT_SECRET_KEY=hack'], cwd=root, capture_output=True, text=True)
    assert r.returncode != 0 and 'JWT_SECRET_KEY=keep' in env.read_text(), 'maxfiy kalitni o‘zgartirib bo‘lmaydi'
