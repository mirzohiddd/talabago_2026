"""
TalabaGo — E2E: Support panelidan akkauntsiz e’lon qo‘shish (ish va turar joy), tasdiqlash oqimi va talaba ilovasida ko‘rinishi.

    E2E_ADMIN_USER=... E2E_ADMIN_PASS=... python3 e2e/test_admin_listings_e2e.py
Faqat test bazasida ishga tushiring (DATA_DIR — vaqtinchalik papka).
"""
import asyncio
import io
import os
import random
import sys

import httpx
from PIL import Image
from playwright.async_api import async_playwright

APP = os.environ.get('E2E_APP', 'http://localhost:5173') + '/#'
C = os.environ.get('E2E_SUPPORT', 'http://localhost:5174')
API = os.environ.get('E2E_API', 'http://127.0.0.1:8000') + '/api/v1'
ADMIN = (os.environ.get('E2E_ADMIN_USER', 'm_777'), os.environ['E2E_ADMIN_PASS'])
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
RUN = random.randint(100, 999)
R, ERR = [], []
JOB_TITLE = f'Ofitsiant (kechki smena) {RUN}'
HOUSE_TITLE = f'Talabalar uchun xona {RUN}'


def ok(name, cond, extra=''):
    R.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f' — {extra}' if extra and not cond else ''), flush=True)


def photo(path):
    Image.new('RGB', (640, 480), (16, 185, 129)).save(path)
    return path


