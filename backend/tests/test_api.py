"""Asosiy foydalanuvchi jarayonlari va barcha endpointlar uchun integratsion testlar."""
from datetime import datetime, timedelta, timezone

from app.telegram import sign_init_data

from conftest import BOT, JOB, SENT, png_bytes, register, upload

API = '/api/v1'


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


# ============================================================ auth
def test_health_and_public_config(client):
    assert client.get(API + '/health').json()['ok']
    cfg = client.get(API + '/public/config').json()
    assert cfg['platformName'] == 'TalabaGo' and cfg['telegramLogin'] is True


def test_register_login_and_duplicates(client):
    h, user, body = register(client, 'student', university='TATU', course=2, skills=['Excel'])
    assert 'passwordHash' not in user and user['phone'].startswith('+998 90')
    assert client.get(API + '/users/me', headers=h).json()['university'] == 'TATU'
    r = client.post(API + '/auth/register', json={**body, 'firstName': 'Boshqa'})
    assert r.status_code == 409
    assert client.post(API + '/auth/login', json={'phone': body['phone'], 'password': 'parol12345'}).status_code == 200
    assert client.post(API + '/auth/login', json={'phone': body['phone'], 'password': 'xato-parol'}).status_code == 401


def test_register_validation(client):
    r = client.post(API + '/auth/register', json={'role': 'student', 'firstName': 'Al', 'phone': '123', 'password': 'parol12345'})
    assert r.status_code == 422 and 'phone' in r.json()['detail']
    r = client.post(API + '/auth/register', json={'role': 'student', 'firstName': 'Ali', 'phone': '901234500'})
    assert r.status_code == 422, 'Telegram’siz parol majburiy'
    r = client.post(API + '/auth/register', json={'role': 'admin', 'firstName': 'Ali', 'phone': '901234501', 'password': 'parol12345'})
    assert r.status_code == 422
    r = client.post(API + '/auth/register', json={'role': 'employer', 'firstName': 'Ali', 'phone': '901234502', 'password': 'parol12345'})
    assert r.status_code == 422, 'ish beruvchi uchun kompaniya majburiy'


def test_login_lockout(client):
    _, _, body = register(client)
    for _ in range(5):
        assert client.post(API + '/auth/login', json={'phone': body['phone'], 'password': 'noto‘g‘ri1'}).status_code == 401
    r = client.post(API + '/auth/login', json={'phone': body['phone'], 'password': 'parol12345'})
    assert r.status_code == 429 and int(r.headers['retry-after']) > 0


def test_telegram_register_and_login(client):
    init = sign_init_data({'id': 987654, 'first_name': 'Tg', 'username': 'tg_user1'}, BOT)
    assert client.post(API + '/auth/telegram', json={'initData': init}).status_code == 404
    r = client.post(API + '/auth/register', json={'role': 'landlord', 'firstName': 'Tg', 'phone': '939998877', 'initData': init})
    assert r.status_code == 201 and r.json()['user']['telegram'] == '@tg_user1' and r.json()['user']['telegramLinked']
    r = client.post(API + '/auth/telegram', json={'initData': init})
    assert r.status_code == 200 and r.json()['user']['role'] == 'landlord'
    bad = init.replace('tg_user1', 'hacker')
    assert client.post(API + '/auth/telegram', json={'initData': bad}).status_code == 401


def test_unauthenticated_and_bad_token(client):
    assert client.get(API + '/users/me').status_code == 401
    assert client.get(API + '/jobs', headers={'Authorization': 'Bearer abc.def.ghi'}).status_code == 401


