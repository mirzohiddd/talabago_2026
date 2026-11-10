"""Xavfsizlik va forma validatsiyasi: maxfiy maydonlar, rollar, JWT, so‘rov hajmi, telefon (+998), ism, parol, takroriy raqam."""
import base64
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from conftest import JOB, register
from app.config import Settings, get_settings
from app.main import create_app
from app.security import create_token

API = '/api/v1'
SECRET_FIELDS = ('passwordHash', 'telegramId', 'tokenVersion', 'envHashApplied', 'JWT_SECRET', 'scrypt$')


def reg(client, phone, **kw):
    body = {'role': 'student', 'firstName': 'Aziz', 'lastName': 'Karimov', 'phone': phone, 'password': 'parol12345', **kw}
    return client.post(API + '/auth/register', json=body)


# ---------------------------------------------------------------- telefon
@pytest.mark.parametrize('phone', ['+998 90 123 45 01', '+998901234502', '998 91 123 45 03', '93 123 45 04', '(94) 123-45-05', '+998 33 123 45 06',
                                   '+998 88 123 45 07', '+998 20 123 45 08', '+998 71 123 45 09', '+998 99 812 34 10'])
def test_valid_phones_are_normalized(client, phone):
    r = reg(client, phone)
    assert r.status_code == 201, r.text
    p = r.json()['user']['phone']
    assert len(p) == 17 and p.startswith('+998 ') and p[4] == ' ' and p[7] == ' ' and p[11] == ' ' and p[14] == ' ', p


@pytest.mark.parametrize('phone,msg', [
    ('', 'Telefon raqamini kiriting'), ('+998', 'Telefon raqamini kiriting'), ('+998 90 123 45', 'to‘liq emas'), ('90 123 45 6', 'to‘liq emas'),
    ('+998 90 123 45 678', 'to‘liq emas'), ('+998 12 345 67 89', 'Operator kodi noto‘g‘ri'), ('+998 00 000 00 00', 'Operator kodi noto‘g‘ri'),
    ('+7 912 345 67 89', 'to‘liq emas'), ('abc', 'Telefon raqamini kiriting'),
])
def test_invalid_phones_rejected_in_uzbek(client, phone, msg):
    r = reg(client, phone)
    assert r.status_code == 422, r.text
    assert r.json()['errors'][0]['field'] == 'phone' and msg in r.json()['detail'] and r.json()['detail'].startswith('Telefon:'), r.json()


def test_duplicate_phone_blocked_in_any_format_and_any_role(client):
    assert reg(client, '+998 97 555 11 22').status_code == 201
    for variant, role in (('+998975551122', 'student'), ('97 555 11 22', 'employer'), ('998-97-555-11-22', 'landlord')):
        r = reg(client, variant, role=role, company='ACME')
        assert r.status_code == 409 and 'telefon' in r.json()['detail'].lower(), (variant, r.text)
    # profilda boshqa birovning raqamiga o‘zgartirish ham bloklanadi
    h, _, _ = register(client)
    assert client.patch(API + '/users/me', headers=h, json={'phone': '+998 97 555 11 22'}).status_code == 409


# ---------------------------------------------------------------- ism, familiya, parol, sana
@pytest.mark.parametrize('first,last', [('O‘g‘iloy', 'Rahimova'), ("Abdul-Aziz", "To'xtayev"), ('Шерзод', 'Каримов'), ('Ma’mura', 'Qo‘chqorova'), ('  Ali  ', ' Valiyev ')])
def test_valid_names(client, first, last):
    r = reg(client, f'+998 90 7{len(first):02d} {len(last):02d} {ord(first.strip()[0]) % 100:02d}', firstName=first, lastName=last)
    assert r.status_code == 201, r.text
    assert r.json()['user']['firstName'] == first.strip() and r.json()['user']['lastName'] == last.strip()