async def main():
    tmp = photo(f'/tmp/e2e-house-{RUN}.png')
    async with async_playwright() as pw:
        br = await pw.chromium.launch(executable_path=CHROME)
        ctx = await br.new_context(viewport={'width': 1440, 'height': 900})
        s = await ctx.new_page()
        s.on('pageerror', lambda e: ERR.append(str(e)[:200]))
        await s.goto(C + '/login'); await s.fill('input[name=username]', ADMIN[0]); await s.fill('input[name=password]', ADMIN[1])
        await s.click('button[type=submit]'); await s.wait_for_url('**/dashboard', timeout=15000)

        # ---------- 1. Ish e’loni (darhol nashr)
        await s.goto(C + '/jobs'); await s.wait_for_timeout(1200)
        ok('1 “E’lon qo‘shish” tugmasi bor', await s.locator('[data-testid=add-listing]').count() == 1)
        await s.click('[data-testid=add-listing]'); await s.wait_for_selector('[data-testid=admin-listing-form]')
        await s.fill('[data-testid=al-title] input', JOB_TITLE)
        await s.fill('[data-testid=al-company] input', 'Kafe (Chilonzor)')
        await s.fill('[data-testid=al-salary] input', '25000')
        await s.fill('[data-testid=al-schedule] input', 'Du–Ju, 18:00–23:00')
        await s.locator('[data-testid=al-district] select').select_option('Chilonzor')
        await s.fill('[data-testid=al-address] input', 'Bunyodkor ko‘chasi 12')
        await s.fill('[data-testid=al-req] textarea', '18 yoshdan katta\nMuloqotga ochiq')
        await s.fill('[data-testid=al-desc] textarea', 'Mehmonlarga xizmat ko‘rsatish, buyurtma qabul qilish. O‘rgatamiz.')
        await s.locator('[data-testid=al-phone] input').fill('90 555 44 33')
        await s.fill('[data-testid=al-src-name] input', '@toshkent_ish')
        # rozilik belgilanmagan → nashr tugmasi o‘chiq
        ok('1 Rozilik belgilanmaguncha nashr qilib bo‘lmaydi', await s.locator('[data-testid=al-publish]').is_disabled())
        for t in ('al-contacted', 'al-consent', 'al-phone-consent'):
            await s.click(f'[data-testid={t}]')
        await s.click('[data-testid=al-publish]')
        await s.click('[data-testid=al-save]'); await s.wait_for_timeout(1200)
        row = s.locator(f'[data-testid=jobs-table] tr:has-text("{JOB_TITLE}")')
        ok('1 Ish e’loni jadvalda “Faol” va “Admin” belgisi bilan', await row.count() == 1 and 'Faol' in await row.inner_text() and await row.locator('[data-testid=admin-tag]').count() == 1,
           await row.inner_text() if await row.count() else 'qator yo‘q')
        await row.locator('button[aria-label="Ko‘rish"]').click(); await s.wait_for_timeout(500)
        meta = await s.locator('[data-testid=admin-meta]').inner_text()
        ok('1 Batafsil oynada manba va tekshiruv ma’lumotlari', '@toshkent_ish' in meta and 'Egasi bilan bog‘lanildi' in meta, meta[:200])
        await s.keyboard.press('Escape'); await s.wait_for_timeout(300)

        # ---------- 1b. Minimal e’lon: faqat lavozim + manba, maosh “Kelishiladi” → “Tasdiqlashni kutmoqda”
        await s.click('[data-testid=add-listing]'); await s.wait_for_selector('[data-testid=admin-listing-form]')
        await s.fill('[data-testid=al-title] input', f'Laborant yordamchisi {RUN}')
        await s.click('[data-testid=al-salary-nego]')
        ok('1b “Kelishiladi” tanlanganda maosh maydoni o‘chadi', await s.locator('[data-testid=al-salary] input').is_disabled())
        await s.click('[data-testid=al-save]'); await s.wait_for_timeout(500)
        ok('1b Manba nomisiz saqlanmaydi (xato ko‘rsatiladi)', await s.locator('[data-testid=admin-listing-form]').count() == 1)
        await s.fill('[data-testid=al-src-name] input', '@lab_ishlar')
        await s.click('[data-testid=al-save]'); await s.wait_for_timeout(1200)
        row = s.locator(f'[data-testid=jobs-table] tr:has-text("Laborant yordamchisi {RUN}")')
        ok('1b Minimal e’lon saqlandi: “Tekshiruvda”, maosh “Kelishiladi”', await row.count() == 1 and 'Tekshiruvda' in await row.inner_text() and 'Kelishiladi' in await row.inner_text(),
           await row.inner_text() if await row.count() else 'qator yo‘q')

        # ---------- 2. Turar joy (tasdiqlashni kutadi → tasdiqlash)
        await s.goto(C + '/housing'); await s.wait_for_timeout(1000)
        await s.click('[data-testid=add-listing]'); await s.wait_for_selector('[data-testid=admin-listing-form]')
        await s.fill('[data-testid=al-title] input', HOUSE_TITLE)
        await s.fill('[data-testid=al-price] input', '1800000')
        await s.fill('[data-testid=al-rooms] input', '1')
        await s.locator('[data-testid=al-district] select').select_option('Yunusobod')
        await s.fill('[data-testid=al-address] input', 'Yunusobod 4-mavze')
        await s.fill('[data-testid=al-desc] textarea', 'Metroga yaqin, jihozlangan, Wi-Fi bor. Faqat talabalar uchun.')
        await s.set_input_files('[data-testid=al-photos]', tmp); await s.wait_for_timeout(1200)
        await s.fill('[data-testid=al-src-name] input', 'Ijara Toshkent guruhi')
        await s.click('[data-testid=al-save]'); await s.wait_for_timeout(1200)
        row = s.locator(f'[data-testid=houses-table] tr:has-text("{HOUSE_TITLE}")')
        ok('2 Turar joy “Tekshiruvda” holatida saqlandi', await row.count() == 1 and 'Tekshiruvda' in await row.inner_text())
        ok('2 Kutayotgan e’lonlar soni ko‘rinadi', await s.locator('[data-testid=pending-count]').count() == 1)
        await row.locator('[data-testid=approve]').click(); await s.wait_for_timeout(800)
        ok('2 Rozilik yo‘q — tasdiqlash rad etildi (xato xabari)', 'Tekshiruvda' in await row.inner_text())
        # tahrirlash → rozilik belgilash → tasdiqlash
        await row.locator('button[aria-label="Tahrirlash"]').click(); await s.wait_for_selector('[data-testid=admin-listing-form]')
        for t in ('al-contacted', 'al-consent'):
            await s.click(f'[data-testid={t}]')
        await s.click('[data-testid=al-save]'); await s.wait_for_timeout(1000)
        await row.locator('[data-testid=approve]').click(); await s.wait_for_timeout(1000)
        ok('2 Egasi roziligidan keyin tasdiqlandi (Faol)', 'Faol' in await row.inner_text(), await row.inner_text())
        await ctx.close()

        # ---------- 3. Talaba ilovasida
        with httpx.Client(base_url=API, trust_env=False) as api:
            phone = f'+998 93 {RUN} 77 1{RUN % 10}'
            r = api.post('/auth/register', json={'role': 'student', 'firstName': 'Sardor', 'lastName': 'Sinov', 'phone': phone, 'password': 'Parol2026'})
            ok('3 Talaba ro‘yxatdan o‘tdi (API)', r.status_code == 201, r.text[:120])
            token = r.json().get('token'); uid = r.json()['user']['id']
            jobs = api.get('/jobs', headers={'Authorization': f'Bearer {token}'}).json()
            j = next((x for x in jobs if x['title'] == JOB_TITLE), None)
            ok('3 API: admin ish e’loni talabaga ko‘rinadi, ichki ma’lumotsiz', j and 'source' not in j and 'verification' not in j and j['phone'], j)
            houses = api.get('/houses', headers={'Authorization': f'Bearer {token}'}).json()
            h = next((x for x in houses if x['title'] == HOUSE_TITLE), None)
            ok('3 API: telefon roziligi yo‘q uy — telefon yashirin', h and h['phone'] is None and h['owner']['id'] is None, h and h.get('owner'))
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        p = await ctx.new_page()
        p.on('pageerror', lambda e: ERR.append(str(e)[:200]))
        # sessiya: API orqali olingan token (login sahifasi alohida E2E’da tekshirilgan)
        await p.goto(APP + '/welcome'); await p.evaluate('localStorage.clear()')
        await p.evaluate("([t, id]) => localStorage.setItem('talabago_session_v2', JSON.stringify({ token: t, userId: id, role: 'student', onboarding: { step: 1, role: null } }))", [token, uid])
        await p.reload(); await p.wait_for_timeout(1200)
        await p.goto(APP + '/student/jobs'); await p.wait_for_timeout(1800)
        card = p.locator(f'text={JOB_TITLE}').first
        ok('3 Ilova: “Ishlar” bo‘limida admin e’loni', await card.count() == 1)
        if await card.count():
            await card.click(); await p.wait_for_timeout(800)
            d = await p.locator('[data-testid=job-detail]').inner_text()
            ok('3 Ilova: “TalabaGo tekshirgan” belgisi, manzil va telefon', 'TalabaGo tekshirgan' in d and 'Bunyodkor' in d and '+998 90 555 44 33' in d, d[:300])
            btn = p.locator('button:has-text("Ariza yuborish")').first
            if await btn.count():
                await btn.click(); await p.wait_for_timeout(500)
                await p.locator('button:has-text("Yuborish"), button:has-text("Ariza yuborish")').last.click(); await p.wait_for_timeout(1200)
                ok('3 Ilova: admin e’loniga ariza yuborildi', await p.locator('[data-testid=apply-done]').count() == 1)
        await p.goto(APP + '/student/housing'); await p.wait_for_timeout(1800)
        ok('3 Ilova: “Turar joy” bo‘limida admin e’loni', await p.locator(f'text={HOUSE_TITLE}').count() >= 1)
        await br.close()

    print('\n' + ('\n'.join(sorted(set(ERR))[:10]) if ERR else 'Brauzer konsolida JS xatosi yo‘q'))
    passed = sum(1 for _, o in R if o)
    print(f'\n{passed}/{len(R)} PASS')
    sys.exit(0 if passed == len(R) else 1)


asyncio.run(main())
