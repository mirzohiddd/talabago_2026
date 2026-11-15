"""Yangi funksiyalar: yakuniy test + sertifikat, chat, ish kategoriyalari, monitoring, o‘zaro baholash (Support nazorati bilan)."""
import pytest
from conftest import JOB, register

API = '/api/v1'


@pytest.fixture(autouse=True)
def _cleanup(admin):
    """Testlar umumiy bazani ishlatadi — bu modulda yaratilgan vakansiyalar boshqa testlarning filtr natijalariga ta’sir qilmasin."""
    before = {x['id'] for x in admin.get(API + '/crm/jobs').json()}
    yield
    for x in admin.get(API + '/crm/jobs').json():
        if x['id'] not in before:
            admin.delete(API + f'/crm/jobs/{x["id"]}')


def _job(client, admin, eh, **over):
    j = client.post(API + '/employer/jobs', headers=eh, json={**JOB, **over})
    assert j.status_code == 201, j.text
    j = j.json()
    assert admin.post(API + f'/crm/jobs/{j["id"]}/approve').json()['status'] == 'active'
    return j


# ============================================================ 1. kurslar: yakuniy test va sertifikat
QUESTIONS = [{'q': f'Savol {i}?', 'options': ['A', 'B', 'C'], 'answer': i % 3} for i in range(5)]


def _finish_lessons(client, sh, course):
    for l in course['lessons']:
        ans = [q['answer'] for q in l.get('quiz') or []]
        r = client.post(API + f'/courses/{course["id"]}/lessons/{l["id"]}/complete', headers=sh, json={'answers': ans if l.get('quiz') else None})
        assert r.status_code == 200, r.text


def test_final_exam_two_attempts_and_certificate(client, admin):
    sh, su, _ = register(client, 'student')
    courses = client.get(API + '/courses', headers=sh).json()
    en = next(c for c in courses if c['id'] == 'c-en')
    assert en['exam'] == {'available': False, 'questions': 0} and 'finalTest' not in en
    # Support: noto‘g‘ri test saqlanmaydi, keyin to‘g‘risi nashr qilinadi
    assert admin.put(API + '/crm/courses/c-en/final-test', json={'status': 'published', 'questions': QUESTIONS[:2]}).status_code == 422
    assert admin.put(API + '/crm/courses/c-en/final-test', json={'status': 'draft', 'questions': [{'q': 'Bu nima?', 'options': ['a', 'b'], 'answer': 3}]}).status_code == 422
    r = admin.put(API + '/crm/courses/c-en/final-test', json={'status': 'published', 'passPercent': 80, 'questions': QUESTIONS})
    assert r.status_code == 200 and r.json()['maxAttempts'] == 2
    # talabaga to‘g‘ri javoblar yuborilmaydi
    ex = client.get(API + '/courses/c-en/exam', headers=sh).json()
    assert all('answer' not in q for q in ex['questions']) and ex['eligible'] is False and ex['attemptsLeft'] == 2
    assert 'finalTest' not in str(client.get(API + '/courses', headers=sh).json())
    # darslar tugamaguncha topshirib bo‘lmaydi
    assert client.post(API + '/courses/c-en/exam/submit', headers=sh, json={'answers': [0] * 5}).status_code == 409
    _finish_lessons(client, sh, en)
    assert client.post(API + '/courses/c-en/exam/submit', headers=sh, json={'answers': [0, 1]}).status_code == 422
    wrong = [(q['answer'] + 1) % 3 for q in QUESTIONS]
    r1 = client.post(API + '/courses/c-en/exam/submit', headers=sh, json={'answers': wrong}).json()
    assert r1['attempt']['passed'] is False and r1['attemptsLeft'] == 1 and r1['certificate'] is None
    right = [q['answer'] for q in QUESTIONS]
    right[0] = (right[0] + 1) % 3                                     # 4/5 = 80% — o‘tadi
    r2 = client.post(API + '/courses/c-en/exam/submit', headers=sh, json={'answers': right}).json()
    assert r2['attempt']['percent'] == 80 and r2['attempt']['passed'] and r2['certificate']['code'].startswith('TG-')
    # uchinchi urinish bloklangan
    assert client.post(API + '/courses/c-en/exam/submit', headers=sh, json={'answers': right}).status_code == 409
    code = r2['certificate']['code']
    # ommaviy tekshirish va PDF (QR bilan)
    v = client.get(API + f'/certificates/{code}').json()
    assert v['valid'] and v['fullName'] == f'{su["firstName"]} {su["lastName"]}'
    pdf = client.get(API + f'/certificates/{code}/pdf')
    assert pdf.status_code == 200 and pdf.headers['content-type'] == 'application/pdf' and pdf.content[:5] == b'%PDF-'
    page = client.get(API + f'/certificates/{code}/page')
    assert page.status_code == 200 and 'Sertifikat haqiqiy' in page.text
    assert client.get(API + '/certificates/TG-NOTEXIST/page').status_code == 200
    assert client.get(API + '/certificates/TG-NOTEXIST').status_code == 404
    assert [c['code'] for c in client.get(API + '/me/certificates', headers=sh).json()] == [code]
    # Support: urinishlar, sertifikatni bekor qilish
    attempts = admin.get(API + '/crm/exams').json()
    assert len([a for a in attempts if a['userId'] == su['id']]) == 2 and 'answers' not in attempts[0]
    cert = next(c for c in admin.get(API + '/crm/certificates').json() if c['code'] == code)
    assert cert['verifyUrl'].endswith(f'/certificates/{code}/page')
    assert admin.patch(API + f'/crm/certificates/{cert["id"]}', json={'status': 'revoked', 'reason': 'Test'}).json()['status'] == 'revoked'
    assert client.get(API + f'/certificates/{code}').json()['valid'] is False
    assert 'bekor qilingan' in client.get(API + f'/certificates/{code}/page').text


