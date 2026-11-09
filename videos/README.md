# TalabaGo — Instagram Reels / Story reklama videosi

| Fayl | Tavsif |
|---|---|
| `TalabaGo_Instagram_Reels.mp4` | 1080×1920 (9:16), 75 s, 30 fps, H.264 + AAC, subtitrlar videoga yozilgan, fon musiqasi |
| `TalabaGo_Instagram_Reels.srt` | Subtitrlar (alohida fayl) |
| `voiceover/script.json` | Ovoz va subtitr matni + vaqtlari (yagona manba) |
| `voiceover/make_voiceover.py` | ElevenLabs o‘zbekcha ovozini qo‘shadi (voice `agoC45V78njTIxYzwmSb`) |
| `source/` | Videoni qayta yaratish: yozib olish, kompozitsiya, musiqa, render |

## Ovozni qo‘shish (macOS)

```bash
cd "/Users/macbook/Desktop/TalabaGo 9"
brew install ffmpeg                         # bir marta
export ELEVENLABS_API_KEY="..."              # yoki videos/.env ga: ELEVENLABS_API_KEY=...
python3 videos/voiceover/make_voiceover.py
```
Natija: `videos/TalabaGo_Instagram_Reels.mp4` ovoz bilan yangilanadi (musiqa ovoz paytida avtomatik pasayadi, −14 LUFS),
ovozsiz nusxa `TalabaGo_Instagram_Reels_music_only.mp4` bo‘lib saqlanadi. Har qator alohida generatsiya qilinadi va
subtitr vaqtiga joylanadi; natija `voiceover/cache/` da saqlanadi (qayta ishga tushirish bepul).
Model: `eleven_v3` (o‘zbek tili), ishlamasa `eleven_multilingual_v2`; boshqasini `ELEVENLABS_MODEL=...` bilan tanlash mumkin.
Matnni o‘zgartirish: `voiceover/script.json` (`text` — subtitr, `voice` — o‘qiladigan matn).
Subtitrlar videoga yozilgan — matn o‘zgarsa videoni qayta render qiling (pastga qarang).

## Videoni qayta yaratish

1. Backend (bo‘sh `DATA_DIR`, test `BOT_TOKEN`) va Mini App’ni ishga tushiring; `python3 source/seed.py` — namunaviy e’lonlar.
2. `python3 source/record.py` — Playwright Mini App’ni Telegram rejimida 390×844@3x yozib oladi (`source/frames/`).
3. `data.js` / `subs.js` ni yarating (frames/*/index.json, events.json va voiceover/script.json dan), `python3 source/music.py music.wav`.
4. `python3 source/render.py source music.wav TalabaGo_Instagram_Reels.mp4` — kompozitor (`compose.html`) kadrma-kadr → FFmpeg.

## Ma’lumotlar haqida

Ilovadagi ish va uy e’lonlari videoni tayyorlash uchun yaratilgan **namunaviy e’lonlar** — videoda ham shunday belgilangan
(“Namunaviy e’lonlar — ilova imkoniyatlarini ko‘rsatish uchun”). Hech qanday mijoz soni, statistika yoki sharh ko‘rsatilmagan.
Kurs darslari — ilovadagi haqiqiy kontent. Fon musiqasi `source/music.py` da kod bilan sintez qilingan original asar (tashqi sempl yo‘q).
