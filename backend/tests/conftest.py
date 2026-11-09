import io
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp(prefix='talabago-test-'))
BOT = '123456:TEST-token'
os.environ.update({
    'DATA_DIR': str(TMP / 'data'), 'JWT_SECRET_KEY': 'test-secret-key-' + 'x' * 40, 'BOT_TOKEN': BOT, 'ADMIN_ID': '777',
    'COOKIE_SECURE': 'false', 'ADMIN_USERNAME': 'root', 'RATE_LIMIT_ENABLED': 'true', 'BACKUP_INTERVAL_SECONDS': '0',
    'FRONTEND_URL': 'https://app.example.uz', 'BOT_WEBHOOK_SECRET': 'hook-secret-123', 'CORS_ORIGIN_REGEX': r'https://[a-z0-9-]+\.trycloudflare\.com', 'SUPPORT_URL': 'https://support.example.uz',
})
from app.security import hash_password  # noqa: E402

os.environ['ADMIN_PASSWORD_HASH'] = hash_password('root-password-1')

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app import ratelimit, telegram  # noqa: E402
from app.main import create_app  # noqa: E402

SENT: list = []


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    SENT.clear()
    monkeypatch.setattr(telegram, 'SYNC', True)
    monkeypatch.setattr(telegram, 'call', lambda method, payload, timeout=8.0: SENT.append((method, payload)) or {'ok': True})
    ratelimit.reset()


@pytest.fixture(scope='session')
def app():
    return create_app(get_settings())


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(app):
    with TestClient(app) as c:
        r = c.post('/api/v1/auth/admin/login', json={'username': 'root', 'password': 'root-password-1'})
        assert r.status_code == 200, r.text
        c.headers['X-Requested-With'] = 'TalabaGo'
        yield c


_counter = [100]


def register(client, role='student', **extra):
    _counter[0] += 1
    body = {'role': role, 'firstName': f'Test{_counter[0]}', 'lastName': 'User', 'phone': f'90{_counter[0]:07d}', 'password': 'parol12345', **extra}
    if role == 'employer':
        body.setdefault('company', 'ACME LLC')
    r = client.post('/api/v1/auth/register', json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    return {'Authorization': f'Bearer {data["token"]}'}, data['user'], body


def png_bytes(w=40, h=30, color=(16, 185, 129)):
    from PIL import Image
    b = io.BytesIO()
    Image.new('RGB', (w, h), color).save(b, 'PNG')
    return b.getvalue()


def upload(client, headers, kind='photo', data=None, name='a.png', path='/api/v1/files'):
    r = client.post(path, headers=headers, files={'file': (name, data or png_bytes(), 'image/png')}, data={'kind': kind})
    return r


JOB = {'title': 'Kafe ofitsianti', 'company': 'ACME LLC', 'city': 'Toshkent', 'district': 'Chilonzor', 'format': 'offline', 'type': 'hourly',
       'salary': 25000, 'salaryPeriod': 'hour', 'workTime': 'evening', 'schedule': '18:00-23:00', 'category': 'Xizmat ko‘rsatish',
       'description': 'Talabalar uchun kechki smenada ishlash, o‘rgatamiz.', 'requirements': ['Muloqot'], 'phone': '+998 90 000 00 01'}
