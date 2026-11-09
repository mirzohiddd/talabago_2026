# TalabaGo

Talabalar uchun ish, turar joy va bepul til kurslari platformasi. Uch qism bitta Python API orqali ishlaydi:

```
TalabaGo/
├── backend/     # Python FastAPI API — barcha ma’lumot JSON fayllarda (backend/data/)   → http://localhost:8000
├── frontend/    # Telegram Mini App / website — Talaba, Ish beruvchi, Uy egasi           → http://localhost:5173
├── frontend2/   # TalabaGo Support — faqat vakolatli administratorlar uchun panel           → http://localhost:5174
├── shared/      # ikkala frontend uchun umumiy: i18n (4 til), domen konstantalari, logo/illustratsiya manbalari
├── scripts/mac/ # macOS: setup.sh, start.sh, stop.sh
├── deploy/      # Cloudflare Tunnel konfiguratsiyasi (HTTP/2)
├── docs/        # MACOS.md — ishga tushirish va muammolarni bartaraf etish
└── e2e/         # brauzerda to‘liq oqim testi (Playwright) va test fayllari
```

Demo ma’lumot yo‘q: tizim bo‘sh holatda ishga tushadi, hamma narsa (foydalanuvchilar, e’lonlar, arizalar, reklamalar, murojaatlar, statistika) faqat backend JSON fayllaridan olinadi. Ma’lumot bo‘lmasa — `0` va bo‘sh holat (empty state) ko‘rsatiladi.
Yagona istisno — **Rus va Ingliz tili kurslarining boshlang‘ich darslari** (haqiqiy o‘quv kontenti, 2×5 dars). Ular birinchi ishga tushishda bir marta yaratiladi va Support panelidan to‘liq tahrirlanadi / yashiriladi.

## macOS: bitta buyruq bilan (Telegram Mini App + HTTPS)

```bash
cd "/Users/macbook/Desktop/TalabaGo 8"
bash scripts/mac/setup.sh     # bir marta: Python/Node/cloudflared, kutubxonalar, .env, administrator
bash scripts/mac/start.sh     # backend + Mini App + Support (production build) + Cloudflare tunnel (HTTP/2) + Telegram bot
bash scripts/mac/start.sh --dev   # xuddi shu, lekin frontendlar Vite dev server’da (hot reload, faqat dasturlash uchun)
bash scripts/mac/stop.sh
```
Batafsil (BotFather, doimiy domen, Cloudflare QUIC/DNS muammolari): [`docs/MACOS.md`](docs/MACOS.md).

## Ishga tushirish (qo‘lda)

```bash
# 1) Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # so‘ng .env ni to‘ldiring (pastga qarang)
python -m app.cli secret        # → JWT_SECRET_KEY
python -m app.cli hash-password # → ADMIN_PASSWORD_HASH (ADMIN_USERNAME bilan birga)
uvicorn app.main:app --host 0.0.0.0 --port 8000
# API hujjati: http://localhost:8000/api/docs

# 2) Mini App (alohida terminalda)
cd frontend && npm install && npm run dev      # http://localhost:5173

# 3) TalabaGo Support (alohida terminalda)
cd frontend2 && npm install && npm run dev     # http://localhost:5174
```

Frontendlar API’ga `VITE_API_URL` orqali murojaat qiladi (standart `/api/v1` — sahifa hosti orqali; Vite `/api` va `/media` ni `BACKEND_URL` ga proxy qiladi).
Shuning uchun bitta HTTPS host (Cloudflare Tunnel) yetadi, CORS sozlash shart emas. Backend alohida domenda bo‘lsa — `VITE_API_URL=https://api.../api/v1` va backend `CORS_ORIGINS`.

Telegram bot (`BOT_TOKEN` kerak): `python -m app.bot` (polling) yoki webhook — `backend/README.md`. Mini App tugmalari faqat `FRONTEND_URL` https bo‘lganda yuboriladi.

## Testlar

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q          # 44 test: API, 3 rol, xavfsizlik, JSON ombor, Telegram bot, reklama, tunnel/proxy
cd frontend && npm run build && cd ../frontend2 && npm run build                   # ikkala frontend build
# E2E (backend bo‘sh DATA_DIR bilan + ikkala frontend ishlab turganda; dev yoki `vite preview`):
E2E_ADMIN_USER=<login> E2E_ADMIN_PASS=<parol> E2E_BOT_TOKEN=<BOT_TOKEN> python3 e2e/test_e2e.py         # 34 ta asosiy oqim
E2E_ADMIN_USER=<login> E2E_ADMIN_PASS=<parol> E2E_BOT_TOKEN=<BOT_TOKEN> python3 e2e/test_e2e_roles.py   # 26 ta: Telegram telefon/Desktop, rollar, mobil 360/390px
```

## Rollar va sahifalar

| Qism | Sahifalar |
|---|---|
| Talaba | Ishlar · Turar joy · Arizalarim · Kurslar · Sozlamalar (+ Texnik yordam) |
| Ish beruvchi | Ishlar · E’lon qo‘shish · Arizalar · Sozlamalar (+ Texnik yordam) |
| Uy egasi | Uylar · E’lon qo‘shish · So‘rovlar · Sozlamalar (+ Texnik yordam) |
| TalabaGo Support | Dashboard · Foydalanuvchilar · Ish e’lonlari · Turar joylar · Reklama · Kurslar · Arizalar va so‘rovlar · Support · Shikoyatlar · Sozlamalar |

Kirish: Telegram Mini App ichida — imzolangan `initData` (server HMAC bilan tekshiradi, parol shart emas); brauzerda — telefon raqam + parol.
Ish va uy e’lonlari TalabaGo Support tasdig‘idan keyin ko‘rinadi (Sozlamalar → “E’lonlarni oldindan tekshirish” o‘chirilsa, darhol chiqadi).

Batafsil: [`backend/README.md`](backend/README.md) — API, xavfsizlik, Telegram, persistent storage, production va cheklovlar.
