"""
TalabaGo Mini App’ni telefon ekranida (390×844 @3x) yozib olish — CDP screencast (kadr + vaqt), Telegram WebApp muhiti.
Har sahna: frames/<sahna>/NNNNN.jpg + index.json [{t, f}] + events.json (teginishlar va kesish belgilari).
"""
import asyncio, base64, hashlib, hmac, json, os, sys, time
from pathlib import Path
from urllib.parse import urlencode
from playwright.async_api import async_playwright

APP = 'http://127.0.0.1:5173/#'
OUT = Path(__file__).parent / 'frames'
BOT = '777000:VIDEO-recording'
TG_USER = {'id': 990001, 'first_name': 'Aziz', 'last_name': 'Karimov', 'username': 'aziz_talaba', 'language_code': 'uz'}


def init_data():
    f = {'auth_date': str(int(time.time())), 'query_id': 'AAVIDEO', 'user': json.dumps(TG_USER, separators=(',', ':'))}
    secret = hmac.new(b'WebAppData', BOT.encode(), hashlib.sha256).digest()
    f['hash'] = hmac.new(secret, '\n'.join(f'{k}={v}' for k, v in sorted(f.items())).encode(), hashlib.sha256).hexdigest()
    return urlencode(f)


TG_SHIM = """
window.Telegram = { WebApp: {
  initData: %s, initDataUnsafe: { user: %s }, platform: 'ios', colorScheme: 'light', viewportStableHeight: 844,
  ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, setBottomBarColor(){}, disableVerticalSwipes(){}, onEvent(){}, offEvent(){},
  openLink(u){}, openTelegramLink(u){},
  HapticFeedback: { impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} },
  BackButton: { onClick(){}, offClick(){}, show(){}, hide(){} },
} };
"""


class Recorder:
    def __init__(self, page, cdp):
        self.page, self.cdp = page, cdp
        self.scene = None

    async def start(self, name):
        self.scene = name
        self.dir = OUT / name
        self.dir.mkdir(parents=True, exist_ok=True)
        for f in self.dir.glob('*'):
            f.unlink()
        self.frames, self.events, self.t0, self.n = [], [], None, 0
        await self.cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 93, 'maxWidth': 1170, 'maxHeight': 2532, 'everyNthFrame': 1})
        await self.page.wait_for_timeout(300)
        self.t0 = time.monotonic()

    def on_frame(self, p):
        asyncio.ensure_future(self.cdp.send('Page.screencastFrameAck', {'sessionId': p['sessionId']}))
        if self.scene is None:
            return
        t = time.monotonic() - (self.t0 or time.monotonic())
        name = f'{self.n:05d}.jpg'
        (self.dir / name).write_bytes(base64.b64decode(p['data']))
        self.frames.append({'t': round(max(0.0, t), 3), 'f': name})
        self.n += 1

    def mark(self, kind, **kw):
        self.events.append({'t': round(time.monotonic() - self.t0, 3), 'kind': kind, **kw})

    async def stop(self):
        await self.page.wait_for_timeout(250)
        await self.cdp.send('Page.stopScreencast')
        self.mark('end')
        (self.dir / 'index.json').write_text(json.dumps(self.frames))
        (self.dir / 'events.json').write_text(json.dumps(self.events))
        print(self.scene, len(self.frames), 'kadr', self.events[-1]['t'], 's', flush=True)
        self.scene = None

    async def tap(self, locator, wait=450):
        await locator.scroll_into_view_if_needed()
        box = await locator.bounding_box()
        self.mark('tap', x=box['x'] + box['width'] / 2, y=box['y'] + box['height'] / 2)
        await self.page.wait_for_timeout(180)  # ripple ko‘rinib ulgursin
        await locator.tap()
        await self.page.wait_for_timeout(wait)

    async def type(self, locator, text, delay=85):
        await self.tap(locator, 150)
        await locator.press_sequentially(text, delay=delay)

    async def scroll(self, dy, ms=700, selector=None):
        await self.page.evaluate("""([dy, sel]) => { const el = sel ? document.querySelector(sel) : window; el.scrollBy({ top: dy, behavior: 'smooth' }) }""", [dy, selector])
        await self.page.wait_for_timeout(ms)


