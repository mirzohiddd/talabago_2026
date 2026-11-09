"""Uch rolning to‘liq funksiyalari va audit davomida tuzatilgan xatolar uchun regressiya testlari."""
import json
from datetime import datetime, timedelta, timezone

from conftest import JOB, SENT, png_bytes, register, upload

API = '/api/v1'


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def set_moderation(admin, on: bool):
    s = admin.get(API + '/crm/settings').json()
    s['system']['moderation'] = on
    assert admin.put(API + '/crm/settings', json=s).status_code == 200


def house_payload(client, h):
    photos = [upload(client, h).json()['url'] for _ in range(3)]
    return {'title': 'Talabalar uchun xona', 'type': 'room', 'photos': photos, 'city': 'Toshkent', 'district': 'Yunusobod', 'address': 'Amir Temur 1',
            'rooms': 1, 'price': 1_500_000, 'audience': 'any', 'capacity': 2, 'freeSpots': 1, 'description': 'Metroga yaqin, jihozlangan toza xona.',
            'phone': '+998 90 111 22 33'}


def test_employer_full_listing_lifecycle(client, admin):
    eh, _, _ = register(client, 'employer')
    sh, _, _ = register(client, 'student')
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    assert job['status'] == 'pending'
    assert client.get(API + f'/jobs/{job["id"]}', headers=sh).status_code == 404, 'tasdiqlanmagan e’lon talabaga ko‘rinmaydi'
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    # tahrirlash → moderatsiya yoqilgan bo‘lsa qayta tekshiruvga tushadi
    upd = client.patch(API + f'/employer/jobs/{job["id"]}', headers=eh, json={**JOB, 'title': 'Barista (kechki)'}).json()
    assert upd['title'] == 'Barista (kechki)' and upd['status'] == 'pending'
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    # yopish / qayta ochish
    assert client.patch(API + f'/employer/jobs/{job["id"]}/active', headers=eh, json={'active': False}).json()['status'] == 'closed'
    assert job['id'] not in [j['id'] for j in client.get(API + '/jobs', headers=sh).json()]
    assert client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={}).status_code == 404, 'yopilgan vakansiyaga ariza yo‘q'
    assert client.patch(API + f'/employer/jobs/{job["id"]}/active', headers=eh, json={'active': True}).json()['status'] == 'active'
    # nusxa: moderatsiya yoqiq → tekshiruvda; o‘chiq → darhol aktiv (avval doim “pending” qolib ketardi)
    assert client.post(API + f'/employer/jobs/{job["id"]}/duplicate', headers=eh).json()['status'] == 'pending'
    set_moderation(admin, False)
    try:
        dup = client.post(API + f'/employer/jobs/{job["id"]}/duplicate', headers=eh).json()
        assert dup['status'] == 'active' and dup['approvedAt'] and dup['views'] == 0
        assert client.post(API + '/employer/jobs', headers=eh, json=JOB).json()['status'] == 'active'
    finally:
        set_moderation(admin, True)
    # filtr va qidiruv
    mine = client.get(API + '/employer/jobs', headers=eh, params={'status': 'pending'}).json()
    assert mine and all(x['status'] == 'pending' for x in mine)
    assert client.get(API + '/employer/jobs', headers=eh, params={'q': 'barista'}).json()
    # o‘chirish: saqlanganlardan ham olib tashlanadi
    client.post(API + f'/jobs/{job["id"]}/save', headers=sh)
    assert client.delete(API + f'/employer/jobs/{job["id"]}', headers=eh).status_code == 204
    assert client.get(API + '/jobs', headers=sh, params={'saved': 'true'}).json() == []
    # boshqa ish beruvchi begona e’lonni o‘zgartira olmaydi
    eh2, _, _ = register(client, 'employer')
    other = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    for r in (client.patch(API + f'/employer/jobs/{other["id"]}', headers=eh2, json=JOB),
              client.patch(API + f'/employer/jobs/{other["id"]}/active', headers=eh2, json={'active': False}),
              client.delete(API + f'/employer/jobs/{other["id"]}', headers=eh2)):
        assert r.status_code == 404