def test_exam_reset_by_support(client, admin):
    admin.put(API + '/crm/courses/c-ru/final-test', json={'status': 'published', 'questions': QUESTIONS})
    sh, su, _ = register(client, 'student')
    ru = next(c for c in client.get(API + '/courses', headers=sh).json() if c['id'] == 'c-ru')
    _finish_lessons(client, sh, ru)
    wrong = [(q['answer'] + 1) % 3 for q in QUESTIONS]
    for _ in range(2):
        client.post(API + '/courses/c-ru/exam/submit', headers=sh, json={'answers': wrong})
    assert client.get(API + '/courses/c-ru/exam', headers=sh).json()['attemptsLeft'] == 0
    assert client.post(API + '/courses/c-ru/exam/submit', headers=sh, json={'answers': wrong}).status_code == 409
    assert admin.post(API + '/crm/exams/reset', json={'userId': su['id'], 'courseId': 'c-ru'}).json()['reset'] == 2
    assert client.get(API + '/courses/c-ru/exam', headers=sh).json()['attemptsLeft'] == 2
    admin.put(API + '/crm/courses/c-ru/final-test', json={'status': 'draft', 'questions': QUESTIONS})
    assert client.get(API + '/courses/c-ru/exam', headers=sh).status_code == 404


# ============================================================ 2. chat
def test_chat_after_application(client, admin):
    eh, eu, _ = register(client, 'employer')
    sh, su, _ = register(client, 'student')
    oh, _, _ = register(client, 'student')
    job = _job(client, admin, eh)
    app = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={'message': 'Salom'}).json()
    chats = client.get(API + '/chats', headers=sh).json()
    c = next(x for x in chats if x['applicationId'] == app['id'])
    assert c['other']['id'] == eu['id'] and c['job']['title'] == JOB['title'] and c['unread'] == 0
    assert client.post(API + f'/chats/{c["id"]}/messages', headers=sh, json={'text': '   '}).status_code == 422
    m = client.post(API + f'/chats/{c["id"]}/messages', headers=sh, json={'text': 'Assalomu alaykum! Qachon boraman?'})
    assert m.status_code == 201
    client.post(API + f'/chats/{c["id"]}/messages', headers=sh, json={'text': 'Ikkinchi xabar'})
    # ish beruvchida: 2 ta o‘qilmagan, bitta bildirishnoma (spam yo‘q)
    assert client.get(API + '/chats/unread', headers=eh).json()['count'] == 2
    notes = [n for n in client.get(API + '/notifications', headers=eh).json() if n['title'].startswith('Yangi xabar')]
    assert len(notes) == 1
    msgs = client.get(API + f'/chats/{c["id"]}/messages', headers=eh).json()
    assert [x['text'] for x in msgs] == ['Assalomu alaykum! Qachon boraman?', 'Ikkinchi xabar'] and msgs[0]['readAt'] is None
    assert client.post(API + f'/chats/{c["id"]}/read', headers=eh).status_code == 204
    assert client.get(API + '/chats/unread', headers=eh).json()['count'] == 0
    assert all(x['readAt'] for x in client.get(API + f'/chats/{c["id"]}/messages', headers=sh).json())
    reply = client.post(API + f'/chats/{c["id"]}/messages', headers=eh, json={'text': 'Ertaga 10:00 da keling'}).json()
    after = client.get(API + f'/chats/{c["id"]}/messages', headers=sh, params={'after': msgs[-1]['createdAt']}).json()
    assert [x['id'] for x in after] == [reply['id']]
    # begona foydalanuvchi ko‘ra olmaydi
    assert client.get(API + f'/chats/{c["id"]}/messages', headers=oh).status_code == 404
    assert client.post(API + f'/chats/{c["id"]}/messages', headers=oh, json={'text': 'x'}).status_code == 404
    # ariza kartasidan ochish (mavjud suhbat qaytadi)
    assert client.post(API + f'/applications/{app["id"]}/chat', headers=eh).json()['id'] == c['id']
    # Support: ko‘radi, xabarni yashiradi, suhbatni bloklaydi
    crm = next(x for x in admin.get(API + '/crm/chats').json() if x['id'] == c['id'])
    assert crm['messages'] == 3 and crm['studentName'] and crm['employerName']
    admin.patch(API + f'/crm/messages/{reply["id"]}', json={'hidden': True})
    last = client.get(API + f'/chats/{c["id"]}/messages', headers=sh).json()[-1]
    assert last['hidden'] and last['text'] != 'Ertaga 10:00 da keling'
    admin.patch(API + f'/crm/chats/{c["id"]}', json={'locked': True})
    assert client.post(API + f'/chats/{c["id"]}/messages', headers=sh, json={'text': 'Salom'}).status_code == 403