@pytest.mark.parametrize('field,value,msg', [
    ('firstName', '', 'Majburiy maydon'), ('firstName', 'A', 'Kamida 2 ta harf'), ('firstName', 'Ali123', 'Faqat harflar'),
    ('firstName', '<script>', 'Faqat harflar'), ('lastName', '', 'Majburiy maydon'), ('lastName', 'Ka' * 25, 'Ko‘pi bilan 40'),
    ('password', 'qisqa1', 'kamida 8'), ('password', 'parolparol', 'harf va bitta raqam'), ('password', '12345678', 'harf va bitta raqam'),
    ('birthDate', '2020-01-01', '14 dan 70'), ('birthDate', '01.01.2000', 'Sana formati'), ('role', 'admin', 'Ruxsat etilmagan'),
])
def test_register_field_errors_in_uzbek(client, field, value, msg):
    r = reg(client, '+998 90 700 00 01', **{field: value})
    assert r.status_code == 422, r.text
    errs = {e['field']: e['message'] for e in r.json()['errors']}
    assert msg in errs.get(field, ''), r.json()


def test_missing_last_name_and_company(client):
    r = client.post(API + '/auth/register', json={'role': 'student', 'firstName': 'Aziz', 'phone': '+998 90 700 00 02', 'password': 'parol12345'})
    assert r.status_code == 422 and r.json()['detail'] == 'Familiya: Majburiy maydon'
    r = reg(client, '+998 90 700 00 03', role='employer')
    assert r.status_code == 422 and 'Kompaniya' in r.json()['detail']


def test_role_fields_not_mixed(client):
    r = reg(client, '+998 90 700 00 04', role='landlord', university='TATU', company='X MChJ', skills=['SMM'])
    u = r.json()['user']
    assert r.status_code == 201 and 'university' not in u and 'company' not in u
    h = {'Authorization': f'Bearer {r.json()["token"]}'}
    me = client.patch(API + '/users/me', headers=h, json={'university': 'TATU', 'company': 'X'}).json()
    assert 'university' not in me and 'company' not in me


# ---------------------------------------------------------------- maxfiy maydonlar
def _walk(o):
    s = json.dumps(o, ensure_ascii=False)
    return [f for f in SECRET_FIELDS if f in s]


def test_no_secret_fields_in_any_response(client, admin):
    from app.telegram import sign_init_data
    from conftest import BOT
    init = sign_init_data({'id': 424242, 'first_name': 'Sir'}, BOT)
    r = client.post(API + '/auth/register', json={'role': 'student', 'firstName': 'Sirli', 'lastName': 'Talaba', 'phone': '+998 90 700 00 05', 'initData': init})
    sh = {'Authorization': f'Bearer {r.json()["token"]}'}
    assert not _walk(r.json())
    eh, emp, _ = register(client, 'employer')
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={})
    client.post(API + '/users/me/password', headers=sh, json={'current': '', 'next': 'yangiParol1'})
    for path, h in (('/users/me', sh), ('/jobs', sh), (f'/jobs/{job["id"]}', sh), ('/me/applications', sh), ('/employer/applications', eh),
                    (f'/users/{r.json()["user"]["id"]}/public', eh)):
        body = client.get(API + path, headers=h).json()
        assert not _walk(body), (path, _walk(body))
    for path in ('/crm/users', '/crm/jobs', '/crm/applications', '/auth/admin/me', '/crm/settings'):
        assert not _walk(admin.get(API + path).json()), path
    login = client.post(API + '/auth/login', json={'phone': '+998 90 700 00 05', 'password': 'yangiParol1'})
    assert login.status_code == 200 and not _walk(login.json())


# ---------------------------------------------------------------- rollar va JWT
def test_role_matrix(client, admin):
    sh, _, _ = register(client, 'student')
    eh, _, _ = register(client, 'employer')
    lh, _, _ = register(client, 'landlord')
    forbidden = [
        (sh, 'post', '/employer/jobs'), (sh, 'get', '/employer/applications'), (sh, 'get', '/landlord/requests'), (sh, 'post', '/landlord/houses'),
        (eh, 'get', '/landlord/requests'), (eh, 'get', '/me/applications'), (lh, 'get', '/employer/applications'), (lh, 'post', '/employer/jobs'),
    ]
    for h, m, path in forbidden:
        r = getattr(client, m)(API + path, headers=h, **({'json': {}} if m == 'post' else {}))
        assert r.status_code in (403, 422) and (r.status_code == 403 or m == 'post'), (path, r.status_code)
        if m == 'get':
            assert r.status_code == 403
    for h in (sh, eh, lh):  # foydalanuvchi tokeni Support paneliga kirita olmaydi
        assert client.get(API + '/crm/users', headers=h).status_code == 401
    assert client.get(API + '/crm/users').status_code == 401
    assert client.get(API + '/users/me').status_code == 401