def test_profile_update_and_password(client):
    h, _, body = register(client)
    r = client.patch(API + '/users/me', headers=h, json={'faculty': 'Iqtisodiyot', 'skills': ['Excel', 'SMM'], 'telegram': 'yangi_user'})
    assert r.status_code == 200 and r.json()['telegram'] == '@yangi_user'
    assert client.patch(API + '/users/me', headers=h, json={'phone': 'abc'}).status_code == 422
    assert client.patch(API + '/users/me', headers=h, json={'cv': {'url': 'https://evil.com/x.pdf', 'name': 'x'}}).status_code == 422
    assert client.post(API + '/users/me/password', headers=h, json={'current': 'xato', 'next': 'yangiparol1'}).status_code == 400
    assert client.post(API + '/users/me/password', headers=h, json={'current': 'parol12345', 'next': 'yangiparol1'}).status_code == 204
    assert client.post(API + '/auth/login', json={'phone': body['phone'], 'password': 'yangiparol1'}).status_code == 200


# ============================================================ fayllar
def test_uploads_are_sniffed_and_reencoded(client, app):
    h, _, _ = register(client)
    r = upload(client, h, 'photo')
    assert r.status_code == 201 and r.json()['url'].endswith('.webp') and r.json()['mime'] == 'image/webp'
    img = client.get(r.json()['url'])
    assert img.status_code == 200 and img.content[:4] == b'RIFF' and img.headers['x-content-type-options'] == 'nosniff'
    assert upload(client, h, 'photo', data=b'MZ\x90\x00 fake exe', name='x.png').status_code == 415
    assert upload(client, h, 'cv', data=png_bytes(), name='cv.pdf').status_code == 415
    pdf = upload(client, h, 'cv', data=b'%PDF-1.4\n%test\n', name='../../cv.pdf')
    assert pdf.status_code == 201 and pdf.json()['name'] == 'cv.pdf'
    assert upload(client, h, 'photo', data=b'\x89PNG\r\n\x1a\n' + b'0' * (6 * 1024 * 1024)).status_code == 413
    assert upload(client, h, 'ad').status_code == 400, 'oddiy foydalanuvchi reklama fayli yuklay olmaydi'
    assert client.get('/media/../db/users.json').status_code == 404