def test_chat_created_for_old_applications(client, admin, app):
    """Chat funksiyasidan oldingi arizalar uchun ham suhbat ochiladi (eski ma’lumot buzilmaydi)."""
    eh, _, _ = register(client, 'employer')
    sh, _, _ = register(client, 'student')
    job = _job(client, admin, eh)
    a = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={'message': ''}).json()
    from app.deps import get_store
    from app.config import get_settings
    store = get_store(get_settings())
    with store.tx('chats') as db:                       # eski holatni taqlid qilish: suhbat yo‘q
        db['chats'] = [c for c in db['chats'] if c['applicationId'] != a['id']]
    assert any(c['applicationId'] == a['id'] for c in client.get(API + '/chats', headers=eh).json())


# ============================================================ 3. kategoriyalar va filtrlar
def test_job_categories_and_filters(client, admin):
    eh, _, _ = register(client, 'employer')
    sh, _, _ = register(client, 'student')
    bad = client.post(API + '/employer/jobs', headers=eh, json={**JOB, 'category': 'Kosmonavtika'})
    assert bad.status_code == 422 and 'Faoliyat sohasi' in bad.json()['detail']
    no_cat = {k: v for k, v in JOB.items() if k != 'category'}
    assert client.post(API + '/employer/jobs', headers=eh, json=no_cat).status_code == 422
    it = _job(client, admin, eh, title='Frontend dasturchi (stajyor)', category='IT', type='permanent', salaryPeriod='month', salary=4_000_000)
    sale = _job(client, admin, eh, title='Savdo maslahatchisi', category='Savdo', type='daily', salaryPeriod='day', salary=150_000)
    ids = lambda **f: {j['id'] for j in client.get(API + '/jobs', headers=sh, params=f).json()}  # noqa: E731
    assert it['id'] in ids(category='IT') and sale['id'] not in ids(category='IT')
    assert sale['id'] in ids(category='Savdo', type='daily') and sale['id'] not in ids(category='Savdo', type='hourly')
    assert {it['id'], sale['id']} <= ids(category='all')
    # Support e’lonni boshqa sohaga o‘tkaza oladi, noto‘g‘ri soha rad etiladi
    assert admin.patch(API + f'/crm/jobs/{it["id"]}', json={'category': 'Nimadir'}).status_code == 422
    assert admin.patch(API + f'/crm/jobs/{it["id"]}', json={'category': 'Dizayn'}).json()['category'] == 'Dizayn'


