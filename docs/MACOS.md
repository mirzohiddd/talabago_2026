# TalabaGo — macOS’da ishga tushirish (Telegram Mini App + Cloudflare Tunnel)

Barcha buyruqlar **Terminal** ilovasida bajariladi. Papka nomida bo‘sh joy bor, shuning uchun manzil qo‘shtirnoq ichida.

## 1. Bir martalik o‘rnatish

```bash
cd "/Users/macbook/Desktop/TalabaGo 8"
bash scripts/mac/setup.sh
```

Skript Homebrew orqali Python 3.11+, Node.js 20+ va `cloudflared` ni tekshiradi yoki o‘rnatadi. So‘ng backend uchun `.venv` va kutubxonalarni, ikkala frontend uchun `npm install` ni bajaradi. `backend/.env` bo‘lmasa, uni yangi `JWT_SECRET_KEY` bilan yaratadi. Administrator ham sozlanadi: `.env` dagi `ADMIN_USERNAME` va `ADMIN_PASSWORD_HASH` ishlatiladi, ular bo‘lmasa login so‘raladi.

`backend/.env` ga Telegram ma’lumotlarini yozing:

```bash
open -e "/Users/macbook/Desktop/TalabaGo 8/backend/.env"
#   BOT_TOKEN=123456:ABC...   (@BotFather)
#   ADMIN_ID=123456789        (o‘z chat ID’ingiz: @userinfobot ga /start yozing)
```

## 2. Ishga tushirish

```bash
cd "/Users/macbook/Desktop/TalabaGo 8"
bash scripts/mac/start.sh            # tezkor HTTPS tunnel (https://*.trycloudflare.com) + bot
bash scripts/mac/start.sh --named    # o‘z domeningiz (deploy/cloudflared/config.yml)
bash scripts/mac/start.sh --local    # faqat http://localhost (Telegram tugmasi ishlamaydi)
bash scripts/mac/start.sh --dev      # frontendlar Vite dev server’da (hot reload) — faqat dasturlash uchun, --named/--local bilan ham ishlaydi
bash scripts/mac/stop.sh             # hammasini to‘xtatish
tail -f .run/logs/backend.log        # loglar: backend, frontend, frontend2, tunnel-*, bot
cd backend && .venv/bin/python -m app.cli bot-check   # bot, webhook va menyu tugmasi holati
```

`start.sh` quyidagi tartibda ishlaydi:

1. Ikkala frontendni production build qiladi (`vite build`) va tayyor fayllarni beradi (`vite preview`): Mini App 5173 portda, Support paneli 5174 portda. Telegram’da bir necha siqilgan fayl yuklanadi — dev serverdagi yuzlab modul o‘rniga (telefonda uzoq oq ekran bo‘lmaydi). Kodni o‘zgartirsangiz `start.sh` ni qayta ishga tushiring yoki `--dev` dan foydalaning.
2. Ikkala port uchun HTTP/2 rejimidagi Cloudflare tunnelini ochadi.
3. Tunnel manzili DNS’da paydo bo‘lishini kutadi.
4. Manzilni `backend/.env` dagi `FRONTEND_URL` va `SUPPORT_URL` ga yozadi.
5. FastAPI’ni (8000) ishga tushiradi.
6. Botni ishga tushiradi va Telegram’dagi menyu tugmasini yangi manzilga moslaydi.

Brauzer API’ga faqat sahifa hosti orqali murojaat qiladi: `https://….trycloudflare.com/api/v1` → Vite proxy → FastAPI. Shuning uchun alohida API tunneli, CORS sozlamasi yoki “mixed content” muammosi yo‘q.

## 3. Telegram bot va Mini App

| Holat | Natija |
|---|---|
| `/start` | Salomlashish xabari va uning ostida **🚀 TalabaGo’ni ochish** tugmasi (`InlineKeyboardMarkup` + `WebAppInfo`). Mini App Telegram ichida ochiladi |
| Chat pastidagi tugma | **🚀 Ilovani ochish** (`MenuButtonWebApp`). Hamma chatlar uchun, `/start` bosilganda esa shu chat uchun ham o‘rnatiladi |
| `/app`, istalgan matn | Yana “ochish” tugmasi yuboriladi |
| Kirish | Mini App imzolangan `initData` ni yuboradi, server uni `BOT_TOKEN` bilan HMAC-SHA256 orqali tekshiradi. Ro‘yxatdan o‘tgan foydalanuvchi keyingi safar avtomatik kiradi |

