"""Support paneli sessiyasi: cookie rejimlari (bitta sayt / Vercel→Render), sliding muddat, muhitdan admin paroli, o‘zgarishlar belgisi."""
import json
import tempfile
import time
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.deps import ADMIN_COOKIE
from app.main import create_app, env_admin_id
from app.security import create_token, hash_password

API = '/api/v1'
PW = 'mirzokhid-test-1'  # testdagi parol (haqiqiy parol kodda yo‘q)


def make_app(**over):
    """Alohida DATA_DIR va sozlamalar bilan ilova (Render’dagi kabi)."""
    base = get_settings().model_dump()
    data_dir = over.pop('DATA_DIR', None) or Path(tempfile.mkdtemp(prefix='tg-admin-'))
    s = Settings(**{**base, 'DATA_DIR': data_dir, 'ADMIN_USERNAME': 'm_777', 'ADMIN_PASSWORD_HASH': hash_password(PW), **over})
    app = create_app(s)
    app.dependency_overrides[get_settings] = lambda: s
    return app, s


def put_cookie(c, value):
    c.cookies.clear()
    c.cookies.set(ADMIN_COOKIE, value, domain='testserver.local')


def login(c, password=PW, username='m_777'):
    return c.post(API + '/auth/admin/login', json={'username': username, 'password': password}, headers={'X-Requested-With': 'TalabaGo'})


def test_same_site_cookie_default_is_lax_host_only():
    app, _ = make_app(COOKIE_SECURE=True)
    with TestClient(app, base_url='https://support.example.uz') as c:
        r = login(c)
        assert r.status_code == 200
        sc = r.headers['set-cookie']
        assert sc.startswith(f'{ADMIN_COOKIE}=') and 'HttpOnly' in sc and 'Secure' in sc and 'SameSite=Lax' in sc
        assert 'Domain' not in sc, 'host-only: Vercel rewrite orqali panel domenida saqlanadi'
        assert r.headers['x-session-expires']
        for path in ('/auth/admin/me', '/crm/users', '/crm/settings', '/ads', '/crm/changes'):
            assert c.get(API + path).status_code == 200, path


def test_cross_site_mode_sets_samesite_none_secure_partitioned_and_cors():
    app, _ = make_app(COOKIE_SAMESITE='none', COOKIE_SECURE=False, CORS_ORIGINS='https://talabago-support.vercel.app')
    with TestClient(app, base_url='https://talabago-api.onrender.com') as c:
        origin = {'Origin': 'https://talabago-support.vercel.app'}
        pre = c.options(API + '/crm/users', headers={**origin, 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'x-requested-with'})
        assert pre.status_code == 200 and pre.headers['access-control-allow-credentials'] == 'true'
        assert pre.headers['access-control-allow-origin'] == 'https://talabago-support.vercel.app'
        r = c.post(API + '/auth/admin/login', json={'username': 'm_777', 'password': PW}, headers={**origin, 'X-Requested-With': 'TalabaGo'})
        sc = r.headers['set-cookie']
        assert 'SameSite=None' in sc and 'Secure' in sc and 'Partitioned' in sc, 'SameSite=None doim Secure bilan'
        assert 'x-session-expires' in r.headers['access-control-expose-headers'].lower()
        got = c.get(API + '/crm/users', headers=origin)
        assert got.status_code == 200 and got.headers['access-control-allow-origin'] == 'https://talabago-support.vercel.app'
        # boshqa sayt cookie bilan o‘zgartiruvchi so‘rov yubora olmaydi (CSRF sarlavhasi yo‘q)
        assert c.put(API + '/crm/settings', json={}, headers={'Origin': 'https://evil.example'}).status_code == 403


def test_sliding_session_renews_cookie_and_logout_clears():
    app, s = make_app()
    with TestClient(app) as c:
        assert login(c).status_code == 200
        fresh = c.get(API + '/crm/users')
        assert 'set-cookie' not in fresh.headers, 'yangi sessiyada har so‘rovda cookie qayta yozilmaydi'
        # muddati tugashiga oz qolgan token (faol administrator) → yangi cookie va yangi muddat
        aid = env_admin_id('m_777')
        old, old_exp = create_token(s.JWT_SECRET_KEY, aid, 'admin', timedelta(minutes=10), ver=0)
        put_cookie(c, old)
        r = c.get(API + '/crm/users')
        assert r.status_code == 200 and ADMIN_COOKIE in r.headers.get('set-cookie', '')
        new_exp = r.headers['x-session-expires']
        assert new_exp > old_exp.isoformat()
        me = c.get(API + '/auth/admin/me').json()
        assert me['expiresAt'] >= new_exp[:19]
        # muddati o‘tgan token → 401
        expired, _ = create_token(s.JWT_SECRET_KEY, aid, 'admin', timedelta(seconds=-5), ver=0)
        put_cookie(c, expired)
        assert c.get(API + '/crm/users').status_code == 401
        assert login(c).status_code == 200
        out = c.post(API + '/auth/admin/logout', headers={'X-Requested-With': 'TalabaGo'})
        assert out.status_code == 204 and 'Max-Age=0' in out.headers['set-cookie']
        c.cookies.clear()
        assert c.get(API + '/crm/users').status_code == 401