# ============================================================ 4. monitoring
def test_employer_insights_real_numbers(client, admin):
    eh, _, _ = register(client, 'employer')
    s1, _, _ = register(client, 'student')
    s2, _, _ = register(client, 'student')
    empty = client.get(API + '/employer/insights', headers=eh).json()
    assert empty['totals']['jobs'] == 0 and empty['totals']['views'] == 0 and len(empty['timeline']) == 30
    j1 = _job(client, admin, eh, category='IT', type='hourly')
    j2 = _job(client, admin, eh, title='Kuryer', category='Yetkazib berish', type='daily', salaryPeriod='day', salary=200000)
    for sh in (s1, s2):
        client.post(API + f'/jobs/{j1["id"]}/view', headers=sh)
    client.post(API + f'/jobs/{j1["id"]}/view', headers=eh)                         # egasining o‘zi — hisoblanmaydi
    client.post(API + f'/jobs/{j1["id"]}/save', headers=s1)
    client.post(API + f'/jobs/{j1["id"]}/apply', headers=s1, json={'message': ''})
    client.post(API + f'/jobs/{j2["id"]}/apply', headers=s2, json={'message': ''})
    r = client.get(API + '/employer/insights', headers=eh, params={'days': 7}).json()
    t = r['totals']
    assert (t['jobs'], t['active'], t['views'], t['applications'], t['interests']) == (2, 2, 2, 2, 1)
    assert t['conversion'] == 100.0 and len(r['timeline']) == 7
    today = r['timeline'][-1]
    assert (today['views'], today['applications'], today['interests']) == (2, 2, 1)
    cats = {c['key']: c for c in r['byCategory']}
    assert cats['IT']['views'] == 2 and cats['Yetkazib berish']['applications'] == 1
    assert {c['key'] for c in r['byType']} == {'hourly', 'daily'}
    assert next(s for s in r['applicationsByStatus'] if s['key'] == 'sent')['count'] == 2
    assert client.get(API + '/employer/insights', headers=s1).status_code == 403


# ============================================================ 5. baholash
def test_mutual_reviews_after_completion(client, admin):
    eh, eu, _ = register(client, 'employer')
    sh, su, _ = register(client, 'student')
    job = _job(client, admin, eh)
    a = client.post(API + f'/jobs/{job["id"]}/apply', headers=sh, json={'message': ''}).json()
    assert client.post(API + f'/applications/{a["id"]}/review', headers=sh, json={'stars': 5}).status_code == 409   # hali yakunlanmagan
    assert client.patch(API + f'/employer/applications/{a["id"]}', headers=eh, json={'status': 'completed'}).status_code == 409
    client.patch(API + f'/employer/applications/{a["id"]}', headers=eh, json={'status': 'accepted'})
    assert client.post(API + f'/me/applications/{a["id"]}/complete', headers=sh).json()['status'] == 'completed'
    assert client.patch(API + f'/employer/applications/{a["id"]}', headers=eh, json={'status': 'declined'}).status_code == 409
    assert client.post(API + f'/applications/{a["id"]}/review', headers=sh, json={'stars': 6}).status_code == 422
    r1 = client.post(API + f'/applications/{a["id"]}/review', headers=sh, json={'stars': 5, 'comment': 'Juda yaxshi jamoa'})
    assert r1.status_code == 201
    assert client.post(API + f'/applications/{a["id"]}/review', headers=sh, json={'stars': 1}).status_code == 409   # takroriy
    assert client.post(API + f'/applications/{a["id"]}/review', headers=eh, json={'stars': 4, 'comment': 'Mas’uliyatli'}).status_code == 201
    info = client.get(API + f'/applications/{a["id"]}/reviews', headers=sh).json()
    assert info['canReview'] is False and info['mine']['stars'] == 5 and info['theirs']['stars'] == 4
    assert client.get(API + f'/users/{eu["id"]}/reviews', headers=sh).json()['avg'] == 5.0
    jobs = client.get(API + '/jobs', headers=sh).json()
    assert next(j for j in jobs if j['id'] == job['id'])['employerRating'] == {'avg': 5.0, 'count': 1}
    apps = client.get(API + '/employer/applications', headers=eh).json()
    row = next(x for x in apps if x['id'] == a['id'])
    assert row['student']['rating'] == {'avg': 4.0, 'count': 1} and row['reviewed'] is True
    # Support yashirsa — o‘rtachaga kirmaydi
    rv = next(r for r in admin.get(API + '/crm/reviews').json() if r['applicationId'] == a['id'] and r['fromRole'] == 'student')
    assert rv['fromName'] and rv['toName']
    admin.patch(API + f'/crm/reviews/{rv["id"]}', json={'hidden': True, 'note': 'Reklama'})
    assert client.get(API + f'/users/{eu["id"]}/reviews', headers=sh).json() == {'avg': None, 'count': 0, 'items': []}


def test_new_crm_endpoints_require_admin(client):
    for path in ('/crm/exams', '/crm/certificates', '/crm/chats', '/crm/reviews', '/crm/courses/c-en/final-test'):
        assert client.get(API + path).status_code in (401, 403)