def test_student_save_apply_withdraw_and_statuses(client, admin):
    eh, _, _ = register(client, 'employer')
    sh, student, _ = register(client, 'student', university='TDIU')
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    assert client.post(API + f'/jobs/{job["id"]}/save', headers=sh).json() is True
    listed = client.get(API + '/jobs', headers=sh, params={'saved': 'true'}).json()
    assert [j['id'] for j in listed] == [job['id']] and listed[0]['saved']
    assert client.post(API + f'/jobs/{job["id"]}/save', headers=sh).json() is False
    assert client.post(API + f'/jobs/{job["id"]}/save', headers=eh).status_code == 403, 'saqlash faqat talaba uchun'
    # filtrlar
    assert client.get(API + '/jobs', headers=sh, params={'type': 'daily'}).json() == []
    assert client.get(API + '/jobs', headers=sh, params={'workTime': 'evening', 'format': 'offline', 'q': 'ofitsiant'}).json()
    assert client.get(API + '/jobs', headers=sh, params={'salary': '5'}).json() == [], '25 000/soat ≈ 4 mln/oy < 5 mln'
    # ariza → ko‘rildi → suhbat → qabul
    app = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={'message': 'Kechki smenaga tayyorman'}).json()
    assert client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={}).status_code == 409
    assert client.get(API + '/jobs', headers=sh).json()[0]['applied'] is True
    assert client.patch(API + f'/employer/applications/{app["id"]}', headers=eh, json={'status': 'interview'}).status_code == 422, 'suhbat vaqti majburiy'
    SENT.clear()
    r = client.patch(API + f'/employer/applications/{app["id"]}', headers=eh, json={'status': 'interview', 'interviewAt': '2026-11-20T10:00'})
    assert r.json()['status'] == 'interview' and r.json()['interviewAt'] == '2026-11-20T10:00'
    mine = client.get(API + '/me/applications', headers=sh).json()
    assert mine[0]['status'] == 'interview' and [h['status'] for h in mine[0]['history']] == ['sent', 'interview']
    notes = client.get(API + '/notifications', headers=sh).json()
    assert notes and notes[0]['title'] == 'Sizni suhbatga chaqirishdi'
    # bekor qilish
    assert client.post(API + f'/me/applications/{app["id"]}/withdraw', headers=sh).json()['status'] == 'withdrawn'
    assert client.post(API + f'/me/applications/{app["id"]}/withdraw', headers=sh).status_code == 409
    assert client.get(API + '/employer/applications', headers=eh).json() == [], 'bekor qilingan ariza ish beruvchiga ko‘rinmaydi'
    # qayta ariza yuborish mumkin
    app2 = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={}).json()
    assert client.patch(API + f'/employer/applications/{app2["id"]}', headers=eh, json={'status': 'declined', 'note': 'Joy to‘ldi'}).json()['status'] == 'declined'
    assert client.post(API + f'/me/applications/{app2["id"]}/withdraw', headers=sh).status_code == 409
    # boshqa talaba/ish beruvchi begona arizaga tegolmaydi
    sh2, _, _ = register(client, 'student')
    eh2, _, _ = register(client, 'employer')
    assert client.post(API + f'/me/applications/{app2["id"]}/withdraw', headers=sh2).status_code == 404
    assert client.patch(API + f'/employer/applications/{app2["id"]}', headers=eh2, json={'status': 'accepted'}).status_code == 404
    assert client.get(API + f'/users/{student["id"]}/public', headers=eh2).status_code == 403
    assert client.get(API + f'/users/{student["id"]}/public', headers=eh).json()['university'] == 'TDIU'


