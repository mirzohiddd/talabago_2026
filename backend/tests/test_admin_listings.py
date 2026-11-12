"""Support (admin) qo‘shadigan e’lonlar: akkauntsiz ish/uy e’loni, manba va tekshiruv, nashr qoidalari,
foydalanuvchiga ko‘rinish, telefon roziligi, arizalarni Support boshqarishi va eski oqimlar buzilmaganligi."""
import pytest

from conftest import JOB, SENT, png_bytes, register  # noqa: F401

API = '/api/v1'
SRC = {'type': 'telegram_channel', 'name': '@toshkent_ish_elonlari', 'url': 'https://t.me/toshkent_ish_elonlari/1234'}
OK = {'ownerContacted': True, 'ownerConsent': True, 'phoneConsent': True, 'method': 'phone', 'note': 'Egasi bilan 12.11 da gaplashildi'}


@pytest.fixture(autouse=True)
def _cleanup(admin):
    """Testlar umumiy (vaqtinchalik) bazani ishlatadi — bu modulda yaratilgan e’lonlar boshqa testlarga ta’sir qilmasin."""
    before = {c: {x['id'] for x in admin.get(API + f'/crm/{c}').json()} for c in ('jobs', 'houses')}
    yield
    for coll, ids in before.items():
        for x in admin.get(API + f'/crm/{coll}').json():
            if x['id'] not in ids:
                admin.delete(API + f'/crm/{coll}/{x["id"]}')


def admin_job(**extra):
    body = {'title': 'Ofitsiant (kechki smena)', 'company': 'Kafe (Chilonzor)', 'format': 'offline', 'type': 'hourly', 'salary': 25000,
            'salaryPeriod': 'hour', 'workTime': 'evening', 'schedule': 'Du–Ju, 18:00–23:00', 'district': 'Chilonzor', 'address': 'Bunyodkor ko‘chasi',
            'description': 'Mehmonlarga xizmat ko‘rsatish, buyurtmalarni qabul qilish.', 'requirements': ['18 yoshdan katta', 'Muloqotga ochiq'],
            'phone': '+998 90 555 44 33', 'telegram': '@kafe_admin', 'contactName': 'Kafe menejeri', 'source': SRC, 'verification': OK}
    body.update(extra)
    return body


def admin_photo(admin):
    r = admin.post(API + '/crm/files', data={'kind': 'photo'}, files={'file': ('uy.png', png_bytes(320, 240), 'image/png')})
    assert r.status_code == 201, r.text
    return r.json()['url']


def admin_house(admin, **extra):
    body = {'title': 'Talabalar uchun 2 xonali kvartira', 'type': 'flat', 'photos': [admin_photo(admin)], 'city': 'Toshkent', 'district': 'Yunusobod',
            'address': 'Yunusobod 4-mavze', 'rooms': 2, 'price': 3_000_000, 'audience': 'any', 'capacity': 3, 'freeSpots': 2,
            'amenities': ['Wi-Fi', 'Mebel'], 'description': 'Metroga 5 daqiqa, jihozlangan, kommunal to‘lovlar alohida.',
            'phone': '+998 93 222 11 00', 'contactName': 'Uy egasi', 'source': {**SRC, 'type': 'telegram_group', 'name': 'Ijara Toshkent guruhi'}, 'verification': OK}
    body.update(extra)
    return body


def test_admin_job_requires_admin(client):
    assert client.post(API + '/crm/jobs', json=admin_job()).status_code == 401
    h, _, _ = register(client, 'employer')
    assert client.post(API + '/crm/jobs', json=admin_job(), headers=h).status_code == 401


def test_admin_job_publish_visible_to_students(client, admin):
    r = admin.post(API + '/crm/jobs', json=admin_job(publish=True))
    assert r.status_code == 201, r.text
    job = r.json()
    assert job['status'] == 'active' and job['employerId'] is None and job['createdBy'] == 'admin' and job['approvedAt']
    assert job['source']['name'] == '@toshkent_ish_elonlari' and job['verification']['verifiedBy'] == 'root' and job['verification']['verifiedAt']
    h, _, _ = register(client)
    lst = client.get(API + '/jobs', headers=h).json()
    pub = next(j for j in lst if j['id'] == job['id'])
    # ichki ma’lumot (manba, tekshiruv) talabaga chiqmaydi; rozilik bor — telefon ko‘rinadi
    assert 'source' not in pub and 'verification' not in pub and 'adminId' not in pub
    assert pub['phone'] == '+998 90 555 44 33' and pub['verified'] is True and pub['address'] == 'Bunyodkor ko‘chasi'
    # filtrlar admin e’loniga ham ishlaydi
    assert any(j['id'] == job['id'] for j in client.get(API + '/jobs?type=hourly&district=Chilonzor', headers=h).json())
    assert not any(j['id'] == job['id'] for j in client.get(API + '/jobs?type=permanent', headers=h).json())
    detail = client.get(API + f'/jobs/{job["id"]}', headers=h).json()
    assert 'verification' not in detail and detail['phone']


