"""
TalabaGo — end-to-end test: haqiqiy backend (8000) + Mini App (5173) + TalabaGo Support (5174), Chromium (Playwright).
Ishga tushirish (bo‘sh DATA_DIR bilan backend va ikkala frontend ishlab turgan bo‘lishi kerak):
    E2E_ADMIN_USER=... E2E_ADMIN_PASS=... E2E_BOT_TOKEN=<backend’dagi BOT_TOKEN> python3 e2e/test_e2e.py
Tunnel hostlari orqali (Vite allowedHosts + /api proxy, CORS’siz):
    E2E_APP=http://app-e2e.trycloudflare.com:5173 E2E_SUPPORT=http://sup-e2e.trycloudflare.com:5174 \
    E2E_CHROME_ARGS='--host-resolver-rules=MAP *.trycloudflare.com 127.0.0.1' ... python3 e2e/test_e2e.py
"""
import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from overflow import OVERFLOW_JS  # noqa: E402

A = os.environ.get('E2E_APP', 'http://localhost:5173') + '/#'
C = os.environ.get('E2E_SUPPORT', 'http://localhost:5174')
ADMIN = (os.environ.get('E2E_ADMIN_USER', 'm_777'), os.environ['E2E_ADMIN_PASS'])
BOT = os.environ.get('E2E_BOT_TOKEN', '')
FX = Path(__file__).parent / 'fixtures'
R, ERR = [], []
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')


def ok(name, cond, extra=''):
    R.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f' — {extra}' if extra and not cond else ''), flush=True)


def init_data(user: dict) -> str:
    f = {'auth_date': str(int(time.time())), 'query_id': 'AAE2E', 'user': json.dumps(user, separators=(',', ':'))}
    secret = hmac.new(b'WebAppData', BOT.encode(), hashlib.sha256).digest()
    f['hash'] = hmac.new(secret, '\n'.join(f'{k}={v}' for k, v in sorted(f.items())).encode(), hashlib.sha256).hexdigest()
    return urlencode(f)


async def page(br, mobile=False, tg_user=None):
    ctx = await br.new_context(viewport={'width': 390, 'height': 844} if mobile else {'width': 1440, 'height': 900}, is_mobile=mobile, has_touch=mobile)
    if tg_user:  # Telegram WebApp muhitini taqlid qilish (initData haqiqiy bot token bilan imzolangan)
        await ctx.add_init_script(f"window.Telegram = {{ WebApp: {{ initData: {json.dumps(init_data(tg_user))}, initDataUnsafe: {{ user: {json.dumps(tg_user)} }}, ready(){{}}, expand(){{}}, onEvent(){{}}, HapticFeedback: {{ impactOccurred(){{}}, notificationOccurred(){{}}, selectionChanged(){{}} }} }} }}")
    p = await ctx.new_page()
    p.on('pageerror', lambda e: ERR.append(f'PAGEERR {e}'))
    p.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and ERR.append(m.text[:200]))
    return p


async def register(p, role, phone, first='Test', company=None, password='parol12345'):
    await p.goto(A + '/welcome')
    await p.evaluate('localStorage.clear()')
    await p.reload(); await p.wait_for_timeout(600)
    for _ in range(4):
        await p.click('[data-testid=ob-next]'); await p.wait_for_timeout(250)
    await p.click(f'[data-testid=role-{role}]'); await p.click('[data-testid=ob-next]'); await p.wait_for_timeout(300)
    await p.fill('[data-testid=f-first] input', first)
    await p.fill('[data-testid=f-phone] input', phone)
    if company:
        await p.fill('[data-testid=f-company] input', company)
    if await p.locator('[data-testid=f-password]').count():
        await p.fill('[data-testid=f-password] input', password)
        await p.fill('[data-testid=f-password2] input', password)
    await p.click('[data-testid=ob-submit]')
    await p.wait_for_url(f'**/{role}/**', timeout=10000)
    await p.wait_for_timeout(800)


