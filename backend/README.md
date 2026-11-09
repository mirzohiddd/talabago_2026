# TalabaGo API (FastAPI)

Python 3.11+ · FastAPI · ma’lumotlar **faqat JSON fayllarda** (SQLite/MongoDB/MySQL ishlatilmaydi).

## Tuzilma

```
backend/
├── app/
│   ├── main.py          # ilova, CORS, xavfsizlik sarlavhalari, /media, Telegram webhook, birinchi ishga tushish
│   ├── config.py        # sozlamalar faqat .env / muhit o‘zgaruvchilaridan
│   ├── storage.py       # JSON ombor: fayl qulfi, atomik yozish, zaxira, buzilishdan tiklash
│   ├── security.py      # scrypt parol xeshi, JWT
│   ├── deps.py          # joriy foydalanuvchi / administrator, rollar, CSRF
│   ├── ratelimit.py     # so‘rovlar cheklovi va login bloklash
│   ├── telegram.py      # initData tekshiruvi, Bot API (bildirishnoma, /start)
│   ├── uploads.py       # xavfsiz fayl yuklash
│   ├── schemas.py       # kiruvchi ma’lumot validatsiyasi (pydantic)
│   ├── routers/         # auth, users, listings (ish/uy/ariza/so‘rov), content (kurs/support/reklama), admin (Support paneli)
│   ├── cli.py           # boshqaruv buyruqlari
│   ├── bot.py           # Telegram bot (polling)
│   └── seed/            # Rus/Ingliz kurslarining boshlang‘ich darslari (bir marta yaratiladi)
├── tests/               # pytest
├── requirements.txt · requirements-dev.txt · .env.example
└── data/                # ← ish vaqtidagi ma’lumotlar (git’ga kirmaydi)
    ├── db/*.json        #   users, jobs, houses, applications, requests, courses, progress, tickets, complaints, notifications, ads, saved, settings, admins, meta
    ├── media/           #   yuklangan rasm, CV, skrinshot, video
    └── backups/         #   avtomatik zaxira nusxalar
```

## .env