def test_publish_requires_owner_consent(client, admin):
    r = admin.post(API + '/crm/jobs', json=admin_job(publish=True, verification={'ownerContacted': True, 'ownerConsent': False}))
    assert r.status_code == 422
    # rozilik yo‘q → faqat “pending” sifatida saqlanadi, tasdiqlab bo‘lmaydi
    job = admin.post(API + '/crm/jobs', json=admin_job(verification={'ownerContacted': False})).json()
    assert job['status'] == 'pending' and job['approvedAt'] is None
    assert admin.post(API + f'/crm/jobs/{job["id"]}/approve').status_code == 422
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'status': 'approved'}).status_code == 422
    h, _, _ = register(client)
    assert not any(j['id'] == job['id'] for j in client.get(API + '/jobs', headers=h).json())
    assert client.get(API + f'/jobs/{job["id"]}', headers=h).status_code == 404
    # egasi bilan tekshirildi → tasdiqlash mumkin
    r = admin.patch(API + f'/crm/jobs/{job["id"]}', json={'verification': OK})
    assert r.status_code == 200 and r.json()['verification']['verifiedBy'] == 'root'
    r = admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    assert r.status_code == 200 and r.json()['status'] == 'active' and r.json()['approvedBy'] == 'root'
    assert any(j['id'] == job['id'] for j in client.get(API + '/jobs', headers=h).json())


def test_phone_hidden_without_phone_consent(client, admin):
    job = admin.post(API + '/crm/jobs', json=admin_job(publish=True, verification={**OK, 'phoneConsent': False})).json()
    h, _, _ = register(client)
    pub = next(j for j in client.get(API + '/jobs', headers=h).json() if j['id'] == job['id'])
    assert pub['phone'] is None and pub['telegram'] is None
    # admin panelida telefon saqlangan
    assert next(j for j in admin.get(API + '/crm/jobs').json() if j['id'] == job['id'])['phone'] == '+998 90 555 44 33'


def test_admin_house_flow_and_owner_card(client, admin):
    r = admin.post(API + '/crm/houses', json=admin_house(admin, publish=True))
    assert r.status_code == 201, r.text
    house = r.json()
    assert house['ownerId'] is None and house['status'] == 'active' and house['occupancy'] == 'free'
    h, _, _ = register(client)
    pub = next(x for x in client.get(API + '/houses?rooms=2&district=Yunusobod', headers=h).json() if x['id'] == house['id'])
    assert pub['owner'] == {'id': None, 'name': 'Uy egasi', 'phone': '+998 93 222 11 00', 'telegram': None}
    assert 'source' not in pub and pub['amenities'] == ['Wi-Fi', 'Mebel']
    d = client.get(API + f'/houses/{house["id"]}', headers=h).json()
    assert d['owner']['name'] == 'Uy egasi' and 'verification' not in d
    # rasm faqat /media/ orqali
    bad = admin_house(admin); bad['photos'] = ['https://evil.example/x.jpg']
    assert admin.post(API + '/crm/houses', json=bad).status_code == 422


