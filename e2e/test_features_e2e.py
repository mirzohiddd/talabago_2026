"""
TalabaGo — 5 ta yangi funksiyaning E2E tekshiruvi (haqiqiy brauzer, haqiqiy API, demo ma’lumotsiz):
  F1 Kurs yakuniy testi → QR-kodli PDF sertifikat (2 urinish), Support’da test muharriri va sertifikatlar
  F2 Ariza → chat: xabar yozish, javob, tarix, o‘qilgan belgisi, sarlavhadagi o‘qilmaganlar soni, Support nazorati
  F3 Faoliyat sohasi + ish turi filtrlari (Mini App va Support)
  F4 Ish beruvchi monitoringi (Statistika sahifasi) — raqamlar API bilan mos
  F5 Ish yakunlangach o‘zaro baholash, takroriy baholash bloki, Support’da yashirish
Talab: backend (8000) + Mini App (5173) + Support (5174) ishlab turgan bo‘lsin.
    E2E_ADMIN_USER=... E2E_ADMIN_PASS=... python3 e2e/test_features_e2e.py
"""
import asyncio
import os
import random
import sys

import httpx
from playwright.async_api import async_playwright

APP = os.environ.get('E2E_APP', 'http://localhost:5173')
A = APP + '/#'
C = os.environ.get('E2E_SUPPORT', 'http://localhost:5174')
API = os.environ.get('E2E_API', 'http://127.0.0.1:8000') + '/api/v1'
ADMIN = (os.environ.get('E2E_ADMIN_USER', 'm_777'), os.environ['E2E_ADMIN_PASS'])
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
RUN = random.randint(1000, 9999)
R, ERR = [], []

api = httpx.Client(base_url=API, trust_env=False, timeout=20)
adm = httpx.Client(base_url=API, trust_env=False, timeout=20, headers={'X-Requested-With': 'TalabaGo'})


def ok(name, cond, extra=''):
    R.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f' — {extra}' if extra and not cond else ''), flush=True)


def phone(n):
    code = ('90', '91', '93', '94', '95', '97', '98', '99', '33', '88')[n % 10]
    return f'+998 {code} {RUN % 1000:03d} {n // 100 % 100:02d} {n % 100:02d}'


def reg(role, n, first):
    body = {'role': role, 'firstName': first, 'lastName': 'Testov', 'phone': phone(n), 'password': 'parol12345'}
    if role == 'employer':
        body['company'] = f'Feat Kompaniya {RUN}'
    r = api.post('/auth/register', json=body)
    assert r.status_code == 201, r.text
    return r.json()


def H(u):
    return {'Authorization': f'Bearer {u["token"]}'}


JOB = {'title': f'Frontend stajyor {RUN}', 'company': f'Feat Kompaniya {RUN}', 'city': 'Toshkent', 'district': 'Chilonzor', 'format': 'offline', 'type': 'hourly',
       'salary': 40000, 'salaryPeriod': 'hour', 'workTime': 'evening', 'schedule': '16:00-20:00', 'category': 'IT',
       'description': 'Vue va Tailwind bilan kichik sahifalar yasash, kod sharhida qatnashish.', 'phone': '+998 90 000 00 19'}
QUESTIONS = [{'q': f'E2E savol {i}?', 'options': ['Birinchi', 'Ikkinchi', 'Uchinchi'], 'answer': i % 3} for i in range(4)]


async def ctx_page(br, u=None, viewport=None, mobile=False):
    ctx = await br.new_context(viewport=viewport or {'width': 1280, 'height': 860}, is_mobile=mobile, has_touch=mobile)
    if u:
        await ctx.add_init_script("try { localStorage.setItem('talabago_session_v2', %r) } catch (e) {}"
                                  % __import__('json').dumps({'userId': u['user']['id'], 'role': u['user']['role'], 'token': u['token'], 'onboarding': {'step': 1, 'role': None}}))
    p = await ctx.new_page()
    p.on('pageerror', lambda e: ERR.append(f'PAGEERR {e}'))
    p.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and ERR.append(m.text[:200]))
    return ctx, p


async def screen(p):
    return await p.evaluate("""() => ({ txt: (document.querySelector('#app')?.innerText || '').trim().length,
      bg: getComputedStyle(document.body).backgroundColor, w: document.scrollingElement.scrollWidth, vw: innerWidth })""")