| O‘zgaruvchi | Vazifasi |
|---|---|
| `BOT_TOKEN` | @BotFather tokeni. Telegram initData tekshiruvi, bot va bildirishnomalar uchun |
| `ADMIN_ID` | Yangi Support murojaati / shikoyat / tekshiruvdagi e’lon haqida xabar oladigan chat ID (vergul bilan bir nechta) |
| `JWT_SECRET_KEY` | **Majburiy**, ≥ 32 belgi (`python -m app.cli secret`). Bo‘lmasa server ishga tushmaydi |
| `CORS_ORIGINS` | Ruxsat etilgan frontend manzillari (vergul bilan) |
| `FRONTEND_URL` | Mini App manzili — bot tugmasi uchun **https** bo‘lishi kerak |
| `SUPPORT_URL` | TalabaGo Support paneli manzili (admin xabaridagi havola) |
| `COOKIE_SECURE` | Production’da `true` (https), lokal http da `false` |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH` | Birinchi administrator (adminlar ro‘yxati bo‘sh bo‘lsa yaratiladi). Ochiq parol hech qayerga yozilmaydi |
| `DATA_DIR` | JSON va media papkasi (production’da doimiy disk) |
| `BOT_WEBHOOK_SECRET` | Webhook ishlatilsa — tasodifiy satr |

Administratorlar: `python -m app.cli create-admin --username <login>` (parol so‘raladi), parolni tiklash: `set-admin-password`.

## Xavfsizlik

- **Parollar**: scrypt (N=2¹⁵, tasodifiy salt). Foydalanuvchi ham, administrator ham. API hech qachon xeshni qaytarmaydi.
- **JWT**: foydalanuvchi — `Authorization: Bearer` (30 kun); administrator — **HttpOnly** cookie (8 soat, JS o‘qiy olmaydi), tur (`typ`) ajratilgan: foydalanuvchi tokeni admin endpointlarida yaroqsiz. Admin parolini o‘zgartirish barcha eski sessiyalarni bekor qiladi.
- **CSRF**: cookie bilan kelgan o‘zgartiruvchi admin so‘rovlarida `X-Requested-With: TalabaGo` majburiy + SameSite cookie.
- **Rollar**: har bir endpoint serverda tekshiradi (talaba / ish beruvchi / uy egasi / administrator); boshqa foydalanuvchining e’loni, arizasi, murojaati — 404/403.
- **Telegram initData**: HMAC-SHA256 (`WebAppData` kaliti) va `auth_date` muddati (24 soat) serverda tekshiriladi. Frontend’dagi Telegram ma’lumoti faqat formani to‘ldirish uchun.
- **Rate limiting**: ro‘yxatdan o‘tish, kirish, fayl yuklash, ariza, murojaat va boshqalar; 5 marta noto‘g‘ri parol → 15 daqiqa bloklash (429 + Retry-After).
- **Fayl yuklash**: tur fayl ichidagi baytlar bo‘yicha aniqlanadi (kengaytmaga ishonilmaydi), hajm cheklangan, rasmlar Pillow bilan WEBP’ga qayta kodlanadi (EXIF/GPS o‘chadi), nomlar tasodifiy, `/media` javoblarida `nosniff` va qat’iy CSP. E’lon/reklama o‘chirilsa fayllari ham o‘chadi.
- **Validatsiya**: barcha kiruvchi ma’lumot pydantic sxemalari orqali (uzunlik, enum, telefon, sana, faqat `/media/` fayl havolalari, `http(s)` reklama havolasi).
- Sozlamalar: texnik ishlar rejimi (foydalanuvchi API → 503), ro‘yxatdan o‘tishni yopish, moderatsiyani o‘chirish, reklamalarni to‘xtatish — barchasi serverda qo‘llanadi.

## JSON saqlash va persistent storage

- Yozish **atomik**: vaqtinchalik fayl → `fsync` → `os.replace`; yarim yozilgan fayl qolmaydi. Xato bo‘lsa tranzaksiya hech narsa yozmaydi.
- **Qulf**: jarayon ichida `RLock`, jarayonlar orasida `fcntl.flock` — bir nechta uvicorn worker bitta diskda xavfsiz ishlaydi (faqat bitta server/konteyner uchun; bir nechta serverda umumiy tarmoq diskida flock’ga ishonmang).
- **Zaxira**: har bir kolleksiya o‘zgarishidan oldin `data/backups/<nom>/` ga (5 daqiqada ko‘pi bilan 1 marta, oxirgi 30 ta). To‘liq nusxa: `python -m app.cli backup`.
- **Buzilish**: JSON o‘qilmasa fayl `<nom>.corrupt-<vaqt>.json` ga ko‘chiriladi va eng so‘nggi butun zaxiradan avtomatik tiklanadi.

**Production talabi:** `DATA_DIR` (JSON + `media/` + `backups/`) **doimiy diskda** bo‘lishi shart — konteyner yoki serverless muhitning vaqtinchalik diskida server qayta ishga tushganda barcha ma’lumot va rasmlar yo‘qoladi:

- VPS: `/var/lib/talabago` kabi papka, `DATA_DIR=/var/lib/talabago`, kunlik `python -m app.cli backup` + serverdan tashqariga nusxa (rsync/S3).
- Docker: `-v talabago-data:/app/data` (named volume yoki host papka).
- Render/Railway/Fly.io: Persistent Disk / Volume’ni `DATA_DIR` ga ulang (bepul “ephemeral” diskda ishlatmang).
- Bitta backend nusxasi ishlatilsin (JSON ombor gorizontal masshtablashga mo‘ljallanmagan).

## Telegram

1. @BotFather → token → `BOT_TOKEN`. Mini App: BotFather’da `/newapp` yoki menyu tugmasi — `FRONTEND_URL` (https).
2. Bot buyruqlari va menyu tugmasi: `python -m app.cli setup-bot`.
3. `/start` → salomlashish + **🚀 TalabaGo’ni ochish** (InlineKeyboardMarkup + WebAppInfo); chat pastida doimiy **🚀 Ilovani ochish** (MenuButtonWebApp). Diagnostika: `python -m app.cli bot-check`.
   Ishga tushirish:
   - polling: `python -m app.bot` (alohida jarayon), yoki
   - webhook: `BOT_WEBHOOK_SECRET` ni to‘ldiring, `API_PUBLIC_URL=https://api.domen.uz python -m app.cli set-webhook`.
     Manzil `/api/v1/telegram/webhook`; maxfiy kalit faqat `X-Telegram-Bot-Api-Secret-Token` sarlavhasida tekshiriladi (URL va access log’da ko‘rinmaydi).
