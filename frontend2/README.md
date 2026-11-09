# TalabaGo Support (frontend2)

Faqat vakolatli administratorlar uchun boshqaruv paneli. Port: **5174**. Barcha ma’lumot TalabaGo API’dan (`../backend`).

```bash
npm install
npm run dev     # http://localhost:5174
npm run build   # dist/
```

`.env`: `VITE_API_URL=http://localhost:8000/api/v1`. Panel manzili backend `.env` dagi `CORS_ORIGINS` da bo‘lishi shart.

**Kirish**: `POST /auth/admin/login` → HttpOnly cookie (8 soat). Login/parol kodda yo‘q — administrator backendda yaratiladi
(`python -m app.cli create-admin --username <login>` yoki `.env` dagi `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH`). Parolni panel Sozlamalaridan o‘zgartirish mumkin (boshqa sessiyalar yopiladi).

**Sahifalar**: Dashboard (bugun/hafta/oy) · Foydalanuvchilar · Ish e’lonlari · Turar joylar · Reklama boshqaruvi · Kurslar boshqaruvi · Arizalar va so‘rovlar · Support (inbox + chat) · Shikoyatlar · Sozlamalar.
Sidebar yig‘iladi (holati saqlanadi), mobilda drawer. Ma’lumotlar har 30 soniyada serverdan yangilanadi.

| Qism | Fayl |
|---|---|
| API klient | `src/services/http.js` (cookie, `X-Requested-With`, fayl yuklash `/crm/files`) |
| Autentifikatsiya | `src/services/auth/index.js` |
| Ma’lumotlar ombori | `src/services/crm.js` (`/crm/*`) |
| Reklamalar | `src/services/ads.js` (`/ads`) |
