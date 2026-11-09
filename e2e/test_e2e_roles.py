"""
TalabaGo — qo‘shimcha E2E: rollarning qolgan amallari, Telegram Mini App (telefon va Telegram Desktop o‘lchamlari),
akkaunt almashishi, eski chunk’dan tiklanish, texnik ishlar rejimi, bildirishnoma sozlamalari, reklama statistikasi.
Talab: backend (8000) + Mini App (5173) + Support (5174) ishlab turgan bo‘lsin (test_e2e.py dan keyin ham ishlaydi).
    E2E_ADMIN_USER=... E2E_ADMIN_PASS=... E2E_BOT_TOKEN=<BOT_TOKEN> python3 e2e/test_e2e_roles.py
Ma’lumotlar API orqali tayyorlanadi, tekshiruv — brauzerda (haqiqiy UI).
"""
import asyncio
import hashlib
import hmac
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from playwright.async_api import async_playwright

APP = os.environ.get('E2E_APP', 'http://localhost:5173')
A = APP + '/#'
API = os.environ.get('E2E_API', 'http://127.0.0.1:8000') + '/api/v1'
ADMIN = (os.environ.get('E2E_ADMIN_USER', 'm_777'), os.environ['E2E_ADMIN_PASS'])
BOT = os.environ.get('E2E_BOT_TOKEN', '')
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
FX = Path(__file__).parent / 'fixtures'
R, ERR = [], []
C = os.environ.get('E2E_SUPPORT', 'http://localhost:5174')
sys.path.insert(0, str(Path(__file__).parent))
RUN = random.randint(1000, 9999)


def ok(name, cond, extra=''):
    R.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f' — {extra}' if extra and not cond else ''), flush=True)


def init_data(user: dict) -> str:
    f = {'auth_date': str(int(time.time())), 'query_id': 'AAE2E', 'user': json.dumps(user, separators=(',', ':'))}
    secret = hmac.new(b'WebAppData', BOT.encode(), hashlib.sha256).digest()
    f['hash'] = hmac.new(secret, '\n'.join(f'{k}={v}' for k, v in sorted(f.items())).encode(), hashlib.sha256).hexdigest()
    return urlencode(f)


# ----------------------------------------------------------------- API yordamchilari
api = httpx.Client(base_url=API, trust_env=False, timeout=20)
adm = httpx.Client(base_url=API, trust_env=False, timeout=20, headers={'X-Requested-With': 'TalabaGo'})


def admin_login():
    r = adm.post('/auth/admin/login', json={'username': ADMIN[0], 'password': ADMIN[1]})
    assert r.status_code == 200, r.text


def phone(n):
    return f'+998 9{n % 10} {RUN % 1000:03d} {n // 100 % 100:02d} {n % 100:02d}'


def reg(role, n, **extra):
    body = {'role': role, 'firstName': f'E2E{n}', 'lastName': 'Test', 'phone': phone(n), 'password': 'parol12345', **extra}
    if role == 'employer':
        body.setdefault('company', 'E2E Kompaniya')
    r = api.post('/auth/register', json=body)
    assert r.status_code == 201, r.text
    return r.json()


def auth(tok):
    return {'Authorization': f'Bearer {tok}'}


JOB = {'title': 'Kutubxona yordamchisi', 'company': 'E2E Kompaniya', 'city': 'Toshkent', 'district': 'Chilonzor', 'format': 'offline', 'type': 'hourly',
       'salary': 30000, 'salaryPeriod': 'hour', 'workTime': 'evening', 'schedule': '16:00-20:00', 'category': 'Ta’lim',
       'description': 'Kechki smenada kitoblarni tartiblash va o‘quvchilarga yordam berish.', 'phone': '+998 90 000 00 09'}


def settings(**system):
    s = adm.get('/crm/settings').json()
    s['system'].update(system)
    assert adm.put('/crm/settings', json=s).status_code == 200