4. `ADMIN_ID` — yangi Support murojaati (foydalanuvchi, rol, telefon, Telegram, matn, skrinshot belgisi), yangi xabar, shikoyat va tekshiruvdagi e’lon haqida xabar oladi.
   Foydalanuvchilarga (Telegram orqali ro‘yxatdan o‘tgan bo‘lsa): Support javobi, ariza/so‘rov statusi, e’lon tasdiqlandi/rad etildi.
   Xabarlar fon oqimida yuboriladi — Telegram sekin javob bersa ham API kechikmaydi.
   Foydalanuvchi Sozlamalarda “Telegram orqali xabar” (`notifyTelegram`) va “Ilova bildirishnomalari” (`notifyApp`) ni o‘chirsa, server bularni qo‘llaydi.
   Telefon bilan ro‘yxatdan o‘tgan hisob Mini App ichida ochilsa, Telegram’ga avtomatik bog‘lanadi.

## Reklama

- Rasm (JPG/PNG/WebP) yoki video (MP4/WebM), boshlanish va tugash vaqti (UTC saqlanadi, panelda Toshkent vaqti), aktiv/noaktiv, tartib, sahifa joylashuvi.
- Holat server vaqti bo‘yicha: `live` · `scheduled` · `inactive` · `expired`. Mini App faqat `live` reklamani ko‘rsatadi.
- Statistika: ko‘rishlar (≥1 s ekranda, bir IP’dan 10 daqiqada 1 marta) va bosishlar; faqat `live` holatdagi reklama uchun hisoblanadi. CTR — Support panelida.
- Ish va uy e’lonlari bepul — pullik joylashtirish yo‘q.

## Production (qisqacha)

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
```
Nginx: `https://api.domen.uz` → 127.0.0.1:8000 (`client_max_body_size 64m`), frontendlar `npm run build` → `dist/` statik (Mini App `https://app...`, Support `https://support...`). `COOKIE_SECURE=true`, `CORS_ORIGINS` — aniq domenlar. Support panelini qo‘shimcha IP allowlist / Basic Auth ortida joylash tavsiya etiladi.
Rate limiter xotirada ishlaydi: reverse proxy darajasida ham `limit_req` qo‘ying va `--proxy-headers` bilan haqiqiy IP’ni uzating.

## Ma’lum cheklovlar

- JSON ombor kichik va o‘rta hajm uchun (o‘n minglab yozuvlar). Har bir so‘rov kolleksiyani to‘liq o‘qiydi; katta o‘sishda ma’lumotlar bazasiga o‘tish kerak bo‘ladi.
- Real vaqt: Mini App va Support chat/bildirishnomalarni 10–45 soniyada so‘rab yangilaydi (WebSocket yo‘q).
- Video yuklashda davomiylik va o‘lcham brauzer bergan qiymatdan olinadi (serverda ffprobe yo‘q).
- Yuklangan CV/rasm havolalari tasodifiy va taxmin qilib bo‘lmaydi, lekin havolani bilgan har kim ochishi mumkin (alohida yopiq saqlash yo‘q).
- Kurs testlarining to‘g‘ri javoblari talabaga darhol tekshirish uchun yuboriladi; dars yakunlanishi esa serverda javoblar bo‘yicha qayta hisoblanadi.
- Parolni unutgan foydalanuvchi uchun SMS/email tiklash yo‘q — Support orqali administrator yordam beradi (yoki Telegram orqali kirish).
- Email bildirishnomalar (“Kunlik hisobot”) — sozlama saqlanadi, lekin email yuborish ulanmagan.
- Bloklangan foydalanuvchining e’lonlari ommaviy ro‘yxatlardan avtomatik yashiriladi (blok olib tashlansa — qaytadi).
