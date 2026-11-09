# TalabaGo — Mini App / website (frontend)

Vue 3 + Vite + Tailwind CSS v4 + Vue Router + lucide-vue-next. Telegram Mini App va oddiy brauzerda ishlaydi.
Barcha ma’lumot TalabaGo API’dan (`../backend`), mock yoki demo ma’lumot yo‘q.

```bash
npm install
npm run dev     # http://localhost:5173
npm run build   # dist/ — statik hosting (Telegram Mini App uchun https)
```

`.env`: `VITE_API_URL=http://localhost:8000/api/v1` (production’da `https://api.domen.uz/api/v1`).

| Rol | Sahifalar |
|---|---|
| Talaba | Ishlar · Turar joy · Arizalarim · Kurslar · Sozlamalar |
| Ish beruvchi | Ishlar · E’lon qo‘shish · Arizalar · Sozlamalar |
| Uy egasi | Uylar · E’lon qo‘shish · So‘rovlar · Sozlamalar |

Texnik yordam (Support chat) — Sozlamalar va navbar yordam ikonkasidan.

**Kirish**
- Birinchi kirish: 6 bosqich (til → 3 ta tanishtiruv → rol → ro‘yxatdan o‘tish).
- Telegram ichida: imzolangan `initData` serverga yuboriladi; keyingi ochilishlarda avtomatik kirish (`POST /auth/telegram`).
- Brauzerda: ro‘yxatdan o‘tishda parol o‘rnatiladi, keyin `/login` — telefon raqam + parol. Token `localStorage`da, muddati tugasa yoki hisob bloklansa kirish sahifasiga qaytariladi.

**Tuzilma**
```
src/
├─ services/http.js       # API klient (Bearer token, Telegram initData, /media URL)
├─ services/index.js      # barcha API chaqiruvlari (auth, jobs, housing, applications, courses, support, ...)
├─ services/adsFeed.js    # reklama carousel: GET /ads/active
├─ services/telegram.js   # Telegram WebApp SDK qobig‘i
├─ stores/session.js      # token, rol, onboarding holati, sozlamalar
├─ views/auth/            # Splash, Onboarding (6 bosqich), Login
├─ views/shared|student/  # rol sahifalari
├─ components/            # UI, kartochkalar, formalar, modallar, layout, brand (logo/illustratsiyalar)
└─ assets/                # logo va illustratsiyalar (webp)
```
Tarjimalar: `../shared/i18n` (O‘zbekcha lotin/kirill, Русский, English).