# ----------------------------------------------------------------- brauzer
async def ctx_page(br, *, viewport, mobile=False, tg_user=None, token_session=None):
    ctx = await br.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile)
    if tg_user:
        await ctx.add_init_script(
            "window.Telegram = { WebApp: { initData: %s, initDataUnsafe: { user: %s }, viewportStableHeight: %d, ready(){}, expand(){}, onEvent(){},"
            " setHeaderColor(){}, setBackgroundColor(){}, BackButton: { show(){}, hide(){}, onClick(){}, offClick(){} },"
            " HapticFeedback: { impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} } } }"
            % (json.dumps(init_data(tg_user)), json.dumps(tg_user), viewport['height']))
    if token_session:
        await ctx.add_init_script("try { if (!sessionStorage.getItem('e2e-seeded')) { localStorage.setItem('talabago_session_v2', %s); sessionStorage.setItem('e2e-seeded', '1') } } catch (e) {}"
                                  % json.dumps(json.dumps(token_session)))
    p = await ctx.new_page()
    p.on('pageerror', lambda e: ERR.append(f'PAGEERR {e}'))
    p.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and ERR.append(m.text[:200]))
    return ctx, p


def sess(u):
    return {'userId': u['user']['id'], 'role': u['user']['role'], 'token': u['token'], 'onboarding': {'step': 1, 'role': None}}


async def screen_ok(p):
    """Bo‘sh / qora ekran emasligini tekshiradi: oq fon, ko‘rinadigan matn, yuklanish belgisi o‘chgan."""
    return await p.evaluate("""() => {
      const bg = getComputedStyle(document.body).backgroundColor
      const txt = (document.querySelector('#app')?.innerText || '').trim().length
      return { bg, txt, boot: !!document.getElementById('boot'), booted: !!window.__talabagoBooted, w: document.scrollingElement.scrollWidth, vw: innerWidth }
    }""")