async def main():
    only = sys.argv[1:]
    async with async_playwright() as pw:
        br = await pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--hide-scrollbars'])
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True, locale='uz-UZ', timezone_id='Asia/Tashkent')
        await ctx.add_init_script(TG_SHIM % (json.dumps(init_data()), json.dumps(TG_USER)))
        await ctx.route('https://telegram.org/**', lambda r: r.fulfill(status=200, body='', content_type='application/javascript'))
        page = await ctx.new_page()
        # Toza holat: talaba hali ro‘yxatdan o‘tmagan
        await page.goto(APP + '/welcome'); await page.evaluate('localStorage.clear()')
        cdp = await ctx.new_cdp_session(page)
        R = Recorder(page, cdp)
        cdp.on('Page.screencastFrame', R.on_frame)
        P = page

        # ---------------- 1. Mini App ochiladi → talaba sifatida ro‘yxatdan o‘tish ----------------
        await P.goto('about:blank')
        await R.start('register')
        await P.goto(APP + '/')
        await P.wait_for_selector('[data-testid=lang-uz]', timeout=15000); await P.wait_for_timeout(900)
        await R.tap(P.locator('[data-testid=lang-uz]'), 500)
        R.mark('skip_from')
        for _ in range(4):
            await P.locator('[data-testid=ob-next]').tap(); await P.wait_for_timeout(260)
        await P.wait_for_selector('[data-testid=role-student]'); await P.wait_for_timeout(450)
        R.mark('skip_to')
        await R.tap(P.locator('[data-testid=role-student]'), 600)
        await R.tap(P.locator('[data-testid=ob-next]'), 900)
        await R.type(P.locator('[data-testid=f-phone] input'), '90 123 45 67')
        await P.wait_for_timeout(400)
        await R.scroll(420, 800)
        await R.tap(P.locator('[data-testid=ob-submit]'), 400)
        await P.wait_for_url('**/student/jobs', timeout=15000); await P.wait_for_timeout(2200)
        await R.stop()

        # ---------------- 2. Ishlar: filtr, vakansiya, ariza ----------------
        await R.start('jobs')
        await P.wait_for_timeout(1300)
        await R.scroll(260, 900)
        await R.tap(P.locator('button:visible:has-text("Soatlik")').first, 1100)
        await R.tap(P.locator('[data-testid=job-card]:has-text("Kafe ofitsianti")'), 1300)
        await R.scroll(380, 900, '[role=dialog] .overflow-y-auto')
        await R.tap(P.locator('[role=dialog] button:has-text("Ariza yuborish")').last, 700)
        await R.type(P.locator('[role=dialog] textarea').last, 'Kechki smenada ishlashga tayyorman!', 55)
        await P.wait_for_timeout(300)
        await R.tap(P.locator('[role=dialog] button:has-text("Yuborish")').last, 2000)
        await R.stop()
        await P.keyboard.press('Escape'); await P.wait_for_timeout(500)

        # ---------------- 3. Turar joy: e’lonlar, galereya, so‘rov ----------------
        await R.start('housing')
        await R.tap(P.locator('[data-testid=bottom-nav] a:has-text("Turar joy")'), 1500)
        await R.scroll(300, 1000)
        await R.tap(P.locator('[data-testid=house-card]').first, 1300)
        for x in (330, 660):
            await P.evaluate("x => document.querySelector('[data-testid=gallery]').scrollTo({ left: x, behavior: 'smooth' })", x); await P.wait_for_timeout(800)
        await R.tap(P.locator('[data-testid=request-btn]'), 700)
        await R.tap(P.locator('[data-testid=move-in] input'), 200)
        await P.fill('[data-testid=move-in] input', '2026-12-01'); await P.wait_for_timeout(500)
        await R.type(P.locator('[role=dialog] textarea').last, 'Ko‘rgani borsam bo‘ladimi?', 55)
        await R.tap(P.locator('[data-testid=request-submit]'), 2000)
        await R.stop()
        await P.keyboard.press('Escape'); await P.wait_for_timeout(500)

        # ---------------- 4. Kurslar: rus va ingliz tili ----------------
        await R.start('courses')
        await R.tap(P.locator('[data-testid=bottom-nav] a:has-text("Kurslar")'), 1600)
        await R.scroll(380, 1000)
        await R.scroll(-380, 700)
        await R.tap(P.locator('[data-testid=course-ru]'), 1400)
        await R.tap(P.locator('[data-testid=lesson-list] li').first, 1300)
        await P.evaluate("() => { const v = document.querySelector('[data-testid=lesson-video]'); if (v) { v.muted = true; v.play() } }")
        await P.wait_for_timeout(2600)
        await R.tap(P.locator('[data-testid=lesson-tabs] button').nth(2), 1600)
        await R.tap(P.locator('[data-testid=lesson-tabs] button').nth(4), 700)
        for i, a in enumerate([1, 1, 2, 2, 0]):
            await P.locator(f'[data-testid=q{i}-o{a}]').scroll_into_view_if_needed()
            await R.tap(P.locator(f'[data-testid=q{i}-o{a}]'), 260)
        await R.tap(P.locator('[data-testid=quiz-check]'), 1800)
        await P.goto(APP + '/student/courses'); await P.wait_for_timeout(1500)
        await R.scroll(420, 1200)
        await R.stop()

        # ---------------- 5. Arizalarim: statuslar ----------------
        R.mark = R.mark  # (holat o‘zgarishlari namuna ish beruvchi va uy egasi tomonidan API orqali beriladi — record_statuses.py)
        os.system(f'{sys.executable} {Path(__file__).parent / "statuses.py"}')
        await R.start('applications')
        await R.tap(P.locator('[data-testid=bottom-nav] a:has-text("Arizalarim")'), 1700)
        await R.tap(P.locator('[data-testid=list-jobs] article button[aria-expanded]').first, 1500)
        await R.tap(P.locator('[data-testid=app-tabs] button').nth(1), 1600)
        await R.tap(P.locator('[data-testid=list-requests] article button[aria-expanded]').first, 1500)
        await R.tap(P.locator('[data-testid=app-tabs] button').nth(0), 1400)
        await R.stop()
        await br.close()


asyncio.run(main())