# ============================================================ ish e’lonlari
def test_job_flow_moderation_application(client, admin):
    eh, emp, _ = register(client, 'employer')
    sh, stu, _ = register(client, 'student')
    assert client.post(API + '/employer/jobs', headers=sh, json=JOB).status_code == 403, 'talaba vakansiya qo‘sha olmaydi'
    assert client.post(API + '/employer/jobs', headers=eh, json={**JOB, 'description': 'qisqa'}).status_code == 422
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    assert job['status'] == 'pending'
    assert any(m == 'sendMessage' and p['chat_id'] == '777' for m, p in SENT), 'admin Telegram’da xabardor qilindi'
    assert all(j['id'] != job['id'] for j in client.get(API + '/jobs', headers=sh).json()), 'tasdiqlanmagan e’lon ko‘rinmaydi'
    assert client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={'message': 'Salom'}).status_code == 404

    assert admin.post(API + f'/crm/jobs/{job["id"]}/approve').json()['status'] == 'active'
    listed = client.get(API + '/jobs', headers=sh, params={'type': 'hourly', 'q': 'ofitsiant', 'district': 'Chilonzor'}).json()
    assert [j['id'] for j in listed] == [job['id']]
    assert client.get(API + '/jobs', headers=sh, params={'format': 'online'}).json() == [] or all(j['format'] == 'online' for j in client.get(API + '/jobs', headers=sh, params={'format': 'online'}).json())
    assert client.get(API + '/notifications', headers=eh).json()[0]['title'] == 'Vakansiya tasdiqlandi'

    assert client.post(API + f'/jobs/{job["id"]}/save', headers=sh).json() is True
    assert client.get(API + '/jobs', headers=sh, params={'saved': 'true'}).json()[0]['saved'] is True
    app_ = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={'message': 'Tayyorman'}).json()
    assert client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={}).status_code == 409
    assert client.get(API + '/jobs', headers=sh).json()[0]['applied'] is True

    inbox = client.get(API + '/employer/applications', headers=eh).json()
    assert inbox[0]['id'] == app_['id'] and inbox[0]['student']['name'].startswith('Test')
    assert client.get(API + f'/users/{stu["id"]}/public', headers=eh).status_code == 200
    other_h, _, _ = register(client, 'employer')
    assert client.get(API + f'/users/{stu["id"]}/public', headers=other_h).status_code == 403
    assert client.patch(API + f'/employer/applications/{app_["id"]}', headers=other_h, json={'status': 'accepted'}).status_code == 404
    assert client.patch(API + f'/employer/applications/{app_["id"]}', headers=eh, json={'status': 'interview'}).status_code == 422
    r = client.patch(API + f'/employer/applications/{app_["id"]}', headers=eh, json={'status': 'interview', 'interviewAt': '2026-12-01T10:00:00Z'})
    assert r.json()['status'] == 'interview' and len(r.json()['history']) == 2
    mine = client.get(API + '/me/applications', headers=sh).json()
    assert mine[0]['status'] == 'interview' and mine[0]['job']['title'] == JOB['title']
    assert client.get(API + '/notifications', headers=sh).json()[0]['title'] == 'Sizni suhbatga chaqirishdi'
    assert client.post(API + f'/me/applications/{app_["id"]}/withdraw', headers=sh).json()['status'] == 'withdrawn'
    assert client.get(API + '/employer/applications', headers=eh).json() == []

    # egasi: ro‘yxat, tahrir (qayta tekshiruv), nusxa, yopish, o‘chirish
    assert client.get(API + '/employer/jobs', headers=eh).json()[0]['applicationsCount'] == 0
    upd = client.patch(API + f'/employer/jobs/{job["id"]}', headers=eh, json={**JOB, 'title': 'Kafe ofitsianti v2'}).json()
    assert upd['status'] == 'pending' and upd['title'] == 'Kafe ofitsianti v2'
    assert client.patch(API + f'/employer/jobs/{job["id"]}', headers=other_h, json=JOB).status_code == 404
    dup = client.post(API + f'/employer/jobs/{job["id"]}/duplicate', headers=eh).json()
    assert dup['title'].endswith('(nusxa)') and dup['status'] == 'pending'
    assert client.patch(API + f'/employer/jobs/{job["id"]}/active', headers=eh, json={'active': False}).json()['status'] == 'closed'
    assert client.patch(API + f'/employer/jobs/{job["id"]}/active', headers=eh, json={'active': True}).json()['status'] == 'active'
    assert client.delete(API + f'/employer/jobs/{dup["id"]}', headers=eh).status_code == 204
    assert len(client.get(API + '/employer/jobs', headers=eh).json()) == 1


def test_admin_reject_with_reason_and_edit_delete(client, admin):
    eh, _, _ = register(client, 'employer')
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    assert admin.post(API + f'/crm/jobs/{job["id"]}/reject', json={'reason': 'x'}).status_code == 422
    r = admin.post(API + f'/crm/jobs/{job["id"]}/reject', json={'reason': 'Maosh aniq emas'}).json()
    assert r['status'] == 'rejected' and r['rejectReason'] == 'Maosh aniq emas'
    assert client.get(API + '/employer/jobs', headers=eh).json()[0]['rejectReason'] == 'Maosh aniq emas'
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'salary': 'abc'}).status_code == 422
    r = admin.patch(API + f'/crm/jobs/{job["id"]}', json={'salary': 30000, 'employerId': 'hack', 'status': 'active'}).json()
    assert r['salary'] == 30000 and r['employerId'] != 'hack' and r['status'] == 'active'
    assert admin.delete(API + f'/crm/jobs/{job["id"]}').status_code == 204
    assert client.get(API + '/employer/jobs', headers=eh).json() == []