Mini App’ni foydalanuvchi hech narsa bosmasdan avtomatik ochib bo‘lmaydi — buni Telegram ruxsat bermaydi. Eng qisqa yo‘llar: `/start` xabaridagi tugma, doimiy menyu tugmasi va BotFather’dagi Main Mini App (pastga qarang).

Ixtiyoriy, lekin tavsiya etiladi — @BotFather’da:

- `/mybots → bot → Bot Settings → Configure Mini App → Enable Mini App`, URL: Mini App manzili. Shundan keyin bot profilida “Open App” tugmasi va `https://t.me/<bot>?startapp` havolasi ishlaydi.
- `/setdomain` (agar Telegram Login Widget kerak bo‘lsa).

Tezkor tunnel manzili har ishga tushganda o‘zgaradi. Menyu tugmasi avtomatik yangilanadi, lekin BotFather’dagi Main Mini App URL’ini qo‘lda yangilash kerak. Doimiy ishlash uchun `--named` rejimidan foydalaning.

## 4. Doimiy domen (Cloudflare named tunnel)

```bash
cloudflared tunnel login
cloudflared tunnel create talabago
cloudflared tunnel route dns talabago app.DOMEN.uz
cloudflared tunnel route dns talabago support.DOMEN.uz
cp deploy/cloudflared/config.example.yml deploy/cloudflared/config.yml   # TUNNEL_ID va domenlarni yozing
cd backend && .venv/bin/python -m app.cli set-env FRONTEND_URL=https://app.DOMEN.uz SUPPORT_URL=https://support.DOMEN.uz COOKIE_SECURE=true && cd ..
# frontend/.env va frontend2/.env: VITE_ALLOWED_HOSTS=localhost,127.0.0.1,app.DOMEN.uz,support.DOMEN.uz
bash scripts/mac/start.sh --named
```

## 5. Cloudflare muammolari

| Belgi (`.run/logs/tunnel-*.log`) | Sabab va yechim |
|---|---|
| `failed to dial to edge with quic: timeout`, `QUIC` xatolari | Tarmoq UDP 7844 portini bloklaydi. Skriptlar har doim `--protocol http2` (TCP 443) bilan ishlaydi. O‘zingiz ishga tushirsangiz ham shu bayroqni qo‘shing |
| `lookup api.trycloudflare.com ... no such host`, `DNS_PROBE_FINISHED_NXDOMAIN` | 1) DNS keshini tozalang: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`. 2) Mac DNS serverini 1.1.1.1 / 8.8.8.8 qiling (System Settings → Network → Details → DNS). 3) VPN va iCloud Private Relay’ni o‘chirib ko‘ring. 4) Yangi trycloudflare manzili DNS’da 10–60 soniyada paydo bo‘ladi — `start.sh` buni kutadi |
| `Blocked request. This host (...) is not allowed` | Host `VITE_ALLOWED_HOSTS` da yo‘q (`frontend/.env`, `frontend2/.env`). `.trycloudflare.com` standart ro‘yxatda bor |
| Telegram’da oq ekran | `FRONTEND_URL` https emas yoki eskirgan. Qayta ishga tushiring va `bot-check` bilan tekshiring |
| Uzoq yuklanish / “Ilova yuklanmadi” ekrani | `--dev` rejimida tunnel orqali juda ko‘p fayl yuklanadi — oddiy `start.sh` (production build) bilan ishga tushiring. 20 soniyada ilova ochilmasa sahifa “Qayta yuklash” tugmasini ko‘rsatadi (bo‘sh ekran o‘rniga) |
| Yangilanishdan keyin bo‘sh sahifa | Telegram eski `index.html` ni keshdan ochgan. Ilova buni o‘zi aniqlab bir marta qayta yuklanadi; `index.html` `Cache-Control: no-cache` bilan beriladi |
| Telegram Desktop’da qora fon | Sahifa `color-scheme: light` va oq fon bilan yuklanadi; yuklanish paytida ham oq ekran va spinner ko‘rinadi |
| Support paneliga kirgach yana login sahifasi | `COOKIE_SECURE=true`, lekin panel http orqali ochilgan. Tunnel (https) orqali oching yoki `--local` rejimidan foydalaning |
| `Error 1033` (named tunnel) | `cloudflared` ishlamayapti yoki `config.yml` dagi TUNNEL_ID xato: `tail .run/logs/tunnel.log` |