def test_requests_to_admin_listings_go_to_support(client, admin):
    job = admin.post(API + '/crm/jobs', json=admin_job(publish=True)).json()
    house = admin.post(API + '/crm/houses', json=admin_house(admin, publish=True)).json()
    h, st, _ = register(client)
    SENT.clear()
    a = client.post(API + f'/jobs/{job["id"]}/apply', json={'message': 'Kechki smenada ishlay olaman'}, headers=h)
    assert a.status_code == 201, a.text
    assert any('Admin e’loniga ariza' in p.get('text', '') and p.get('chat_id') in (777, '777') for _, p in SENT)
    r = client.post(API + f'/houses/{house["id"]}/requests', json={'message': 'Salom', 'moveIn': '2030-01-10', 'term': '1'}, headers=h)
    assert r.status_code == 201, r.text
    # talaba arizalarida ichki ma’lumot yo‘q
    mine = client.get(API + '/me/applications', headers=h).json()
    assert mine[0]['job']['id'] == job['id'] and 'verification' not in mine[0]['job']
    # Support holatni o‘zgartiradi → talabaga bildirishnoma
    r = admin.patch(API + f'/crm/applications/{a.json()["id"]}', json={'status': 'interview', 'note': 'Ertaga 18:00'})
    assert r.status_code == 200 and r.json()['status'] == 'interview'
    notes = client.get(API + '/notifications', headers=h).json()
    assert any('suhbatga' in (n.get('title') or '').lower() for n in (notes.get('items') if isinstance(notes, dict) else notes))
    rq = client.get(API + '/me/rental-requests', headers=h).json()[0]
    assert admin.patch(API + f'/crm/rental-requests/{rq["id"]}', json={'status': 'accepted'}).json()['status'] == 'accepted'
    assert admin.patch(API + f'/crm/rental-requests/{rq["id"]}', json={'status': 'interview'}).status_code == 422


def test_support_cannot_change_status_of_owner_listing_applications(client, admin):
    eh, _, _ = register(client, 'employer')
    job = client.post(API + '/employer/jobs', json=JOB, headers=eh).json()
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    sh, _, _ = register(client)
    app = client.post(API + f'/jobs/{job["id"]}/apply', json={'message': 'Salom'}, headers=sh).json()
    assert admin.patch(API + f'/crm/applications/{app["id"]}', json={'status': 'accepted'}).status_code == 403


def test_owner_listing_moderation_and_hide(client, admin):
    """Ish beruvchi e’loni: pending → faqat tasdiqlangach ko‘rinadi; admin yashirsa egasi o‘zi qayta ocha olmaydi."""
    eh, _, _ = register(client, 'employer')
    job = client.post(API + '/employer/jobs', json=JOB, headers=eh).json()
    assert job['status'] == 'pending'
    sh, _, _ = register(client)
    assert not any(j['id'] == job['id'] for j in client.get(API + '/jobs', headers=sh).json())
    r = admin.patch(API + f'/crm/jobs/{job["id"]}', json={'status': 'approved'})
    assert r.status_code == 200 and r.json()['status'] == 'active'
    assert any(j['id'] == job['id'] for j in client.get(API + '/jobs', headers=sh).json())
    # yashirish (oldin 422 qaytarar edi)
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'status': 'hidden'}).json()['status'] == 'hidden'
    assert not any(j['id'] == job['id'] for j in client.get(API + '/jobs', headers=sh).json())
    assert client.patch(API + f'/employer/jobs/{job["id"]}/active', json={'active': True}, headers=eh).status_code == 409
    assert client.patch(API + f'/employer/jobs/{job["id"]}/active', json={'active': False}, headers=eh).status_code == 409
    # rad etish → egasiga sabab bilan
    j2 = client.post(API + '/employer/jobs', json={**JOB, 'title': 'Boshqa vakansiya'}, headers=eh).json()
    r = admin.post(API + f'/crm/jobs/{j2["id"]}/reject', json={'reason': 'Maosh aniq emas'})
    assert r.json()['status'] == 'rejected'


def test_admin_edit_and_delete(client, admin):
    job = admin.post(API + '/crm/jobs', json=admin_job(publish=True)).json()
    r = admin.patch(API + f'/crm/jobs/{job["id"]}', json={'title': 'Ofitsiant (tushlik)', 'requirements': ['Tajriba shart emas'], 'address': 'Yangi manzil',
                                                         'source': {**SRC, 'name': '@yangi_kanal'}, 'phone': '90 111 22 33'})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['title'] == 'Ofitsiant (tushlik)' and j['requirements'] == ['Tajriba shart emas'] and j['source']['name'] == '@yangi_kanal' and j['phone'] == '+998 90 111 22 33'
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'phone': '12345'}).status_code == 422
    assert admin.delete(API + f'/crm/jobs/{job["id"]}').status_code == 204
    assert all(x['id'] != job['id'] for x in admin.get(API + '/crm/jobs').json())


def test_legacy_records_without_new_fields_still_work(client, admin, app):
    """Eski (createdBy/source maydonlarisiz) yozuvlar o‘zgarishsiz ishlaydi — migratsiya talab qilinmaydi."""
    eh, _, _ = register(client, 'employer')
    job = client.post(API + '/employer/jobs', json=JOB, headers=eh).json()
    admin.post(API + f'/crm/jobs/{job["id"]}/approve')
    store = app.state.store if hasattr(app.state, 'store') else None
    sh, _, _ = register(client)
    pub = next(j for j in client.get(API + '/jobs', headers=sh).json() if j['id'] == job['id'])
    assert 'verified' not in pub and pub['phone'] == job['phone'] and pub['employerId'] == job['employerId']
    assert store is None or all('createdBy' not in j for j in store.read('jobs') if j['id'] == job['id'])