def test_landlord_occupancy_requests_and_filters(client, admin):
    lh, _, _ = register(client, 'landlord')
    sh, _, _ = register(client, 'student')
    house = client.post(API + '/landlord/houses', headers=lh, json=house_payload(client, lh)).json()
    admin.post(API + f'/crm/houses/{house["id"]}/approve')
    assert client.get(API + '/houses', headers=sh, params={'onlyFree': 'true', 'price': '2', 'rooms': '1'}).json()[0]['id'] == house['id']
    assert client.get(API + '/houses', headers=sh, params={'price': '1'}).json() == []
    got = client.get(API + f'/houses/{house["id"]}', headers=sh).json()
    assert got['owner']['phone'] and 'passwordHash' not in json.dumps(got)
    # band qilish
    assert client.patch(API + f'/landlord/houses/{house["id"]}/occupancy', headers=lh, json={'occupancy': 'occupied'}).json()['occupancy'] == 'occupied'
    assert client.get(API + '/houses', headers=sh, params={'onlyFree': 'true'}).json() == []
    client.patch(API + f'/landlord/houses/{house["id"]}/occupancy', headers=lh, json={'occupancy': 'free'})
    # so‘rov
    assert client.post(API + f'/houses/{house["id"]}/requests', headers=sh, json={'moveIn': '01.12.2026'}).status_code == 422
    req = client.post(API + f'/houses/{house["id"]}/requests', headers=sh, json={'moveIn': '2026-12-01', 'term': '6', 'message': 'Salom'}).json()
    assert client.get(API + '/landlord/requests', headers=lh).json()[0]['student']['name']
    assert client.get(API + '/houses', headers=sh).json()[0]['requested'] is True
    assert client.patch(API + f'/landlord/requests/{req["id"]}', headers=lh, json={'status': 'accepted'}).json()['status'] == 'accepted'
    assert client.get(API + '/me/rental-requests', headers=sh).json()[0]['status'] == 'accepted'
    assert client.post(API + f'/me/rental-requests/{req["id"]}/withdraw', headers=sh).status_code == 409
    # boshqa uy egasi
    lh2, _, _ = register(client, 'landlord')
    assert client.patch(API + f'/landlord/houses/{house["id"]}/occupancy', headers=lh2, json={'occupancy': 'occupied'}).status_code == 404
    assert client.patch(API + f'/landlord/requests/{req["id"]}', headers=lh2, json={'status': 'declined'}).status_code == 404
    # rol cheklovlari
    assert client.post(API + '/landlord/houses', headers=sh, json=house_payload(client, lh)).status_code == 403
    assert client.post(API + '/employer/jobs', headers=lh, json=JOB).status_code == 403
    assert client.post(API + f'/houses/{house["id"]}/requests', headers=lh, json={'moveIn': '2026-12-01'}).status_code == 403


def test_blocked_owner_listings_hidden(client, admin):
    eh, emp, _ = register(client, 'employer')
    sh, _, _ = register(client, 'student')
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    assert job['id'] in [j['id'] for j in client.get(API + '/jobs', headers=sh).json()]
    admin.patch(API + f'/crm/users/{emp["id"]}', json={'status': 'blocked'})
    try:
        assert job['id'] not in [j['id'] for j in client.get(API + '/jobs', headers=sh).json()]
        assert client.get(API + f'/jobs/{job["id"]}', headers=sh).status_code == 404
        assert client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={}).status_code == 404
    finally:
        admin.patch(API + f'/crm/users/{emp["id"]}', json={'status': 'active'})
    assert client.get(API + f'/jobs/{job["id"]}', headers=sh).status_code == 200