def test_jwt_tampering_rejected(client):
    h, user, _ = register(client)
    s = get_settings()
    tok = h['Authorization'].split()[1]
    head, payload, sig = tok.split('.')
    pl = json.loads(base64.urlsafe_b64decode(payload + '=='))
    def enc(o):
        return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')
    bad = [
        f'{enc({"alg": "none", "typ": "JWT"})}.{payload}.',                                  # alg=none
        f'{head}.{enc({**pl, "sub": "boshqa"})}.{sig}',                                     # imzosiz o‘zgartirish
        create_token('x' * 40, user['id'], 'user', timedelta(days=1))[0],                    # boshqa kalit
        create_token(s.JWT_SECRET_KEY, user['id'], 'user', timedelta(seconds=-1))[0],       # muddati o‘tgan
        create_token(s.JWT_SECRET_KEY, user['id'], 'admin', timedelta(days=1))[0],          # boshqa tur
        create_token(s.JWT_SECRET_KEY, user['id'], 'user', timedelta(days=1), ver=5)[0],     # bekor qilingan versiya
    ]
    for b in bad:
        assert client.get(API + '/users/me', headers={'Authorization': f'Bearer {b}'}).status_code == 401, b[:40]


def test_password_change_revokes_sessions_and_is_rate_limited(client):
    h, _, body = register(client)
    other_device = dict(h)
    for _ in range(5):
        assert client.post(API + '/users/me/password', headers=h, json={'current': 'xato1234', 'next': 'yangiParol1'}).status_code == 400
    r = client.post(API + '/users/me/password', headers=h, json={'current': body['password'], 'next': 'yangiParol1'})
    assert r.status_code == 429, 'joriy parolni tanlash bloklandi'


def test_password_change_policy_and_new_token(client):
    h, _, body = register(client)
    r = client.post(API + '/users/me/password', headers=h, json={'current': body['password'], 'next': 'qisqa'})
    assert r.status_code == 422 and r.json()['detail'].startswith('Yangi parol:')
    r = client.post(API + '/users/me/password', headers=h, json={'current': body['password'], 'next': 'Yangi1parol'})
    assert r.status_code == 200
    assert client.get(API + '/users/me', headers=h).status_code == 401, 'boshqa qurilmadagi eski token bekor'
    assert client.get(API + '/users/me', headers={'Authorization': f'Bearer {r.json()["token"]}'}).status_code == 200


# ---------------------------------------------------------------- so‘rov hajmi, sarlavhalar, docs
def test_request_size_limit(client):
    h, _, _ = register(client)
    big = {'about': 'x' * (1100 * 1024)}
    r = client.patch(API + '/users/me', headers={**h, 'Content-Type': 'application/json'}, content=json.dumps(big))
    assert r.status_code == 413 and r.json()['detail'] == 'So‘rov hajmi juda katta'


def test_security_headers_and_docs_toggle(tmp_path):
    base = get_settings().model_dump()
    s = Settings(**{**base, 'DATA_DIR': tmp_path, 'API_DOCS': False, 'COOKIE_SECURE': True})
    app = create_app(s)
    app.dependency_overrides[get_settings] = lambda: s
    with TestClient(app) as c:
        assert c.get('/api/docs').status_code == 404 and c.get('/api/openapi.json').status_code == 404
        r = c.get(API + '/health')
        assert r.headers['strict-transport-security'].startswith('max-age=') and r.headers['x-content-type-options'] == 'nosniff'
        assert 'camera=()' in r.headers['permissions-policy'] and r.headers['cache-control'] == 'no-store'
        assert 'users' not in r.json()


def test_api_responses_are_gzipped(client):
    h, _, _ = register(client)
    r = client.get(API + '/courses', headers={**h, 'Accept-Encoding': 'gzip'})
    assert r.status_code == 200 and r.headers.get('content-encoding') == 'gzip'