# ============================================================ turar joy
def test_house_flow_with_photos_and_requests(client, admin):
    lh, _, _ = register(client, 'landlord')
    sh, _, _ = register(client, 'student')
    photos = [upload(client, lh).json()['url'] for _ in range(3)]
    base = {'title': 'Talabalar uchun xona', 'type': 'room', 'district': 'Yunusobod', 'address': '4-mavze', 'rooms': 1, 'price': 1500000,
            'audience': 'any', 'capacity': 2, 'freeSpots': 1, 'amenities': ['Wi-Fi'], 'description': 'Toza, metroga yaqin, talabalarga mos xona.'}
    assert client.post(API + '/landlord/houses', headers=lh, json={**base, 'photos': photos[:2]}).status_code == 422, 'kamida 3 ta rasm'
    assert client.post(API + '/landlord/houses', headers=lh, json={**base, 'photos': ['https://x.com/a.jpg'] * 3}).status_code == 422
    h = client.post(API + '/landlord/houses', headers=lh, json={**base, 'photos': photos}).json()
    assert h['status'] == 'pending' and h['occupancy'] == 'free'
    admin.post(API + f'/crm/houses/{h["id"]}/approve')
    found = client.get(API + '/houses', headers=sh, params={'price': '2', 'rooms': '1', 'onlyFree': 'true'}).json()
    assert found[0]['id'] == h['id'] and found[0]['owner']['name']
    assert client.get(API + '/houses', headers=sh, params={'price': '1'}).json() == []
    assert client.post(API + f'/houses/{h["id"]}/requests', headers=sh, json={'moveIn': 'ertaga'}).status_code == 422
    req = client.post(API + f'/houses/{h["id"]}/requests', headers=sh, json={'moveIn': '2026-12-15', 'term': '6', 'message': 'Salom'}).json()
    assert client.get(API + '/landlord/requests', headers=lh).json()[0]['id'] == req['id']
    assert client.patch(API + f'/landlord/requests/{req["id"]}', headers=lh, json={'status': 'accepted'}).json()['status'] == 'accepted'
    assert client.get(API + '/me/rental-requests', headers=sh).json()[0]['status'] == 'accepted'
    assert client.post(API + f'/me/rental-requests/{req["id"]}/withdraw', headers=sh).status_code == 409
    assert client.patch(API + f'/landlord/houses/{h["id"]}/occupancy', headers=lh, json={'occupancy': 'occupied'}).json()['occupancy'] == 'occupied'
    assert client.get(API + '/houses', headers=sh, params={'onlyFree': 'true'}).json() == [] or all(x['id'] != h['id'] for x in client.get(API + '/houses', headers=sh, params={'onlyFree': 'true'}).json())
    # o‘chirish — rasmlar ham o‘chadi
    assert client.delete(API + f'/landlord/houses/{h["id"]}', headers=lh).status_code == 204
    assert client.get(photos[0]).status_code == 404


# ============================================================ kurslar
def test_courses_progress_server_side_scoring(client, admin):
    sh, _, _ = register(client)
    courses = client.get(API + '/courses', headers=sh).json()
    assert {c['id'] for c in courses} == {'c-ru', 'c-en'} and all(c['percent'] == 0 for c in courses)
    ru = next(c for c in courses if c['id'] == 'c-ru')
    l1, l2 = ru['lessons'][0], ru['lessons'][1]
    assert client.get(l1['video']['url']).status_code == 200
    assert client.post(API + f'/courses/c-ru/lessons/{l2["id"]}/complete', headers=sh, json={'answers': [q['answer'] for q in l2['quiz']]}).status_code == 409
    wrong = [(q['answer'] + 1) % len(q['options']) for q in l1['quiz']]
    assert client.post(API + f'/courses/c-ru/lessons/{l1["id"]}/complete', headers=sh, json={'answers': wrong}).status_code == 422
    assert client.post(API + f'/courses/c-ru/lessons/{l1["id"]}/complete', headers=sh, json={'score': 5}).status_code == 422, 'ballni mijoz belgilay olmaydi'
    r = client.post(API + f'/courses/c-ru/lessons/{l1["id"]}/complete', headers=sh, json={'answers': [q['answer'] for q in l1['quiz']]})
    assert r.status_code == 200 and r.json()['score'] == len(l1['quiz'])
    assert next(c for c in client.get(API + '/courses', headers=sh).json() if c['id'] == 'c-ru')['percent'] == 20
    eh, _, _ = register(client, 'employer')
    assert client.post(API + f'/courses/c-ru/lessons/{l1["id"]}/complete', headers=eh, json={'answers': []}).status_code == 403
    # Support: darsni yashirish → talabaga ko‘rinmaydi
    course = next(c for c in admin.get(API + '/crm/courses').json() if c['id'] == 'c-en')
    course['lessons'][-1]['status'] = 'draft'
    assert admin.put(API + '/crm/courses/c-en', json=course).status_code == 200
    en = next(c for c in client.get(API + '/courses', headers=sh).json() if c['id'] == 'c-en')
    assert len(en['lessons']) == len(course['lessons']) - 1
    bad = {**course, 'lessons': course['lessons'] + [course['lessons'][0]]}
    assert admin.put(API + '/crm/courses/c-en', json=bad).status_code == 422