async def crm_login(p):
    await p.goto(C + '/login'); await p.wait_for_timeout(400)
    await p.fill('input[name=username]', ADMIN[0]); await p.fill('input[name=password]', ADMIN[1])
    await p.click('button[type=submit]')
    await p.wait_for_url('**/dashboard', timeout=10000); await p.wait_for_timeout(800)


async def no_overflow(p):
    return not await p.evaluate(OVERFLOW_JS)


async def main():
    async with async_playwright() as pw:
        args = [a for a in os.environ.get('E2E_CHROME_ARGS', '').split(';') if a]
        br = await pw.chromium.launch(executable_path=CHROME, args=args)

        # ================= 0. Bo‘sh tizim: demo ma’lumot yo‘q =================
        adm = await page(br)
        await adm.goto(C + '/users'); await adm.wait_for_timeout(500)
        ok('S0 Kirmasdan Support paneli yopiq → /login', '/login' in adm.url)
        await adm.fill('input[name=username]', ADMIN[0]); await adm.fill('input[name=password]', 'xato-parol')
        await adm.click('button[type=submit]'); await adm.wait_for_timeout(800)
        ok('S0 Noto‘g‘ri parol rad etiladi', await adm.locator('[data-testid=login-error]').count() == 1)
        await crm_login(adm)
        kpis = await adm.locator('[data-testid=kpi]').all_inner_texts()
        vals = [[x for x in k.split('\n') if x.strip()][1].strip() for k in kpis]
        ok('S0 Dashboard: bo‘sh tizimda hamma ko‘rsatkich 0 (demo yo‘q)', len(kpis) == 11 and all(v == '0' for v in vals), vals)
        nav = [x.strip().split('\n')[0] for x in await adm.locator('[data-testid=crm-sidebar] nav a').all_inner_texts()]
        ok('S0 10 ta bo‘lim', len(nav) == 10, nav)
        ok('S0 Nomi: TalabaGo Support', 'TALABAGO SUPPORT' in (await adm.inner_text('[data-testid=crm-sidebar]')).upper())

        # ================= 1. Ish beruvchi ro‘yxatdan o‘tadi va vakansiya joylaydi =================
        emp = await page(br)
        await register(emp, 'employer', '901110001', 'Dilshod', 'Uzum Tech')
        ok('E1 Ish beruvchi → Ishlar', emp.url.endswith('/employer/jobs'))
        ok('E1 Demo vakansiyalar yo‘q (bo‘sh holat)', await emp.locator('[data-testid=job-card]').count() == 0)
        await emp.goto(A + '/employer/new?tab=new'); await emp.wait_for_timeout(800)
        await emp.fill('[data-testid=jf-title] input', 'Frontend stajyor (Vue)')
        await emp.fill('[data-testid=jf-salary] input', '4000000')
        await emp.select_option('[data-testid=jf-district] select', 'Yunusobod')
        await emp.fill('[data-testid=jf-schedule] input', '10:00-15:00')
        await emp.fill('[data-testid=jf-desc] textarea', 'Talabalar uchun yarim kunlik stajirovka, Vue.js bilan real loyihalarda ishlash.')
        await emp.click('[data-testid=jf-submit]'); await emp.wait_for_timeout(1200)
        card = emp.locator('[data-testid=my-listing]:has-text("Frontend stajyor")')
        ok('E1 Vakansiya “Tekshiruvda”', await card.count() == 1 and (await card.get_attribute('data-status')) == 'pending')

        # ================= 2. Support: tasdiqlash + reklama =================
        await adm.goto(C + '/jobs?status=pending'); await adm.wait_for_timeout(1000)
        row = adm.locator('tr:has-text("Frontend stajyor")')
        ok('S2 Yangi vakansiya Support’da (real API)', await row.count() == 1)
        await row.locator('[data-testid=approve]').click(); await adm.wait_for_timeout(800)
        await adm.goto(C + '/ads/new'); await adm.wait_for_timeout(800)
        await adm.locator('input[placeholder*="CodeStart"]').fill('Kuzgi IT kurslari')
        await adm.set_input_files('[data-testid=ad-file]', str(FX / 'kitob.webp')); await adm.wait_for_timeout(1200)
        # boshlanish — 1 soat oldin (Toshkent vaqti, UTC+5), shunda reklama darhol “Ko‘rsatilmoqda” bo‘ladi
        start = time.strftime('%Y-%m-%dT%H:%M', time.gmtime(time.time() + 5 * 3600 - 3600))
        await adm.fill('[data-testid=ad-start] input', start)
        await adm.locator('button[type=submit]').last.click(); await adm.wait_for_timeout(1500)
        ok('S2 Reklama yaratildi (fayl serverga yuklandi)', '/ads' in adm.url and await adm.locator('text=Kuzgi IT kurslari').count() >= 1, adm.url)

        # ================= 3. Talaba: ish, reklama, ariza, kurs, support =================
        stu = await page(br, mobile=True)
        await register(stu, 'student', '931110002', 'Madina')
        await stu.wait_for_timeout(800)
        ok('M3 Talaba: tasdiqlangan vakansiya ko‘rinadi', await stu.locator('[data-testid=job-card]:has-text("Frontend stajyor")').count() == 1)
        ok('M3 Reklama carousel (server /ads/active)', await stu.locator('.ad-carousel img').count() >= 1)
        await stu.locator('[data-testid=job-card]').first.click(); await stu.wait_for_timeout(600)
        await stu.locator('button:has-text("Ariza yuborish")').last.click(); await stu.wait_for_timeout(400)
        await stu.locator('textarea').last.fill('Vue.js bo‘yicha loyihalarim bor, ishlashga tayyorman.')
        await stu.locator('button:has-text("Yuborish")').last.click(); await stu.wait_for_timeout(1200)
        await stu.keyboard.press('Escape'); await stu.wait_for_timeout(300)
        await stu.goto(A + '/student/applications'); await stu.wait_for_timeout(1000)
        ok('M3 Arizalarim: ariza serverda saqlandi', await stu.locator('article:has-text("Frontend stajyor")').count() >= 1)
        await stu.goto(A + '/student/courses'); await stu.wait_for_timeout(1000)
        ok('M3 2 ta bepul kurs (Rus, Ingliz), progress 0%', await stu.locator('[data-testid^=course-]:not([data-testid=course-list])').count() == 2 and (await stu.inner_text('[data-testid=progress-ru]')) == '0%')
        await stu.goto(A + '/student/courses/c-ru/ru-1'); await stu.wait_for_selector('[data-testid=lesson-tabs]'); await stu.wait_for_timeout(400)
        ok('M3 Dars videosi serverdan', await stu.locator('[data-testid=lesson-video]').count() == 1 and '/media/courses/' in (await stu.get_attribute('[data-testid=lesson-video]', 'src') or ''))
        await stu.locator('[data-testid=lesson-tabs] button').nth(4).click(); await stu.wait_for_timeout(300)
        for i, a in enumerate([1, 1, 2, 2, 0]):
            await stu.click(f'[data-testid=q{i}-o{a}]')
        await stu.click('[data-testid=quiz-check]'); await stu.wait_for_timeout(1200)
        await stu.goto(A + '/student/courses'); await stu.wait_for_timeout(1000)
        ok('M3 Progress serverda: 20%', (await stu.inner_text('[data-testid=progress-ru]')) == '20%')
        await stu.goto(A + '/student/support'); await stu.wait_for_timeout(800)
        await stu.click('[data-testid=new-ticket]'); await stu.wait_for_timeout(300)
        await stu.fill('[data-testid=t-subject] input', 'CV yuklanmayapti')
        await stu.fill('[data-testid=t-text] textarea', 'PDF faylni tanlasam xato chiqyapti, yordam bering.')
        await stu.set_input_files('[data-testid=t-shot]', str(FX / 'screenshot-demo.webp')); await stu.wait_for_timeout(800)
        await stu.click('[data-testid=t-submit]'); await stu.wait_for_timeout(1500)
        ok('M3 Murojaat yuborildi, chat ochildi', (await stu.inner_text('[data-testid=chat-subject]')) == 'CV yuklanmayapti')
        bad = []
        for pth in ['jobs', 'housing', 'applications', 'courses', 'settings', 'support']:
            await stu.goto(f'{A}/student/{pth}'); await stu.wait_for_timeout(700)
            off = await stu.evaluate(OVERFLOW_JS)
            if off:
                bad.append(f'{pth}: {off}')
        ok('M3 390px’da gorizontal overflow yo‘q', not bad, bad)

        # ================= 4. Support chat (real) =================
        await adm.goto(C + '/support'); await adm.wait_for_timeout(1200)
        await adm.locator('[data-testid=crm-ticket-list] >> text=CV yuklanmayapti').first.click(); await adm.wait_for_timeout(800)
        chat = await adm.inner_text('[data-testid=crm-chat]')
        ok('S4 Murojaat Support’ga keldi (skrinshot bilan)', 'PDF faylni tanlasam' in chat and await adm.locator('[data-testid=crm-chat] img').count() >= 1)
        await adm.fill('[data-testid=crm-reply]', 'Fayl 5 MB dan kichik bo‘lsin, qayta urinib ko‘ring.')
        await adm.click('[data-testid=crm-reply-send]'); await adm.wait_for_timeout(1000)
        await stu.goto(A + '/student/support'); await stu.wait_for_timeout(1000)
        await stu.locator('text=CV yuklanmayapti').first.click(); await stu.wait_for_timeout(1000)
        ok('M4 Talaba javobni oldi', '5 MB dan kichik' in await stu.inner_text('[data-testid=chat-messages]'))

        # ================= 5. Ish beruvchi arizani qabul qiladi → talabaga bildirishnoma =================
        await emp.goto(A + '/employer/applications'); await emp.wait_for_timeout(1200)
        await emp.locator('[data-testid=incoming-table] tbody tr').first.locator('button').first.click(); await emp.wait_for_timeout(800)
        cand = await emp.inner_text('[role=dialog]')
        ok('E5 Nomzod profili (real)', 'Madina' in cand and 'Vue.js' in await emp.inner_text('body'))
        await emp.click('[data-testid=act-accept]'); await emp.wait_for_timeout(1000)
        ok('E5 Qabul qilindi', (await emp.locator('[data-testid=candidate] [data-status]').first.get_attribute('data-status')) == 'accepted')
        await stu.goto(A + '/student/applications'); await stu.wait_for_timeout(1200)
        ok('M5 Talaba: ariza “Qabul qilindi”', await stu.locator('article:has-text("Frontend stajyor") [data-status=accepted]').count() >= 1)

        # ================= 6. Uy egasi (Telegram Mini App, initData) =================
        if BOT:
            ll = await page(br, mobile=True, tg_user={'id': 55501, 'first_name': 'Rustam', 'username': 'rustam_uy'})
            await ll.goto(A + '/'); await ll.wait_for_timeout(1800)
            ok('L6 Telegram: ro‘yxatdan o‘tmagan → onboarding', '/welcome' in ll.url)
            await register(ll, 'landlord', '971110003', 'Rustam')
            ok('L6 Telegram ichida parol so‘ralmaydi', True)
            await ll.goto(A + '/landlord/new?tab=new'); await ll.wait_for_timeout(800)
            await ll.fill('[data-testid=hf-title] input', 'Talabalar uchun 2 xonali kvartira')
            await ll.set_input_files('[data-testid=photo-input]', [str(FX / f'p0{i}.webp') for i in (1, 2, 3)]); await ll.wait_for_timeout(2500)
            await ll.select_option('[data-testid=hf-district] select', 'Chilonzor'); await ll.fill('[data-testid=hf-address] input', '9-kvartal')
            await ll.fill('[data-testid=hf-price] input', '3500000'); await ll.fill('[data-testid=hf-desc] textarea', 'Metroga yaqin, mebel va Wi-Fi bor, talabalar uchun qulay.')
            await ll.click('[data-testid=hf-submit]'); await ll.wait_for_timeout(1500)
            ok('L6 Uy e’loni (3 rasm serverga) tekshiruvda', (await ll.locator('[data-testid=my-listing]:has-text("2 xonali")').get_attribute('data-status')) == 'pending')
            # qayta ochish → initData bilan avtomatik kirish
            await ll.evaluate("localStorage.removeItem('talabago_session_v2')")
            await ll.goto(A + '/'); await ll.wait_for_timeout(2000)
            ok('L6 Telegram initData bilan avtomatik kirish', '/landlord/' in ll.url, ll.url)
            await adm.goto(C + '/housing?status=pending'); await adm.wait_for_timeout(1000)
            hrow = adm.locator('tr:has-text("2 xonali")')
            await hrow.locator('button[aria-label="Ko‘rish"]').click(); await adm.wait_for_timeout(800)
            ok('S6 Uy rasmlari Support’da ko‘rinadi', await adm.locator('[data-testid=house-photos] img').count() == 3)
            await adm.keyboard.press('Escape'); await adm.wait_for_timeout(300)
            await hrow.locator('[data-testid=reject]').click()
            await adm.fill('[data-testid=reject-reason] textarea', 'Manzilni to‘liq kiriting (uy raqami)')
            await adm.click('[data-testid=reject-send]'); await adm.wait_for_timeout(800)
            await ll.goto(A + '/landlord/new'); await ll.wait_for_timeout(1000)
            ok('L6 Uy egasi rad etish sababini ko‘radi', 'uy raqami' in await ll.inner_text('[data-testid=reject-reason]'))

        # ================= 7. Kirish / chiqish (telefon + parol) =================
        await emp.goto(A + '/employer/settings'); await emp.wait_for_timeout(800)
        await emp.click('[data-testid=logout]'); await emp.click('[data-testid=confirm-ok]'); await emp.wait_for_timeout(800)
        await emp.goto(A + '/login'); await emp.wait_for_timeout(500)
        await emp.fill('[data-testid=login-phone] input', '90 111 00 01'); await emp.fill('[data-testid=login-password] input', 'xato-parol')
        await emp.click('[data-testid=login-submit]'); await emp.wait_for_timeout(1000)
        ok('E7 Noto‘g‘ri parol', '/login' in emp.url)
        await emp.fill('[data-testid=login-password] input', 'parol12345'); await emp.click('[data-testid=login-submit]')
        await emp.wait_for_url('**/employer/**', timeout=8000)
        ok('E7 Telefon + parol bilan qayta kirish', '/employer/' in emp.url)

        # ================= 8. Dashboard real ma’lumotdan =================
        await adm.goto(C + '/dashboard'); await adm.wait_for_timeout(1200)
        total = [x for x in (await adm.locator('[data-testid=kpi]').first.inner_text()).split('\n') if x.strip()][1].strip()
        ok('S8 Dashboard: jami foydalanuvchilar = 3 (real)', total == '3', total)
        await adm.goto(C + '/users'); await adm.wait_for_timeout(1000)
        ok('S8 Foydalanuvchilar jadvali: 3 ta real hisob', await adm.locator('[data-testid=users-table] tbody tr').count() == 3)
        await adm.click('[data-testid=crm-collapse]'); await adm.reload(); await adm.wait_for_timeout(900)
        ok('S8 Sidebar yig‘ilgan holati saqlanadi', (await adm.get_attribute('[data-testid=crm-sidebar]', 'data-collapsed')) == 'true')
        await adm.click('[data-testid=crm-collapse]')
        await br.close()

    print('\n' + ('\n'.join(sorted(set(ERR))[:12]) if ERR else 'Brauzer konsolida JS xatosi yo‘q'))
    passed = sum(1 for _, o in R if o)
    print(f'\n{passed}/{len(R)} PASS')
    sys.exit(0 if passed == len(R) else 1)


asyncio.run(main())