async def crm_login(p):
    await p.goto(C + '/login'); await p.wait_for_timeout(400)
    await p.fill('input[name=username]', ADMIN[0]); await p.fill('input[name=password]', ADMIN[1])
    await p.click('button[type=submit]')
    await p.wait_for_url('**/dashboard', timeout=10000); await p.wait_for_timeout(800)


async def main():
    assert adm.post('/auth/admin/login', json={'username': ADMIN[0], 'password': ADMIN[1]}).status_code == 200
    emp, st = reg('employer', 41, 'Feruza'), reg('student', 42, 'Jamshid')
    # ---- tayyorlash: ish beruvchi e’loni (IT, soatlik) + ikkinchi e’lon (Savdo, kunlik), Support tasdiqlaydi
    jobs = []
    for over in ({}, {'title': f'Kassir {RUN}', 'category': 'Savdo', 'type': 'daily', 'salaryPeriod': 'day', 'salary': 150000}):
        r = api.post('/employer/jobs', headers=H(emp), json={**JOB, **over})
        assert r.status_code == 201, r.text
        assert adm.post(f'/crm/jobs/{r.json()["id"]}/approve').status_code == 200
        jobs.append(r.json())
    ok('F3 Sohasiz vakansiya serverda rad etiladi', api.post('/employer/jobs', headers=H(emp), json={**JOB, 'category': ''}).status_code == 422)

    async with async_playwright() as pw:
        args = [a for a in os.environ.get('E2E_CHROME_ARGS', '').split(';') if a]
        br = await pw.chromium.launch(executable_path=CHROME, args=args)

        # ================= F3. Faoliyat sohasi va ish turi filtrlari =================
        ctx, p = await ctx_page(br, st, {'width': 390, 'height': 844}, True)
        await p.goto(A + '/student/jobs'); await p.wait_for_timeout(1800)
        chips = p.locator('[data-testid=category-chips]')
        ok('F3 Mobil: soha chiplari ko‘rinadi', await chips.is_visible())
        await chips.get_by_text('Savdo', exact=True).click(); await p.wait_for_timeout(900)
        txt = await p.inner_text('[data-testid=job-list]')
        ok('F3 “Savdo” tanlanganda faqat savdo e’loni', f'Kassir {RUN}' in txt and f'Frontend stajyor {RUN}' not in txt, txt[:200])
        await chips.get_by_text('IT', exact=True).click(); await p.wait_for_timeout(900)
        txt = await p.inner_text('[data-testid=job-list]')
        ok('F3 “IT” tanlanganda faqat IT e’loni', f'Frontend stajyor {RUN}' in txt and f'Kassir {RUN}' not in txt)
        api_it = [j['id'] for j in api.get('/jobs', headers=H(st), params={'category': 'IT', 'type': 'hourly'}).json()]
        ok('F3 API filtr: category=IT&type=hourly', jobs[0]['id'] in api_it and jobs[1]['id'] not in api_it)
        st_ = await screen(p)
        ok('F3 Mobil: gorizontal siljish yo‘q', st_['w'] <= st_['vw'] + 1, st_)
        await ctx.close()

        # ---- ko‘rish va saqlash (monitoring uchun real hodisalar)
        api.post(f'/jobs/{jobs[0]["id"]}/view', headers=H(st)); api.post(f'/jobs/{jobs[1]["id"]}/view', headers=H(st))
        api.post(f'/jobs/{jobs[0]["id"]}/save', headers=H(st))

        # ================= F2. Ariza → chat =================
        app = api.post(f'/jobs/{jobs[0]["id"]}/apply', headers=H(st), json={'message': 'Assalomu alaykum, tajribam bor'})
        assert app.status_code == 201, app.text
        app = app.json()
        ctx_s, ps = await ctx_page(br, st, {'width': 390, 'height': 844}, True)
        ctx_e, pe = await ctx_page(br, emp)
        await ps.goto(A + '/student/applications'); await ps.wait_for_timeout(1500)
        await ps.locator('[data-testid=open-chat]').first.click(); await ps.wait_for_timeout(1500)
        ok('F2 Talaba: arizadan chat ochildi', '/student/chats/' in ps.url and await ps.locator('[data-testid=chat-room]').is_visible(), ps.url)
        await ps.fill('[data-testid=chat-input] textarea, textarea[data-testid=chat-input], [data-testid=chat-input]', 'Salom! Ertaga kelsam bo‘ladimi?')
        await ps.click('[data-testid=chat-send]'); await ps.wait_for_timeout(900)
        ok('F2 Talaba xabari tarixda ko‘rindi', 'Ertaga kelsam' in await ps.inner_text('[data-testid=chat-room]'))
        await pe.goto(A + '/employer/jobs'); await pe.wait_for_timeout(1800)
        badge = pe.locator('[data-testid=chat-badge]')
        ok('F2 Ish beruvchi sarlavhasida o‘qilmagan xabar belgisi', await badge.count() == 1 and (await badge.inner_text()).strip() == '1')
        notes = [n['title'] for n in api.get('/notifications', headers=H(emp)).json()]
        ok('F2 Ish beruvchiga bildirishnoma keldi', any(t.startswith('Yangi xabar') for t in notes), notes[:3])
        await pe.click('[data-testid=chat-btn]'); await pe.wait_for_timeout(1500)
        await pe.locator('[data-testid=chat-list] button[data-testid^=chat-ch]').first.click(); await pe.wait_for_timeout(1500)
        ok('F2 Ish beruvchi xabarni o‘qidi', 'Ertaga kelsam' in await pe.inner_text('[data-testid=chat-room]'))
        await pe.fill('[data-testid=chat-input]', 'Ha, soat 16:00 da kuting')
        await pe.keyboard.press('Enter'); await pe.wait_for_timeout(900)
        await ps.wait_for_timeout(5000)                                         # talaba oynasi 4 s da yangilanadi
        room = await ps.inner_text('[data-testid=chat-room]')
        ticks = await ps.locator('[data-testid=read-tick]').count()
        ok('F2 Talabaga javob keldi (sahifani yangilamasdan)', 'soat 16:00' in room, room[-200:])
        ok('F2 Talaba xabarida “o‘qildi” belgisi', ticks >= 1)
        await ps.reload(); await ps.wait_for_timeout(1800)
        room = await ps.inner_text('[data-testid=chat-room]')
        ok('F2 Qayta ochilganda tarix saqlangan', all(s in room for s in ('Ertaga kelsam', 'soat 16:00')))
        st_ = await screen(ps)
        ok('F2 Mobil chat: oq fon, siljish yo‘q', st_['bg'] == 'rgb(255, 255, 255)' and st_['w'] <= st_['vw'] + 1, st_)
        await ctx_s.close()

        # ================= F4. Monitoring =================
        ins = api.get('/employer/insights', headers=H(emp), params={'days': 30}).json()
        await pe.goto(A + '/employer/stats'); await pe.wait_for_timeout(2000)
        kv = {k: (await pe.inner_text(f'[data-testid=kpi-{k}]')).strip() for k in ('jobs', 'views', 'apps', 'int')}
        ok('F4 KPI raqamlari API bilan mos', kv == {'jobs': str(ins['totals']['jobs']), 'views': str(ins['totals']['views']), 'apps': str(ins['totals']['applications']), 'int': str(ins['totals']['interests'])}, (kv, ins['totals']))
        ok('F4 Real hodisalar hisoblandi (2 e’lon, ≥2 ko‘rish, 1 ariza, 1 qiziqish)', ins['totals']['jobs'] == 2 and ins['totals']['views'] >= 2 and ins['totals']['applications'] == 1 and ins['totals']['interests'] == 1, ins['totals'])
        ok('F4 Grafik chizildi', await pe.locator('[data-testid=timeline-chart] svg path').count() >= 2)
        cat = await pe.inner_text('[data-testid=by-category]')
        ok('F4 Faoliyat sohalari kesimi', 'IT' in cat and 'Savdo' in cat, cat)
        ok('F4 Ish turlari kesimi', await pe.locator('[data-testid=by-type] li').count() == 2)
        await pe.click('[data-testid=period] >> text=7 kun'); await pe.wait_for_timeout(1200)
        ok('F4 Davr almashtirildi (7 kun)', await pe.locator('[data-testid=kpis]').is_visible())

        # ================= F5. Ishni yakunlash va o‘zaro baholash =================
        await pe.goto(A + '/employer/applications'); await pe.wait_for_timeout(1800)
        await pe.locator('[data-testid=incoming-table] button:has-text("Ko‘rish")').first.click(); await pe.wait_for_timeout(900)
        await pe.click('[data-testid=act-accept]'); await pe.wait_for_timeout(1200)
        await pe.click('[data-testid=act-complete]'); await pe.wait_for_timeout(1200)
        status = next(a for a in api.get('/me/applications', headers=H(st)).json() if a['id'] == app['id'])['status']
        ok('F5 Ish beruvchi ishni yakunladi → status “completed”', status == 'completed', status)
        await pe.click('[data-testid=act-review]'); await pe.wait_for_timeout(600)
        await pe.click('[data-testid=star-5]'); await pe.fill('[data-testid=review-comment] textarea, textarea[data-testid=review-comment]', 'Mas’uliyatli va o‘z vaqtida keldi')
        await pe.click('[data-testid=review-send]'); await pe.wait_for_timeout(1200)
        ok('F5 Ish beruvchi talabani baholadi', await pe.locator('text=Baholandi').count() >= 1 and await pe.locator('[data-testid=act-review]').count() == 0)
        again = api.post(f'/applications/{app["id"]}/review', headers=H(emp), json={'stars': 1, 'comment': 'yana'})
        ok('F5 Takroriy baholash bloklandi (409)', again.status_code == 409, again.status_code)

        ctx_s, ps = await ctx_page(br, st)
        await ps.goto(A + '/student/applications'); await ps.wait_for_timeout(1800)
        await ps.wait_for_timeout(500)
        btn = ps.locator('[data-testid=review-employer]').first
        ok('F5 Talabada “Ish beruvchini baholash” tugmasi', await btn.count() == 1)
        await btn.click(); await ps.wait_for_timeout(600)
        await ps.click('[data-testid=star-4]'); await ps.fill('[data-testid=review-comment] textarea, textarea[data-testid=review-comment]', 'Yaxshi jamoa, maosh o‘z vaqtida')
        await ps.click('[data-testid=review-send]'); await ps.wait_for_timeout(1200)
        ok('F5 Talaba baholagach tugma yo‘qoldi', await ps.locator('[data-testid=review-employer]').count() == 0)
        rv = api.get(f'/users/{emp["user"]["id"]}/reviews', headers=H(st)).json()
        ok('F5 Ish beruvchi reytingi 4.0 (1 ta baho)', rv['avg'] == 4 and rv['count'] == 1, rv)
        j = api.get(f'/jobs/{jobs[0]["id"]}', headers=H(st)).json()
        ok('F5 Vakansiyada ish beruvchi reytingi ko‘rinadi', (j.get('employerRating') or {}).get('count') == 1, j.get('employerRating'))
        await ctx_s.close(); await ctx_e.close()

        # ================= F1. Kurs yakuniy testi va sertifikat =================
        r = adm.put('/crm/courses/c-en/final-test', json={'status': 'published', 'passPercent': 75, 'maxAttempts': 2, 'questions': QUESTIONS})
        ok('F1 Support yakuniy testni nashr qildi', r.status_code == 200, r.text[:200])
        course = next(c for c in api.get('/courses', headers=H(st)).json() if c['id'] == 'c-en')
        ok('F1 Talabaga to‘g‘ri javoblar yuborilmaydi', 'finalTest' not in course and all('answer' not in q for q in api.get('/courses/c-en/exam', headers=H(st)).json()['questions']))
        ctx, p = await ctx_page(br, st, {'width': 390, 'height': 844}, True)
        await p.goto(A + '/student/courses/c-en/exam'); await p.wait_for_timeout(1800)
        ok('F1 Darslar tugamaguncha test qulflangan', 'barcha darslar tugagach' in (await p.inner_text('[data-testid=exam-start]')).lower())
        for l in course['lessons']:
            ans = [q['answer'] for q in l.get('quiz') or []]
            api.post(f'/courses/c-en/lessons/{l["id"]}/complete', headers=H(st), json={'answers': ans if l.get('quiz') else None})
        await p.goto(A + '/student/courses/c-en'); await p.wait_for_timeout(1500)
        await p.click('[data-testid=final-exam]'); await p.wait_for_timeout(1500)
        ok('F1 Kurs sahifasidan yakuniy testga o‘tildi', '/exam' in p.url, p.url)
        # 1-urinish: hammasi noto‘g‘ri
        await p.click('[data-testid=exam-begin]'); await p.wait_for_timeout(500)
        for i, q in enumerate(QUESTIONS):
            await p.click(f'[data-testid=q{i}-o{(q["answer"] + 1) % 3}]')
        await p.click('[data-testid=exam-submit]'); await p.wait_for_timeout(400)
        await p.click('[data-testid=confirm-ok]'); await p.wait_for_timeout(1500)
        res = await p.inner_text('[data-testid=exam-result]')
        ok('F1 1-urinish: o‘tmadi, 1 urinish qoldi', 'o‘ta olmadingiz' in res and '1' in res, res)
        # 2-urinish: to‘g‘ri
        await p.click('[data-testid=exam-begin]'); await p.wait_for_timeout(500)
        for i, q in enumerate(QUESTIONS):
            await p.click(f'[data-testid=q{i}-o{q["answer"]}]')
        await p.click('[data-testid=exam-submit]'); await p.wait_for_timeout(400)
        await p.click('[data-testid=confirm-ok]'); await p.wait_for_timeout(1800)
        cert_txt = await p.inner_text('[data-testid=certificate]')
        ok('F1 2-urinish: o‘tdi, sertifikat kartasi chiqdi', 'Sertifikatingiz tayyor' in cert_txt and 'TG-' in cert_txt, cert_txt)
        ok('F1 Uchinchi urinish yo‘q (start kartasi yashirin)', await p.locator('[data-testid=exam-begin]').count() == 0)
        certs = api.get('/me/certificates', headers=H(st)).json()
        code = certs[0]['code']
        pdf = api.get(f'/certificates/{code}/pdf')
        ok('F1 PDF sertifikat yuklab olinadi', pdf.status_code == 200 and pdf.content[:5] == b'%PDF-' and len(pdf.content) > 20000, (pdf.status_code, len(pdf.content)))
        vp = await br.new_page()
        await vp.goto(API.replace('/api/v1', '') + f'/api/v1/certificates/{code}/page'); await vp.wait_for_timeout(500)
        ok('F1 QR tekshirish sahifasi: “Sertifikat haqiqiy”', 'Sertifikat haqiqiy' in await vp.inner_text('body'))
        await vp.close()
        ok('F1 3-urinish API’da ham bloklangan', api.post('/courses/c-en/exam/submit', headers=H(st), json={'answers': [0] * 4}).status_code == 409)
        await ctx.close()

        # ================= Support CRM: yangi bo‘limlar =================
        ctx, p = await ctx_page(br)
        await crm_login(p)
        for path, sel, label in (('/certificates', '[data-testid=certs-table]', 'Sertifikatlar'), ('/chats', '[data-testid=crm-chats-table]', 'Chatlar nazorati'),
                                 ('/reviews', '[data-testid=crm-reviews-table]', 'Baholar nazorati')):
            await p.goto(C + path); await p.wait_for_timeout(1500)
            s_ = await screen(p)
            ok(f'CRM {label}: sahifa ochildi, oq ekran emas', await p.locator(sel).count() == 1 and s_['txt'] > 80, s_)
        # sertifikat bekor qilish → ommaviy sahifada “bekor qilingan”
        await p.goto(C + '/certificates'); await p.wait_for_timeout(1200)
        row = p.locator(f'[data-testid=certs-table] tr:has-text("{code}")')
        await row.locator('[data-testid=cert-revoke]').click(); await p.wait_for_timeout(400)
        await p.click('[data-testid=cert-revoke-confirm]'); await p.wait_for_timeout(1200)
        ok('CRM Sertifikat bekor qilindi → tekshiruvda yaroqsiz', api.get(f'/certificates/{code}').json()['valid'] is False)
        # chat: xabarni yashirish va suhbatni cheklash
        await p.goto(C + '/chats'); await p.wait_for_timeout(1200)
        await p.locator(f'[data-testid=crm-chats-table] tr:has-text("Frontend stajyor {RUN}")').click(); await p.wait_for_timeout(1200)
        ok('CRM Chat tarixi ko‘rinadi', 'Ertaga kelsam' in await p.inner_text('[data-testid=crm-chat]'))
        await p.locator('[data-testid=msg-hide]').first.click(); await p.wait_for_timeout(900)
        chat_id = api.get('/chats', headers=H(st)).json()[0]['id']
        msgs = api.get(f'/chats/{chat_id}/messages', headers=H(st)).json()
        ok('CRM Yashirilgan xabar foydalanuvchiga matnsiz ko‘rinadi', 'Ertaga kelsam' not in msgs[0]['text'], msgs[0]['text'])
        await p.click('[data-testid=chat-lock]'); await p.wait_for_timeout(900)
        ok('CRM Cheklangan suhbatga yozib bo‘lmaydi (403)', api.post(f'/chats/{chat_id}/messages', headers=H(st), json={'text': 'salom'}).status_code == 403)
        await p.keyboard.press('Escape'); await p.wait_for_timeout(400)
        # baholar: yashirish → reytingga kirmaydi
        await p.goto(C + '/reviews'); await p.wait_for_timeout(1200)
        await p.locator('[data-testid=crm-reviews-table] tr:has-text("Yaxshi jamoa") [data-testid=review-hide]').click(); await p.wait_for_timeout(400)
        await p.click('[data-testid=review-hide-confirm]'); await p.wait_for_timeout(1200)
        rv = api.get(f'/users/{emp["user"]["id"]}/reviews', headers=H(st)).json()
        ok('CRM Yashirilgan baho reytingdan chiqdi', rv['count'] == 0, rv)
        # kurs muharriri: “Yakuniy test” bo‘limi
        await p.goto(C + '/courses/c-en'); await p.wait_for_timeout(1500)
        await p.click('[data-testid=course-view] >> text=Yakuniy test'); await p.wait_for_timeout(1200)
        ok('CRM Kurs → Yakuniy test muharriri (4 savol)', await p.locator('[data-testid=final-test-editor] [data-testid^=ft-q]').count() == 4)
        await p.click('[data-testid=ft-add]'); await p.wait_for_timeout(300)
        await p.click('[data-testid=ft-save]'); await p.wait_for_timeout(800)
        ok('CRM Bo‘sh savol bilan saqlanmaydi (xato ko‘rsatildi)', await p.locator('[data-testid=final-test-editor] [role=alert]').count() == 1)
        # ish e’lonlari: soha filtri
        await p.goto(C + '/jobs'); await p.wait_for_timeout(1500)
        await p.select_option('[data-testid=filter2] select', 'Savdo'); await p.wait_for_timeout(600)
        t_ = await p.inner_text('[data-testid=jobs-table]')
        ok('CRM Ish e’lonlari: soha bo‘yicha filtr', f'Kassir {RUN}' in t_ and f'Frontend stajyor {RUN}' not in t_)
        # mobil CRM: yangi sahifalarda siljish yo‘q
        await p.set_viewport_size({'width': 390, 'height': 844})
        for path in ('/certificates', '/chats', '/reviews'):
            await p.goto(C + path); await p.wait_for_timeout(1000)
            s_ = await screen(p)
            ok(f'CRM mobil {path}: sahifa kengligi ekranga sig‘adi', s_['w'] <= s_['vw'] + 1 and s_['txt'] > 40, s_)
        await ctx.close()

        # tozalash: test kursi testini qoralamaga qaytaramiz, e’lonlarni o‘chiramiz
        adm.put('/crm/courses/c-en/final-test', json={'status': 'draft', 'passPercent': 75, 'maxAttempts': 2, 'questions': QUESTIONS})
        await br.close()

    errs = [e for e in ERR if 'favicon' not in e]
    ok('Konsolda JS xatosi yo‘q', not errs, errs[:5])
    passed = sum(1 for _, c in R if c)
    print(f'\n{passed}/{len(R)} PASS')
    sys.exit(0 if passed == len(R) else 1)


if __name__ == '__main__':
    asyncio.run(main())