def test_env_password_hash_rotation_and_restart_stability():
    data = Path(tempfile.mkdtemp(prefix='tg-admin-'))
    app, _ = make_app(DATA_DIR=data)
    with TestClient(app) as c:
        assert login(c).status_code == 200
        assert login(c, username='M_777').status_code == 200, 'login katta-kichik harfga sezgir emas'
        admins = json.loads((data / 'db' / 'admins.json').read_text())
        assert [a['id'] for a in admins] == [env_admin_id('m_777')]
        assert PW not in json.dumps(admins) and 'envHashApplied' in admins[0]
        cookie = c.cookies.get(ADMIN_COOKIE)

    # 1) xuddi shu xesh bilan qayta ishga tushish — sessiya saqlanadi
    app2, _ = make_app(DATA_DIR=data, ADMIN_PASSWORD_HASH=json.loads((data / 'db' / 'admins.json').read_text())[0]['passwordHash'])
    with TestClient(app2) as c:
        put_cookie(c, cookie)
        assert c.get(API + '/crm/users').status_code == 200

    # 2) disk tozalandi (Render free / ephemeral) — admin qayta yaratiladi, ID o‘sha → eski cookie ishlaydi
    for f in (data / 'db').glob('admins*.json'):
        f.unlink()
    app3, s3 = make_app(DATA_DIR=data)
    with TestClient(app3) as c:
        put_cookie(c, cookie)
        assert c.get(API + '/crm/users').status_code == 200, 'qayta yaratilgan admin ID’si o‘zgarmagan'
        # panelda parol o‘zgartirildi → keyingi qayta ishga tushishda muhit xeshi uni qaytarib yozmaydi
        assert c.post(API + '/auth/admin/password', json={'current': PW, 'next': 'panel-parol-2'}, headers={'X-Requested-With': 'TalabaGo'}).status_code == 204
        cookie = c.cookies.get(ADMIN_COOKIE)
    app4, _ = make_app(DATA_DIR=data, ADMIN_PASSWORD_HASH=s3.ADMIN_PASSWORD_HASH)
    with TestClient(app4) as c:
        assert login(c, 'panel-parol-2').status_code == 200
        assert login(c, PW).status_code == 401

    # 3) Render’da ADMIN_PASSWORD_HASH yangi parol xeshiga almashtirildi → parol yangilanadi, eski sessiyalar bekor
    app5, _ = make_app(DATA_DIR=data, ADMIN_PASSWORD_HASH=hash_password('yangi-parol-3'))
    with TestClient(app5) as c:
        put_cookie(c, cookie)
        assert c.get(API + '/crm/users').status_code == 401, 'parol almashganda eski sessiya bekor'
        c.cookies.clear()
        assert login(c, 'panel-parol-2').status_code == 401
        assert login(c, 'yangi-parol-3').status_code == 200


def test_invalid_env_hash_is_ignored_safely():
    app, _ = make_app(ADMIN_PASSWORD_HASH='ochiq-parol-123')  # ochiq parol xato bilan yozilsa — qabul qilinmaydi
    with TestClient(app) as c:
        assert login(c, 'ochiq-parol-123').status_code == 401


def test_admin_login_lockout_per_username_across_ips():
    app, _ = make_app()
    with TestClient(app) as c:
        codes = [c.post(API + '/auth/admin/login', json={'username': 'm_777', 'password': 'xato-parol'},
                        headers={'X-Forwarded-For': f'10.0.0.{i}'}).status_code for i in range(22)]
        assert codes[0] == 401 and codes[-1] == 429, 'IP almashtirib parol tanlash 20 urinishdan keyin to‘xtaydi'


def test_changes_endpoint_tracks_collection_versions(admin, client):
    assert client.get(API + '/crm/changes').status_code == 401
    v1 = admin.get(API + '/crm/changes').json()['versions']
    assert set(v1) >= {'users', 'jobs', 'houses', 'applications', 'requests', 'tickets', 'complaints', 'settings', 'ads', 'courses', 'progress'}
    time.sleep(0.02)
    from conftest import register
    register(client, 'student')
    v2 = admin.get(API + '/crm/changes').json()['versions']
    assert v2['users'] != v1['users'] and v2['jobs'] == v1['jobs']