# ============================================================ support
def test_support_chat_end_to_end(client, admin):
    h, u, _ = register(client, 'employer')
    shot = upload(client, h, 'shot').json()
    t = client.post(API + '/support/tickets', headers=h, json={'type': 'technical', 'subject': 'Ariza ochilmayapti', 'text': 'Tugma bosilganda xato chiqadi',
                                                                   'attachment': {'url': shot['url'], 'name': 'skrin.png'}}).json()
    assert t['status'] == 'new' and 'unreadBySupport' not in t
    admin_msgs = [p for m, p in SENT if m == 'sendMessage' and p['chat_id'] == '777']
    assert admin_msgs and 'Ariza ochilmayapti' in admin_msgs[-1]['text'] and 'Ish beruvchi' in admin_msgs[-1]['text']
    crm = next(x for x in admin.get(API + '/crm/support/tickets').json() if x['id'] == t['id'])
    assert crm['unreadBySupport'] == 1 and crm['messages'][0]['attachment']['url'] == shot['url']
    r = admin.post(API + f'/crm/support/tickets/{t["id"]}/messages', json={'text': 'Tekshirdik, tuzatildi', 'status': 'answered'}).json()
    assert r['status'] == 'answered' and r['messages'][-1]['from'] == 'support'
    mine = client.get(API + f'/support/tickets/{t["id"]}', headers=h).json()
    assert mine['unreadByUser'] == 1 and mine['messages'][-1]['text'] == 'Tekshirdik, tuzatildi'
    assert client.get(API + '/notifications', headers=h).json()[0]['title'] == 'Support javob berdi'
    client.post(API + f'/support/tickets/{t["id"]}/read', headers=h)
    r = client.post(API + f'/support/tickets/{t["id"]}/messages', headers=h, json={'text': 'Rahmat!'}).json()
    assert r['status'] == 'in_review'
    assert admin.patch(API + f'/crm/support/tickets/{t["id"]}', json={'status': 'resolved'}).json()['status'] == 'resolved'
    other, _, _ = register(client)
    assert client.get(API + f'/support/tickets/{t["id"]}', headers=other).status_code == 404
    assert client.post(API + '/support/tickets', headers=h, json={'type': 'hack', 'subject': 'abc', 'text': 'abcdef'}).status_code == 422


# ============================================================ shikoyat, bildirishnoma
def test_complaints(client, admin):
    eh, _, _ = register(client, 'employer')
    sh, _, _ = register(client)
    job = client.post(API + '/employer/jobs', headers=eh, json=JOB).json()
    assert client.post(API + '/complaints', headers=sh, json={'target': {'type': 'job', 'id': 'yoq'}, 'category': 'Firibgarlik'}).status_code == 404
    c = client.post(API + '/complaints', headers=sh, json={'target': {'type': 'job', 'id': job['id']}, 'category': 'Firibgarlik', 'message': 'Pul so‘rashdi'}).json()
    assert c['target']['label'] == JOB['title']
    r = admin.patch(API + f'/crm/complaints/{c["id"]}', json={'status': 'resolved', 'note': 'E’lon yashirildi'}).json()
    assert r['status'] == 'resolved' and r['notes'][0]['text'] == 'E’lon yashirildi'
    client.post(API + '/notifications/read-all', headers=eh)
    assert all(n['read'] for n in client.get(API + '/notifications', headers=eh).json())