# ============================================================ ixtiyoriy maydonlar va “Kelishiladi”
def test_minimal_admin_job_negotiable_salary(client, admin):
    r = admin.post(API + '/crm/jobs', json={'title': 'Laborant yordamchisi', 'type': 'permanent', 'source': SRC})
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['salary'] is None and j['salaryNegotiable'] is True and j['status'] == 'pending' and j['company'] == '' and j['description'] == ''
    # maosh berilsa — “Kelishiladi” emas; 0 / bo‘sh qiymat — “Kelishiladi”
    j2 = admin.post(API + '/crm/jobs', json={'title': 'Kassir', 'type': 'daily', 'salary': 150000, 'salaryPeriod': 'day', 'source': SRC}).json()
    assert j2['salary'] == 150000 and j2['salaryNegotiable'] is False
    assert admin.post(API + '/crm/jobs', json={'title': 'Kassir 2', 'type': 'daily', 'salary': '', 'source': SRC}).json()['salaryNegotiable'] is True
    assert admin.post(API + '/crm/jobs', json={'title': 'Kassir 3', 'type': 'daily', 'salary': 500, 'salaryNegotiable': True, 'source': SRC}).json()['salary'] is None
    # majburiy maydonlar: lavozim va manba
    assert admin.post(API + '/crm/jobs', json={'type': 'daily', 'source': SRC}).status_code == 422
    assert admin.post(API + '/crm/jobs', json={'title': 'Kassir', 'type': 'daily'}).status_code == 422
    assert admin.post(API + '/crm/jobs', json={'title': 'Kassir', 'type': 'daily', 'salary': -5, 'source': SRC}).status_code == 422
    # nashr → talabaga ko‘rinadi; maosh filtri “Kelishiladi”ni chiqarmaydi, xato bermaydi
    admin.patch(API + f'/crm/jobs/{j["id"]}', json={'verification': OK})
    assert admin.post(API + f'/crm/jobs/{j["id"]}/approve').status_code == 200
    h, _, _ = register(client)
    assert any(x['id'] == j['id'] and x['salaryNegotiable'] for x in client.get(API + '/jobs', headers=h).json())
    r = client.get(API + '/jobs?salary=3', headers=h)
    assert r.status_code == 200 and all(x['id'] != j['id'] for x in r.json())
    # tahrirlash: maosh kiritildi → bayroq tushadi; bo‘shatildi → yana “Kelishiladi”
    assert admin.patch(API + f'/crm/jobs/{j["id"]}', json={'salary': 4_000_000}).json()['salaryNegotiable'] is False
    x = admin.patch(API + f'/crm/jobs/{j["id"]}', json={'salary': None}).json()
    assert x['salary'] is None and x['salaryNegotiable'] is True


def test_minimal_admin_house_negotiable_price(client, admin):
    r = admin.post(API + '/crm/houses', json={'title': 'Ijaraga xona', 'type': 'room', 'district': 'Chilonzor', 'source': SRC,
                                             'verification': OK, 'publish': True})
    assert r.status_code == 201, r.text
    hs = r.json()
    assert hs['price'] is None and hs['priceNegotiable'] is True and hs['photos'] == [] and hs['status'] == 'active'
    assert admin.post(API + '/crm/houses', json={'title': 'Xona', 'type': 'room', 'source': SRC}).status_code == 422   # tuman majburiy
    h, _, _ = register(client)
    assert any(x['id'] == hs['id'] for x in client.get(API + '/houses', headers=h).json())
    r = client.get(API + '/houses?price=2', headers=h)
    assert r.status_code == 200 and all(x['id'] != hs['id'] for x in r.json())


def test_owner_listing_still_requires_salary(client, admin):
    eh, _, _ = register(client, 'employer')
    assert client.post(API + '/employer/jobs', json={**JOB, 'salary': None}, headers=eh).status_code == 422
    job = client.post(API + '/employer/jobs', json=JOB, headers=eh).json()
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'salary': ''}).status_code == 422
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'salaryNegotiable': True}).status_code == 422
    assert admin.patch(API + f'/crm/jobs/{job["id"]}', json={'salary': 30000}).json()['salary'] == 30000