def test_notification_preferences_are_enforced_server_side(client, admin):
    from app.telegram import sign_init_data
    from conftest import BOT
    init = sign_init_data({'id': 55501, 'first_name': 'Pref'}, BOT)
    r = client.post(API + '/auth/register', json={'role': 'student', 'firstName': 'Pref', 'phone': '935550101', 'initData': init})
    sh = {'Authorization': f'Bearer {r.json()["token"]}'}
    eh, _, _ = register(client, 'employer')
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    app = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={}).json()
    SENT.clear()
    client.patch(API + f'/employer/applications/{app["id"]}', headers=eh, json={'status': 'accepted'})
    assert any(p.get('chat_id') == 55501 for m, p in SENT if m == 'sendMessage'), 'standart holatda Telegram xabari boradi'
    me = client.patch(API + '/users/me', headers=sh, json={'notifyTelegram': False, 'notifyApp': False}).json()
    assert me['notifyTelegram'] is False and me['notifyApp'] is False
    app2 = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={})
    assert app2.status_code == 409  # allaqachon qabul qilingan ariza bor
    SENT.clear()
    client.patch(API + f'/employer/applications/{app["id"]}', headers=eh, json={'status': 'declined'})
    assert not any(p.get('chat_id') == 55501 for m, p in SENT if m == 'sendMessage'), 'o‘chirilgan bo‘lsa Telegram xabari yuborilmaydi'
    assert client.get(API + '/notifications', headers=sh).json() == []
    client.patch(API + '/users/me', headers=sh, json={'notifyApp': True})
    assert client.get(API + '/notifications', headers=sh).json()


def test_listing_contact_validation(client):
    eh, _, _ = register(client, 'employer')
    assert client.post(API + '/employer/jobs', headers=eh, json={**JOB, 'telegram': 'bad name!'}).status_code == 422
    assert client.post(API + '/employer/jobs', headers=eh, json={**JOB, 'phone': '12345'}).status_code == 422
    ok = client.post(API + '/employer/jobs', headers=eh, json={**JOB, 'telegram': 'acme_hr', 'phone': '901234567'}).json()
    assert ok['telegram'] == '@acme_hr' and ok['phone'] == '+998 90 123 45 67'
    assert client.post(API + '/employer/jobs', headers=eh, json={**JOB, 'telegram': ''}).json()['telegram'] is None


def test_ads_stats_only_count_live_and_naive_dates(client, admin):
    now = datetime.now(timezone.utc)

    def make(**k):
        d = {'name': 'Statistika', 'type': 'image', 'title': 'Kurs', 'link': 'https://example.uz', 'placements': ['all'],
             'startAt': iso(now - timedelta(hours=1)), 'endAt': iso(now + timedelta(days=1)), 'enabled': True, **k}
        return admin.post(API + '/ads', data={'data': json.dumps(d)}, files={'file': ('b.png', png_bytes(600, 360), 'image/png')})

    live = make().json()
    future = make(name='Kelajak', startAt=iso(now + timedelta(days=1)), endAt=iso(now + timedelta(days=2))).json()
    # vaqt zonasiz sana — 500 emas, UTC deb qabul qilinadi
    naive = make(name='Naive', startAt=(now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'), endAt=(now + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%S'))
    assert naive.status_code == 201, naive.text
    assert client.get(API + '/ads/active').status_code == 200
    for ad in (live, future):
        client.post(API + f'/ads/{ad["id"]}/view')
        client.post(API + f'/ads/{ad["id"]}/click')
    rows = {a['id']: a for a in admin.get(API + '/ads').json()}
    assert rows[live['id']]['views'] == 1 and rows[live['id']]['clicks'] == 1 and rows[live['id']]['state'] == 'live'
    assert rows[future['id']]['views'] == 0 and rows[future['id']]['clicks'] == 0 and rows[future['id']]['state'] == 'scheduled'
    # o‘chirilgan reklama statistikasi o‘smaydi
    admin.patch(API + f'/ads/{live["id"]}/enabled', json={'enabled': False})
    client.post(API + f'/ads/{live["id"]}/click', headers={'X-Forwarded-For': '1.2.3.4'})
    assert next(a for a in admin.get(API + '/ads').json() if a['id'] == live['id'])['state'] == 'inactive'
    assert admin.patch(API + '/ads/order', json={'ids': 'not-a-list'}).status_code == 422
    for a in admin.get(API + '/ads').json():
        admin.delete(API + f'/ads/{a["id"]}')


def test_health_does_not_leak_counts(client):
    body = client.get(API + '/health').json()
    assert body['ok'] and 'users' not in body