# ============================================================ admin: xavfsizlik, foydalanuvchilar, sozlamalar
def test_admin_auth_csrf_and_password_change(client, app):
    from fastapi.testclient import TestClient
    assert client.get(API + '/crm/users').status_code == 401
    sh, _, _ = register(client)
    assert client.get(API + '/crm/users', headers=sh).status_code == 401, 'foydalanuvchi tokeni admin uchun yaroqsiz'
    with TestClient(app) as a:
        assert a.post(API + '/auth/admin/login', json={'username': 'root', 'password': 'xato'}).status_code == 401
        r = a.post(API + '/auth/admin/login', json={'username': 'ROOT', 'password': 'root-password-1'})
        assert r.status_code == 200 and 'httponly' in r.headers['set-cookie'].lower() and 'token' not in r.json()
        assert a.get(API + '/auth/admin/me').json()['user']['role'] == 'admin'
        assert a.put(API + '/crm/settings', json={'platform': {'name': 'X'}}).status_code == 403, 'CSRF sarlavhasisiz yozish yo‘q'
        a.headers['X-Requested-With'] = 'TalabaGo'
        old_cookie = a.cookies.get('tg_support_session')
        assert a.post(API + '/auth/admin/password', json={'current': 'xato', 'next': 'yangi-parol-2'}).status_code == 400
        assert a.post(API + '/auth/admin/password', json={'current': 'root-password-1', 'next': 'yangi-parol-2'}).status_code == 204
        assert a.get(API + '/crm/users').status_code == 200
    with TestClient(app) as b:
        b.cookies.set('tg_support_session', old_cookie)
        assert b.get(API + '/crm/users').status_code == 401, 'parol almashgach eski sessiyalar bekor'
        assert b.post(API + '/auth/admin/login', json={'username': 'root', 'password': 'yangi-parol-2'}).status_code == 200
        b.headers['X-Requested-With'] = 'TalabaGo'
        assert b.post(API + '/auth/admin/password', json={'current': 'yangi-parol-2', 'next': 'root-password-1'}).status_code == 204


def test_admin_lockout(client):
    for _ in range(5):
        client.post(API + '/auth/admin/login', json={'username': 'root', 'password': 'xato'})
    assert client.post(API + '/auth/admin/login', json={'username': 'root', 'password': 'root-password-1'}).status_code == 429


def test_block_user_and_settings(client, admin):
    h, u, body = register(client)
    assert admin.patch(API + f'/crm/users/{u["id"]}', json={'status': 'blocked'}).json()['status'] == 'blocked'
    assert client.get(API + '/users/me', headers=h).status_code == 403
    assert client.post(API + '/auth/login', json={'phone': body['phone'], 'password': 'parol12345'}).status_code == 403
    admin.patch(API + f'/crm/users/{u["id"]}', json={'status': 'active', 'university': 'INHA'})
    assert client.get(API + '/users/me', headers=h).json()['university'] == 'INHA'
    users = admin.get(API + '/crm/users').json()
    assert all('passwordHash' not in x for x in users)

    s = admin.get(API + '/crm/settings').json()
    s['system'].update(moderation=False)
    admin.put(API + '/crm/settings', json=s)
    eh, _, _ = register(client, 'employer')
    assert client.post(API + '/employer/jobs', headers=eh, json=JOB).json()['status'] == 'active', 'moderatsiya o‘chiq — darhol faol'
    s['system'].update(moderation=True, registrationOpen=False)
    admin.put(API + '/crm/settings', json=s)
    r = client.post(API + '/auth/register', json={'role': 'student', 'firstName': 'Yopiq', 'phone': '977776655', 'password': 'parol12345'})
    assert r.status_code == 403
    s['system'].update(registrationOpen=True, maintenance=True)
    admin.put(API + '/crm/settings', json=s)
    assert client.get(API + '/jobs', headers=h).status_code == 503
    assert admin.get(API + '/crm/users').status_code == 200, 'admin texnik ishlar paytida ham ishlaydi'
    s['system'].update(maintenance=False)
    s['platform']['name'] = 'TalabaGo Pro'
    admin.put(API + '/crm/settings', json=s)
    assert client.get(API + '/public/config').json()['platformName'] == 'TalabaGo Pro'
    s['platform']['name'] = 'TalabaGo'
    admin.put(API + '/crm/settings', json=s)


