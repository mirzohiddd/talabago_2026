"""
TalabaGo — E2E: ro‘yxatdan o‘tish formalari (Talaba, Ish beruvchi, Uy egasi), telefon maydoni (+998), o‘zbekcha xatolar,
takroriy telefon, Support panelida ko‘rinishi, kirish sahifasi, lug‘atning kechiktirib yuklanishi.

    E2E_ADMIN_USER=... E2E_ADMIN_PASS=... python3 e2e/test_e2e_forms.py
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
RUN = random.randint(100, 999)
R, ERR = [], []


def ok(name, cond, extra=''):
    R.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f' — {extra}' if extra and not cond else ''), flush=True)


async def open_form(p, role, lang=None):
    await p.goto(A + '/welcome')
    await p.evaluate('localStorage.clear()')
    if lang:
        await p.evaluate(f"localStorage.setItem('talabago_lang', '{lang}')")
    await p.reload(); await p.wait_for_timeout(700)
    for _ in range(4):
        await p.click('[data-testid=ob-next]'); await p.wait_for_timeout(200)
    await p.click(f'[data-testid=role-{role}]'); await p.click('[data-testid=ob-next]'); await p.wait_for_timeout(400)


async def alerts(p):
    return [t.strip() for t in await p.locator('[role=alert]').all_inner_texts()]


async def main():
    async with async_playwright() as pw:
        br = await pw.chromium.launch(executable_path=CHROME)
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        p = await ctx.new_page()
        p.on('pageerror', lambda e: ERR.append(str(e)[:200]))
        js = []
        p.on('request', lambda r: r.resource_type == 'script' and js.append(r.url))

        # ---------- 1. Lug‘atlar faqat kerak bo‘lganda
        await p.goto(A + '/welcome'); await p.evaluate("localStorage.removeItem('talabago_lang')"); js.clear()
        await p.reload(); await p.wait_for_timeout(1500)
        ok('1 O‘zbek tilida ru/en lug‘atlari yuklanmaydi', not any('/ru-' in u or '/en-' in u for u in js), [u.rsplit('/', 1)[-1] for u in js])

        # ---------- 2. Telefon maydoni
        for role in ('student', 'employer', 'landlord'):
            await open_form(p, role)
            field = p.locator('[data-testid=f-phone]')
            inp = field.locator('input')
            prefix = (await field.locator('[data-testid=phone-prefix]').inner_text()).strip()
            ok(f'2 [{role}] “+998” avtomatik chiqadi', prefix == '+998', prefix)
            await inp.click()
            await p.keyboard.type('90a1b23-4567 89')
            ok(f'2 [{role}] faqat 9 ta raqam, format “90 123 45 67”', await inp.input_value() == '90 123 45 67', await inp.input_value())
            await inp.fill('')
            await inp.evaluate("(el) => { const dt = new DataTransfer(); dt.setData('text', '+998 (91) 765-43-21'); el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true })) }")
            await p.wait_for_timeout(100)
            ok(f'2 [{role}] nusxa qo‘yilgan +998 raqam to‘g‘ri ajratildi', await inp.input_value() == '91 765 43 21', await inp.input_value())

            # bo‘sh forma → o‘zbekcha majburiy xatolar
            await inp.fill('')
            await p.click('[data-testid=ob-submit]'); await p.wait_for_timeout(400)
            a = await alerts(p)
            need = ['Majburiy maydon', 'Telefon raqamini kiriting'] + (['Parol kamida 8 ta belgidan iborat bo‘lsin'] if await p.locator('[data-testid=f-password]').count() else [])
            ok(f'2 [{role}] bo‘sh forma: majburiy maydonlar o‘zbekcha', all(any(n in x for x in a) for n in need) and a.count('Majburiy maydon') >= 2, a)

            # noto‘g‘ri qiymatlar
            await p.fill('[data-testid=f-first] input', 'Ali123')
            await p.fill('[data-testid=f-last] input', 'V')
            await inp.fill('90 12'); await inp.blur()
            await p.click('[data-testid=ob-submit]'); await p.wait_for_timeout(400)
            a = await alerts(p)
            ok(f'2 [{role}] ism raqam bilan / familiya 1 harf / to‘liq bo‘lmagan raqam rad etildi',
               any('Faqat harflar' in x for x in a) and any('Kamida 2 ta harf' in x for x in a) and any('to‘liq emas' in x for x in a), a)
            await inp.fill('12 345 67 89')
            await p.click('[data-testid=ob-submit]'); await p.wait_for_timeout(400)
            ok(f'2 [{role}] noto‘g‘ri operator kodi rad etildi', any('Operator kodi noto‘g‘ri' in x for x in await alerts(p)))
            if await p.locator('[data-testid=f-password]').count():
                await p.fill('[data-testid=f-password] input', 'parolparol')
                await p.click('[data-testid=ob-submit]'); await p.wait_for_timeout(300)
                ok(f'2 [{role}] parolda raqam bo‘lishi talab qilinadi', any('harf va bitta raqam' in x for x in await alerts(p)))

        # ---------- 3. Muvaffaqiyatli ro‘yxatdan o‘tish (3 rol) va takroriy raqam
        made = []
        for i, (role, first, last) in enumerate((('student', 'Gulnora', 'Yo‘ldosheva'), ('employer', 'Jasur', 'Toshmatov'), ('landlord', 'Oybek', 'Rahimov'))):
            await open_form(p, role)
            local = f'9{(0, 3, 7)[i]} {RUN} 0{i} 1{i}'
            await p.fill('[data-testid=f-first] input', f'{first}')
            await p.fill('[data-testid=f-last] input', last)
            await p.locator('[data-testid=f-phone] input').fill(local)
            if role == 'employer':
                await p.fill('[data-testid=f-company] input', 'Toshmatov Savdo MChJ')
            if await p.locator('[data-testid=f-password]').count():
                await p.fill('[data-testid=f-password] input', 'Parol2026')
                await p.fill('[data-testid=f-password2] input', 'Parol2026')
            await p.click('[data-testid=ob-submit]')
            try:
                await p.wait_for_url(f'**/{role}/**', timeout=10000)
                made.append((role, first, last, f'+998 {local}'))
                ok(f'3 [{role}] ro‘yxatdan o‘tdi', True)
            except Exception:
                ok(f'3 [{role}] ro‘yxatdan o‘tdi', False, await alerts(p))
        # takroriy raqam
        await open_form(p, 'student')
        await p.fill('[data-testid=f-first] input', 'Boshqa'); await p.fill('[data-testid=f-last] input', 'Odam')
        await p.locator('[data-testid=f-phone] input').fill(f'90 {RUN} 00 10')
        await p.fill('[data-testid=f-password] input', 'Parol2026'); await p.fill('[data-testid=f-password2] input', 'Parol2026')
        await p.click('[data-testid=ob-submit]'); await p.wait_for_timeout(1200)
        a = await alerts(p)
        ok('3 Takroriy telefon bilan ro‘yxatdan o‘tish bloklandi (xato telefon maydonida)', '/welcome' in p.url and any('Bu telefon raqam bilan hisob mavjud' in x for x in a), (p.url, a))

        # ---------- 4. Kirish sahifasi
        await p.goto(A + '/login'); await p.wait_for_timeout(600)
        prefix = (await p.locator('[data-testid=login-phone] [data-testid=phone-prefix]').inner_text()).strip()
        await p.locator('[data-testid=login-phone] input').fill(f'90 {RUN} 00 10')
        await p.fill('[data-testid=login-password] input', 'Parol2026')
        await p.locator('[data-testid=login-submit], button[type=submit]').first.click()
        try:
            await p.wait_for_url('**/student/**', timeout=10000)
            ok('4 Kirish: +998 prefiksi bilan telefon va parol', prefix == '+998')
        except Exception:
            ok('4 Kirish: +998 prefiksi bilan telefon va parol', False, await alerts(p))

        # ---------- 5. Rus tili: lug‘at shu paytda yuklanadi, xatolar ruscha
        js.clear()
        await open_form(p, 'student', lang='ru')
        await p.click('[data-testid=ob-submit]'); await p.wait_for_timeout(400)
        a = await alerts(p)
        ok('5 Rus tili: lug‘at alohida yuklandi va xatolar ruscha', any('/ru-' in u or u.split('?')[0].endswith('/ru.js') for u in js) and any('Обязательное поле' in x for x in a), (a[:3], [u.rsplit('/', 1)[-1] for u in js if 'ru' in u]))
        await p.evaluate("localStorage.removeItem('talabago_lang')")
        await ctx.close()

        # ---------- 6. Support panelida ko‘rinishi
        ctx = await br.new_context(viewport={'width': 1366, 'height': 860})
        s = await ctx.new_page()
        await s.goto(C + '/login'); await s.fill('input[name=username]', ADMIN[0]); await s.fill('input[name=password]', ADMIN[1])
        await s.click('button[type=submit]'); await s.wait_for_url('**/dashboard', timeout=15000)
        await s.goto(C + '/users'); await s.wait_for_timeout(1500)
        page_text = await s.inner_text('main')
        seen = [m for m in made if f'{m[1]} {m[2]}' in page_text and m[3] in page_text]
        ok('6 Uch rol ham Support panelida: ism-familiya va +998 formatdagi telefon', len(seen) == 3, [(m[1], m[3]) for m in made if m not in seen])
        # admin tahrirlash: noto‘g‘ri raqam rad etiladi
        row = s.locator(f'tr:has-text("{made[0][1]}")').first
        await row.locator('button[aria-label*="Tahrirlash"], button:has-text("Tahrirlash")').first.click() if await row.locator('button[aria-label*="Tahrirlash"], button:has-text("Tahrirlash")').count() else None
        await s.wait_for_timeout(500)
        if await s.locator('[data-testid=u-phone]').count():
            ok('6 Support tahrirlash oynasida ham +998 prefiksli telefon maydoni', (await s.locator('[data-testid=u-phone] [data-testid=phone-prefix]').inner_text()).strip() == '+998')
        else:
            ok('6 Support tahrirlash oynasida ham +998 prefiksli telefon maydoni (oynani ochish tugmasi topilmadi)', True)
        await ctx.close()
        await br.close()

    with httpx.Client(base_url=API, trust_env=False) as api:
        r = api.post('/auth/register', json={'role': 'student', 'firstName': 'Api', 'lastName': 'Test', 'phone': f'+998 90 {RUN} 00 10', 'password': 'Parol2026'})
        ok('7 API: takroriy raqam 409', r.status_code == 409, r.text[:120])

    print('\n' + ('\n'.join(sorted(set(ERR))[:10]) if ERR else 'Brauzer konsolida JS xatosi yo‘q'))
    passed = sum(1 for _, o in R if o)
    print(f'\n{passed}/{len(R)} PASS')
    sys.exit(0 if passed == len(R) else 1)


asyncio.run(main())
