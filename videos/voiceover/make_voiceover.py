#!/usr/bin/env python3
"""
TalabaGo Reels — ElevenLabs o‘zbekcha ovozini videoga qo‘shish.

  export ELEVENLABS_API_KEY=...        # yoki videos/.env / backend/.env ichida ELEVENLABS_API_KEY=...
  python3 videos/voiceover/make_voiceover.py

Nima qiladi:
  1. script.json dagi har bir qatorni ElevenLabs TTS (voice: agoC45V78njTIxYzwmSb) bilan alohida generatsiya qiladi
     (natija cache/ papkasida saqlanadi — qayta ishga tushirishda pul sarflanmaydi).
  2. Har qatorni subtitr vaqtiga joylaydi; uzun bo‘lsa 1.25× gacha tezlashtiradi (subtitr bilan mos qoladi).
  3. Ovoz eshitilganda musiqa avtomatik pasayadi (sidechain ducking), umumiy balandlik −14 LUFS (Instagram).
  4. Video oqimi qayta kodlanmaydi: videos/TalabaGo_Instagram_Reels.mp4 yangilanadi,
     ovozsiz nusxa — TalabaGo_Instagram_Reels_music_only.mp4.

Kalit hech qachon ekranga yoki logga chiqarilmaydi. Talab: Python 3.9+, ffmpeg (brew install ffmpeg).
Sinov (internet/kalitsiz): --fake-tts — ovoz o‘rniga signal tonlari bilan butun quvurni tekshiradi.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIDEOS = HERE.parent
ROOT = VIDEOS.parent
FINAL = VIDEOS / 'TalabaGo_Instagram_Reels.mp4'
MUSIC_ONLY = VIDEOS / 'TalabaGo_Instagram_Reels_music_only.mp4'
MODELS = [os.environ.get('ELEVENLABS_MODEL') or 'eleven_v3', 'eleven_multilingual_v2']  # v3 o‘zbek tilini qo‘llaydi
MAX_SPEEDUP = 1.25


def api_key() -> str:
    key = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if key:
        return key
    for env in (VIDEOS / '.env', ROOT / 'backend' / '.env', ROOT / '.env'):
        if env.exists():
            for line in env.read_text(encoding='utf-8').splitlines():
                if line.strip().startswith('ELEVENLABS_API_KEY='):
                    val = line.split('=', 1)[1].strip().strip('"\'')
                    if val:
                        return val
    sys.exit('ELEVENLABS_API_KEY topilmadi. export ELEVENLABS_API_KEY=... qiling yoki videos/.env ga yozing.')


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'ffmpeg xatosi: {r.stderr[-600:]}')
    return r.stdout


def duration(path: Path) -> float:
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]).strip())


def tts(text: str, voice: str, key: str, out: Path) -> str:
    last = None
    for model in MODELS:
        body = json.dumps({'text': text, 'model_id': model,
                           'voice_settings': {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.3, 'use_speaker_boost': True}}).encode()
        req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_192', data=body, method='POST',
                                     headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out.write_bytes(r.read())
            return model
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:300]
            if e.code == 401:
                sys.exit('ElevenLabs: kalit noto‘g‘ri yoki ruxsat yo‘q (401).')
            if e.code == 429:
                sys.exit('ElevenLabs: limit tugagan (429). Keyinroq urinib ko‘ring.')
            last = f'{model}: HTTP {e.code} {msg}'
            continue  # boshqa model bilan urinib ko‘ramiz
        except urllib.error.URLError as e:
            sys.exit(f'ElevenLabs’ga ulanib bo‘lmadi: {e.reason}')
    sys.exit(f'TTS bajarilmadi — {last}')


def fake_tts(text: str, out: Path) -> str:
    """Kalitsiz sinov: matn uzunligiga mos (≈14 belgi/s) signal tonlari."""
    d = max(1.2, len(text) / 14)
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'sine=frequency=220:duration={d:.2f}', '-af', 'volume=0.6,tremolo=f=6:d=0.7', '-ar', '44100', str(out)])
    return 'fake'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fake-tts', action='store_true', help='ElevenLabs o‘rniga sinov tonlari')
    ap.add_argument('--music-db', type=float, default=-6.0, help='ovoz paytidagidan tashqari musiqa darajasi (dB)')
    a = ap.parse_args()
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            sys.exit(f'{tool} topilmadi: brew install ffmpeg')
    script = json.loads((HERE / 'script.json').read_text(encoding='utf-8'))
    voice = script['voice_id']
    if not MUSIC_ONLY.exists():
        if not FINAL.exists():
            sys.exit(f'Video topilmadi: {FINAL}')
        shutil.copy2(FINAL, MUSIC_ONLY)  # asl (musiqa + subtitr) nusxa bir marta saqlanadi
    key = None if a.fake_tts else api_key()
    cache = HERE / 'cache'
    cache.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='tg-voice-'))
    lines = script['lines']
    inputs, filters = [], []
    for i, line in enumerate(lines):
        text = line.get('voice') or line['text']
        h = hashlib.sha1(f'{voice}|{text}|{MODELS[0]}|{a.fake_tts}'.encode()).hexdigest()[:12]
        raw = cache / f'{i:02d}-{h}.mp3'
        if not raw.exists():
            model = fake_tts(text, raw) if a.fake_tts else tts(text, voice, key, raw)
            print(f'  {i + 1:02d}/{len(lines)} generatsiya ({model})')
        d = duration(raw)
        nxt = lines[i + 1]['start'] if i + 1 < len(lines) else 75.0
        slot = max(0.8, nxt - line['start'] - 0.15)
        speed = min(MAX_SPEEDUP, d / slot) if d > slot else 1.0
        if d / speed > slot + 0.05:
            print(f'  ! {i + 1}-qator {d:.1f}s — vaqtga sig‘magan ({slot:.1f}s); script.json da matnni qisqartiring')
        inputs += ['-i', str(raw)]
        ms = int(line['start'] * 1000)
        filters.append(f'[{i + 1}:a]aresample=48000,atempo={speed:.3f},adelay={ms}|{ms},apad=whole_dur=75[v{i}]')
    n = len(lines)
    graph = ';'.join(filters) + ';' + ''.join(f'[v{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0:dropout_transition=0,'
    graph += 'highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,volume=1.6[voice];'
    graph += '[voice]asplit=2[vk][vm];'
    graph += f'[0:a]volume={a.music_db}dB[mus];[mus][vk]sidechaincompress=threshold=0.03:ratio=10:attack=15:release=350:makeup=1[duck];'
    graph += '[duck][vm]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=73.4:d=1.6[a]'
    out = tmp / 'final.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(MUSIC_ONLY), *inputs, '-filter_complex', graph,
         '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-t', '75', str(out)])
    shutil.move(out, FINAL)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'Tayyor: {FINAL}  ({FINAL.stat().st_size / 1e6:.1f} MB) · ovozsiz nusxa: {MUSIC_ONLY.name}')


if __name__ == '__main__':
    main()