# ============================================================ reklamalar
def test_ads_schedule_and_tracking(client, admin):
    now = datetime.now(timezone.utc)
    data = lambda **k: __import__('json').dumps({'name': 'Kuzgi kurs', 'type': 'image', 'title': 'IT kurslari', 'description': '', 'link': 'https://example.uz',  # noqa: E731
                                                  'placements': ['/student/jobs'], 'startAt': iso(now - timedelta(hours=1)), 'endAt': iso(now + timedelta(days=1)),
                                                  'enabled': True, **k})
    files = lambda: {'file': ('banner.png', png_bytes(1200, 720), 'image/png')}  # noqa: E731
    assert client.post(API + '/ads', data={'data': data()}, files=files()).status_code == 401
    assert admin.post(API + '/ads', data={'data': data(link='javascript:alert(1)')}, files=files()).status_code == 422
    assert admin.post(API + '/ads', data={'data': data(endAt=iso(now - timedelta(days=2)))}, files=files()).status_code == 422
    assert admin.post(API + '/ads', data={'data': data(type='video')}, files=files()).status_code == 422, 'rasm video sifatida o‘tmaydi'
    live = admin.post(API + '/ads', data={'data': data()}, files=files()).json()
    assert live['media']['src'].startswith('/media/ad/') and live['media']['width'] == 1200 and live['order'] == 1
    future = admin.post(API + '/ads', data={'data': data(name='Kelajak', startAt=iso(now + timedelta(days=2)), endAt=iso(now + timedelta(days=3)), order=1)}, files=files()).json()
    assert future['order'] == 1
    expired_id = admin.post(API + '/ads', data={'data': data(name='Eski')}, files=files()).json()['id']
    active = client.get(API + '/ads/active', params={'placement': '/student/jobs'}).json()
    ids = [a['id'] for a in active]
    assert live['id'] in ids and 'views' not in active[0]
    assert client.get(API + '/ads/active', params={'placement': '/landlord/houses'}).json() == []
    admin.patch(API + f'/ads/{live["id"]}/enabled', json={'enabled': False})
    assert live['id'] not in [a['id'] for a in client.get(API + '/ads/active').json()]
    client.post(API + f'/ads/{expired_id}/view')
    client.post(API + f'/ads/{expired_id}/view')
    client.post(API + f'/ads/{expired_id}/click')
    a = next(x for x in admin.get(API + '/ads').json() if x['id'] == expired_id)
    assert a['views'] == 1 and a['clicks'] == 1, 'ko‘rish IP bo‘yicha takrorlanmaydi'
    ids_all = [x['id'] for x in admin.get(API + '/ads').json()]
    assert admin.patch(API + '/ads/order', json={'ids': list(reversed(ids_all))}).json()['ok']
    assert admin.patch(API + '/ads/order', json={'ids': ids_all[:1]}).status_code == 422
    upd = admin.patch(API + f'/ads/{live["id"]}', data={'data': data(title='Yangi sarlavha')}, files=files()).json()
    assert upd['title'] == 'Yangi sarlavha' and upd['media']['src'] != live['media']['src']
    assert client.get(live['media']['src']).status_code == 404, 'eski fayl o‘chirildi'
    for i in (live['id'], future['id'], expired_id):
        assert admin.delete(API + f'/ads/{i}').status_code == 204
    assert admin.get(API + '/ads').json() == []


def test_admin_lists_have_real_data(client, admin):
    for p in ('/crm/users', '/crm/jobs', '/crm/houses', '/crm/applications', '/crm/rental-requests', '/crm/courses', '/crm/progress',
              '/crm/support/tickets', '/crm/complaints', '/crm/settings', '/ads'):
        assert admin.get(API + p).status_code == 200, p