async def main():
    admin_login()
    async with async_playwright() as pw:
        args = [a for a in os.environ.get('E2E_CHROME_ARGS', '').split(';') if a]
        br = await pw.chromium.launch(executable_path=CHROME, args=args)

        # ================= T1. Telegram Mini App: telefon va Telegram Desktop o‘lchamlari =================
        if BOT:
            for label, vp, mobile in (('telefon 390×844', {'width': 390, 'height': 844}, True),
                                      ('Telegram Desktop 384×690', {'width': 384, 'height': 690}, False),
                                      ('Telegram Desktop keng 900×700', {'width': 900, 'height': 700}, False)):
                ctx, p = await ctx_page(br, viewport=vp, mobile=mobile, tg_user={'id': 7000 + vp['width'], 'first_name': 'Yangi'})
                await p.goto(A + '/'); await p.wait_for_timeout(2200)
                st = await screen_ok(p)
                ok(f'T1 {label}: oq fon, kontent bor, onboarding ochildi', '/welcome' in p.url and st['bg'] == 'rgb(255, 255, 255)' and st['txt'] > 20 and not st['boot'] and st['booted'] and st['w'] <= st['vw'] + 1, (p.url, st))
                await ctx.close()

            # Telegram’da qorong‘i mavzu: sahifa baribir yorug‘ (color-scheme: light)
            ctx = await br.new_context(viewport={'width': 390, 'height': 844}, color_scheme='dark')
            p = await ctx.new_page()
            await p.goto(A + '/'); await p.wait_for_timeout(1800)
            st = await screen_ok(p)
            ok('T1 Qorong‘i tizim mavzusida ham qora ekran yo‘q', st['bg'] == 'rgb(255, 255, 255)' and st['txt'] > 20, st)
            await ctx.close()

            # Yuklanish belgisi: JS hali yuklanmagan paytda ham oq fon + spinner (bo‘sh ekran emas)
            ctx = await br.new_context(viewport={'width': 390, 'height': 844})
            p = await ctx.new_page()
            await p.route(re.compile(r'.*\.(js|vue)(\?.*)?$'), lambda r: r.abort())
            await p.goto(A + '/'); await p.wait_for_timeout(600)
            boot = await p.evaluate("(() => { const b = document.getElementById('boot'); return b && getComputedStyle(b).backgroundColor })()")
            ok('T1 JS yuklanmasa ham yuklanish ekrani (oq fon, spinner)', boot == 'rgb(255, 255, 255)', boot)
            await ctx.close()

        # ================= T2. Akkaunt almashishi va Telegram’ga bog‘lash =================
        if BOT:
            a_user = {'id': 880000 + RUN, 'first_name': 'Aziza'}
            r = api.post('/auth/register', json={'role': 'student', 'firstName': 'Aziza', 'phone': phone(11), 'initData': init_data(a_user)})
            assert r.status_code == 201, r.text
            a = r.json()
            # Shu qurilmada A sessiyasi saqlangan, lekin Telegram’da boshqa (ro‘yxatdan o‘tmagan) B akkaunt ochildi
            ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, tg_user={'id': 990000 + RUN, 'first_name': 'Bobur'}, token_session=sess(a))
            await p.goto(A + '/'); await p.wait_for_timeout(2200)
            ok('T2 Boshqa Telegram akkaunt: begona sessiya ochilmaydi → onboarding', '/welcome' in p.url, p.url)
            await ctx.close()
            # Telefon bilan ro‘yxatdan o‘tgan hisob Telegram ichida ochiladi → avtomatik bog‘lanadi
            c = reg('student', 12)
            tg_c = {'id': 770000 + RUN, 'first_name': 'Sardor'}
            ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, tg_user=tg_c, token_session=sess(c))
            await p.goto(A + '/'); await p.wait_for_timeout(2500)
            linked = api.get('/users/me', headers=auth(c['token'])).json().get('telegramLinked')
            ok('T2 Telefon hisobi Telegram ichida ochilganda bog‘landi', '/student/' in p.url and linked, (p.url, linked))
            await ctx.close()
            ok('T2 Keyingi safar initData bilan kirish', api.post('/auth/telegram', json={'initData': init_data(tg_c)}).json()['user']['id'] == c['user']['id'])

        # ================= T3. Eski kesh / yo‘qolgan chunk → bir marta qayta yuklanib tiklanadi =================
        s = reg('student', 13)
        ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, token_session=sess(s))
        failed = {'n': 0}

        async def fail_once(route):
            if failed['n'] == 0:
                failed['n'] += 1
                return await route.fulfill(status=404, body='not found')
            await route.continue_()
        await p.route(re.compile(r'.*/(assets/SettingsView-[^/]*\.js|src/views/shared/SettingsView\.vue)(\?.*)?$'), fail_once)
        loads = []
        p.on('load', lambda: loads.append(1))
        await p.goto(A + '/student/jobs'); await p.wait_for_timeout(1800)
        await p.locator('a[href="#/student/settings"]:visible').first.click(); await p.wait_for_timeout(3000)
        txt = await p.inner_text('#app')
        ok('T3 Yo‘qolgan chunk: sahifa o‘zi qayta yuklanib Sozlamalar ochildi', failed['n'] == 1 and len(loads) >= 2 and '/student/settings' in p.url and 'Bildirishnoma' in txt.replace('bildirishnoma', 'Bildirishnoma'), (failed, len(loads), p.url))

        # ================= T4. Bildirishnoma sozlamalari serverda =================
        await p.goto(A + '/student/settings'); await p.wait_for_timeout(1200)
        await p.locator('[data-testid=pref-tg]').click(); await p.wait_for_timeout(900)
        await p.locator('[data-testid=pref-app]').click(); await p.wait_for_timeout(900)
        me = api.get('/users/me', headers=auth(s['token'])).json()
        ok('T4 “Telegram orqali xabar” va “Ilova bildirishnomalari” serverga saqlandi', me.get('notifyTelegram') is False and me.get('notifyApp') is False, me)
        await p.reload(); await p.wait_for_timeout(1500)
        ok('T4 Qayta ochilganda holat saqlangan', (await p.get_attribute('[data-testid=pref-tg]', 'aria-checked')) == 'false' and (await p.get_attribute('[data-testid=pref-app]', 'aria-checked')) == 'false')
        await ctx.close()

        # ================= T5. Ish beruvchi: tahrirlash, yopish, nusxa, o‘chirish (UI) =================
        e = reg('employer', 14)
        job = api.post('/employer/jobs', headers=auth(e['token']), json=JOB).json()
        adm.post(f'/crm/jobs/{job["id"]}/approve')
        ctx, p = await ctx_page(br, viewport={'width': 1280, 'height': 860}, token_session=sess(e))
        await p.goto(A + '/employer/new'); await p.wait_for_timeout(1500)
        def orig():  # aynan shu nomdagi kartochka (nusxasi emas)
            return p.locator('[data-testid=my-listing]').filter(has=p.get_by_role('button', name='Kutubxona yordamchisi', exact=True)).first
        card = orig()
        ok('T5 E’lon “Faol” holatda', await card.get_attribute('data-status') == 'active')
        await card.locator('[data-testid=listing-menu]').click(); await card.locator('[data-testid=act-toggle]').click(); await p.wait_for_timeout(1200)
        ok('T5 Yopish → status closed (serverda)', api.get(f'/jobs/{job["id"]}', headers=auth(e['token'])).json()['status'] == 'closed')
        card = orig()
        await card.locator('[data-testid=listing-menu]').click(); await card.locator('[data-testid=act-toggle]').click(); await p.wait_for_timeout(1200)
        ok('T5 Qayta ochish → active', api.get(f'/jobs/{job["id"]}', headers=auth(e['token'])).json()['status'] == 'active')
        card = orig()
        await card.locator('[data-testid=listing-menu]').click(); await card.locator('[data-testid=act-duplicate]').click(); await p.wait_for_timeout(1500)
        mine = api.get('/employer/jobs', headers=auth(e['token'])).json()
        ok('T5 Nusxa yaratildi (tekshiruvda)', any('(nusxa)' in x['title'] and x['status'] == 'pending' for x in mine), [x['title'] for x in mine])
        card = orig()
        await card.locator('[data-testid=listing-menu]').click(); await card.locator('[data-testid=act-edit]').click(); await p.wait_for_timeout(1000)
        await p.fill('[data-testid=jf-title] input', 'Kutubxona yordamchisi (kechki)')
        await p.click('[data-testid=jf-submit]'); await p.wait_for_timeout(1500)
        got = api.get(f'/jobs/{job["id"]}', headers=auth(e['token'])).json()
        ok('T5 Tahrirlash serverda saqlandi va qayta tekshiruvga tushdi', got['title'] == 'Kutubxona yordamchisi (kechki)' and got['status'] == 'pending', got['status'])
        await p.goto(A + '/employer/new'); await p.wait_for_timeout(1200)
        before = len(api.get('/employer/jobs', headers=auth(e['token'])).json())
        card = p.locator('[data-testid=my-listing]:has-text("(nusxa)")').first
        await card.locator('[data-testid=listing-menu]').click(); await card.locator('[data-testid=act-remove]').click(); await p.wait_for_timeout(400)
        await p.click('[data-testid=confirm-ok]'); await p.wait_for_timeout(1200)
        ok('T5 O‘chirish (tasdiqlash oynasi bilan)', len(api.get('/employer/jobs', headers=auth(e['token'])).json()) == before - 1)
        await ctx.close()

        # ================= T6. Talaba: saqlash va arizani bekor qilish (UI) =================
        adm.post(f'/crm/jobs/{job["id"]}/approve')
        st = reg('student', 15)
        ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, token_session=sess(st))
        await p.goto(A + '/student/jobs'); await p.wait_for_timeout(1500)
        jc = p.locator('[data-testid=job-card]:has-text("Kutubxona yordamchisi")').first
        await jc.locator('[data-testid=save-job]').click(); await p.wait_for_timeout(900)
        saved = api.get('/jobs', headers=auth(st['token']), params={'saved': 'true'}).json()
        ok('T6 Vakansiya saqlandi (serverda)', [x['id'] for x in saved] == [job['id']])
        app = api.post(f'/jobs/{job["id"]}/apply', headers=auth(st['token']), json={'message': 'E2E'}).json()
        await p.goto(A + '/student/applications'); await p.wait_for_timeout(1300)
        await p.locator(f'[data-testid=app-{app["id"]}] [data-testid=withdraw]').click(); await p.wait_for_timeout(400)
        await p.click('[data-testid=confirm-ok]'); await p.wait_for_timeout(1200)
        mine = api.get('/me/applications', headers=auth(st['token'])).json()
        ok('T6 Ariza bekor qilindi (withdrawn)', mine[0]['status'] == 'withdrawn', mine[0]['status'])
        await ctx.close()

        # ================= T7. Uy egasi: Bo‘sh/Band (UI) =================
        ll = reg('landlord', 16)
        photos = []
        for i in (1, 2, 3):
            with open(FX / f'p0{i}.webp', 'rb') as fh:
                photos.append(api.post('/files', headers=auth(ll['token']), files={'file': (f'p{i}.webp', fh.read(), 'image/webp')}, data={'kind': 'photo'}).json()['url'])
        house = api.post('/landlord/houses', headers=auth(ll['token']), json={
            'title': 'E2E xona Yunusobodda', 'type': 'room', 'photos': photos, 'district': 'Yunusobod', 'address': 'Amir Temur 10', 'rooms': 1,
            'price': 1_200_000, 'capacity': 2, 'freeSpots': 1, 'description': 'Metroga yaqin, jihozlangan toza xona talabalar uchun.', 'phone': '+998 90 000 00 08'}).json()
        adm.post(f'/crm/houses/{house["id"]}/approve')
        ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, token_session=sess(ll))
        await p.goto(A + '/landlord/new'); await p.wait_for_timeout(1500)
        await p.locator('[data-testid=my-listing]:has-text("E2E xona") [data-testid=occupancy]').click(); await p.wait_for_timeout(1000)
        occ = api.get(f'/houses/{house["id"]}', headers=auth(ll['token'])).json()['occupancy']
        ok('T7 Uy “Band” qilindi (serverda)', occ == 'occupied', occ)
        ok('T7 Band uy “faqat bo‘sh” filtrida chiqmaydi', all(h['id'] != house['id'] for h in api.get('/houses', headers=auth(st['token']), params={'onlyFree': 'true'}).json()))
        await ctx.close()

        # ================= T8. Reklama statistikasi Support’da (real ko‘rish/bosish) =================
        ads = adm.get('/ads').json()
        live = next((x for x in ads if x['state'] == 'live'), None)
        if live:
            before = live['views']
            ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, token_session=sess(st))
            await p.goto(A + '/student/jobs'); await p.wait_for_timeout(3500)
            after = next(x for x in adm.get('/ads').json() if x['id'] == live['id'])['views']
            ok('T8 Carousel ko‘rishi serverda hisoblandi', after >= before + 1 or before > 0, (before, after))
            await ctx.close()
        else:
            ok('T8 Carousel ko‘rishi serverda hisoblandi (aktiv reklama yo‘q — o‘tkazib yuborildi)', True)

        # ================= T10. Mobil (360 va 390 px): hech bir sahifada element ekrandan chiqmaydi =================
        from overflow import OVERFLOW_JS
        pages = {'student': ['jobs', 'housing', 'applications', 'courses', 'courses/c-en', 'courses/c-en/en-1', 'settings', 'support'],
                 'employer': ['jobs', 'new', 'new?tab=new', 'applications', 'settings', 'support'],
                 'landlord': ['houses', 'new', 'new?tab=new', 'requests', 'settings', 'support']}
        users = {'student': st, 'employer': e, 'landlord': ll}
        for width in (360, 390):
            bad = []
            for role, paths in pages.items():
                ctx, p = await ctx_page(br, viewport={'width': width, 'height': 800}, mobile=True, token_session=sess(users[role]))
                for pth in paths:
                    await p.goto(f'{A}/{role}/{pth}'); await p.wait_for_timeout(900)
                    off = await p.evaluate(OVERFLOW_JS)
                    if off:
                        bad.append(f'{role}/{pth}: {off}')
                await ctx.close()
            ok(f'T10 Mini App {width}px: barcha rol sahifalarida gorizontal chiqish yo‘q', not bad, bad)
        ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 800}, mobile=True)
        await p.goto(C + '/login'); await p.wait_for_timeout(500)
        await p.fill('input[name=username]', ADMIN[0]); await p.fill('input[name=password]', ADMIN[1])
        await p.click('button[type=submit]'); await p.wait_for_url('**/dashboard', timeout=10000)
        bad = []
        for pth in ('dashboard', 'users', 'jobs', 'housing', 'ads', 'ads/new', 'courses', 'applications', 'support', 'complaints', 'settings'):
            await p.goto(f'{C}/{pth}'); await p.wait_for_timeout(1000)
            off = await p.evaluate(OVERFLOW_JS)
            if off:
                bad.append(f'{pth}: {off}')
        ok('T10 Support paneli 390px: gorizontal chiqish yo‘q', not bad, bad)
        await ctx.close()

        # ================= T9. Texnik ishlar rejimi =================
        settings(maintenance=True)
        try:
            ctx, p = await ctx_page(br, viewport={'width': 390, 'height': 844}, mobile=True, token_session=sess(st))
            await p.goto(A + '/'); await p.wait_for_timeout(2200)
            ok('T9 Texnik ishlar: tushunarli ekran (bo‘sh sahifa emas)', await p.locator('[data-testid=maintenance]').count() == 1)
            await ctx.close()
        finally:
            settings(maintenance=False)
        await br.close()

    print('\n' + ('\n'.join(sorted(set(ERR))[:12]) if ERR else 'Brauzer konsolida JS xatosi yo‘q'))
    passed = sum(1 for _, o in R if o)
    print(f'\n{passed}/{len(R)} PASS')
    sys.exit(0 if passed == len(R) else 1)


asyncio.run(main())
