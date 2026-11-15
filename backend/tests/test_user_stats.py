"""Dashboard “Jami foydalanuvchilar”: 41 (eski, tiklanmagan baza) + boshlang‘ich paytdan keyin ro‘yxatdan o‘tgan haqiqiy foydalanuvchilar.
Soxta profil yaratilmaydi, mavjudlar ikki marta hisoblanmaydi, boshlang‘ich hisob qayta ishga tushirishdan keyin ham saqlanadi."""
from fastapi.testclient import TestClient

from conftest import register

from app import stats
from app.config import Settings, get_settings
from app.main import create_app

API = '/api/v1'


def test_baseline_saved_in_meta_once(admin):
    s = admin.get(API + '/crm/stats/users').json()
    assert s['baseline'] == 41 and s['since']
    assert s['total'] == max(41, s['existingAtStart']) + s['newSinceBaseline']
    assert s['unrecovered'] == max(0, 41 - s['existingAtStart'])
    assert s['storage']['platform'] == 'local'


def test_new_registration_increments_total(admin, client):
    before = admin.get(API + '/crm/stats/users').json()
    users_before = len(admin.get(API + '/crm/users').json())
    register(client, 'student')
    after = admin.get(API + '/crm/stats/users').json()
    assert after['total'] == before['total'] + 1                      # 41 → 42 → 43 …
    assert after['newSinceBaseline'] == before['newSinceBaseline'] + 1
    assert after['existingAtStart'] == before['existingAtStart']
    assert len(admin.get(API + '/crm/users').json()) == users_before + 1   # bazaga faqat haqiqiy yangi foydalanuvchi qo‘shildi (soxta profil yo‘q)


def test_restart_keeps_baseline(admin):
    before = admin.get(API + '/crm/stats/users').json()
    app2 = create_app(get_settings())
    with TestClient(app2) as c:                                          # lifespan → bootstrap qayta ishlaydi
        r = c.post(API + '/auth/admin/login', json={'username': 'root', 'password': 'root-password-1'})
        assert r.status_code == 200
        again = c.get(API + '/crm/stats/users', headers={'X-Requested-With': 'TalabaGo'}).json()
    assert again['since'] == before['since'] and again['total'] == before['total']


def test_stats_requires_admin(client):
    assert client.get(API + '/crm/stats/users').status_code in (401, 403)


def _settings(**kw):
    return Settings(JWT_SECRET_KEY='x' * 40, **kw)


def test_formula_unit():
    S = _settings()
    since = '2026-11-12T10:00:00.000Z'
    meta = {'usersBaseline': {'count': 41, 'since': since, 'existingAtStart': 3}}
    old = [{'id': f'o{i}', 'createdAt': '2026-11-10T00:00:00Z'} for i in range(3)] + [{'id': 'nocreated'}]   # vaqtsiz yozuv — eski
    new = [{'id': f'n{i}', 'createdAt': f'2026-11-12T1{i + 1}:00:00Z'} for i in range(2)]
    r = stats.user_totals(meta, old + new, S)
    assert (r['total'], r['newSinceBaseline'], r['unrecovered']) == (43, 2, 38)
    # bazadagilar 41 dan ko‘p bo‘lsa — ular yo‘qolmaydi, ikki marta ham qo‘shilmaydi
    meta45 = {'usersBaseline': {'count': 41, 'since': since, 'existingAtStart': 45}}
    assert stats.user_totals(meta45, new, S)['total'] == 47


def test_ensure_baseline_does_not_overwrite_and_env_override():
    S = _settings()
    db = {'meta': {}, 'users': [{'id': 'a', 'createdAt': '2026-01-01T00:00:00Z'}]}
    b1 = stats.ensure_user_baseline(db, S)
    assert b1['count'] == 41 and b1['existingAtStart'] == 1
    assert stats.ensure_user_baseline(db, S)['since'] == b1['since']    # ikkinchi chaqiruv o‘zgartirmaydi
    S2 = _settings(USERS_BASELINE_AT='2025-12-31T00:00:00Z')
    r = stats.user_totals(db['meta'], db['users'], S2)                  # env ustun: undan keyingi foydalanuvchi — yangi
    assert r['since'] == '2025-12-31T00:00:00Z' and r['total'] == 42
    assert stats.user_totals(db['meta'], db['users'], _settings(USERS_BASELINE_AT='notadate'))['since'] == b1['since']
