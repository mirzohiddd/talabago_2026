"""
TalabaGo reklama videosi uchun ORIGINAL fon musiqasi (kod bilan sintez qilingan — tashqi namuna/sempl yo‘q,
shuning uchun litsenziya cheklovi yo‘q). 75 s, 104 BPM, Am–F–C–G. Natija: 48 kHz stereo WAV.
Ishlatish: python3 music.py out.wav
"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR, DUR, BPM = 48000, 75.0, 104
BEAT = 60 / BPM
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(2026)
L = np.zeros(N); R = np.zeros(N)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(round(start * SR))
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= N or not len(sig): return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * gain * np.sqrt(0.5 * (1 + pan))

def env(n, a, d, s, r, length):
    tt = np.arange(n) / SR
    e = np.where(tt < a, tt / a, np.where(tt < a + d, 1 - (1 - s) * (tt - a) / d, s))
    rel = np.clip((length - tt) / r, 0, 1)
    return e * np.where(tt > length - r, rel, 1)

CHORDS = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]  # Am F C G
BAR = 4 * BEAT
GRID0 = 5.0 - 3 * BAR          # bar chegarasi aynan 5.0 s ga tushadi (intro → asosiy qism)
bars = int((DUR - GRID0) / BAR) + 1

def section(t):
    if t < 4.99: return 'intro'
    if t >= 72.0: return 'end'
    if 65.0 <= t < 72.0: return 'outro'
    return 'main'

for b in range(bars):
    t0 = GRID0 + b * BAR
    if t0 >= DUR: break
    root, notes = CHORDS[b % 4]
    sec = section(t0)
    # --- pad (bir necha garmonika, sekin attack, low-pass) ---
    n = int(SR * (BAR + 0.6)); tt = np.arange(n) / SR
    pad = np.zeros(n)
    for k, m in enumerate(notes + [notes[0] + 12]):
        f = midi(m)
        for det in (-0.12, 0.12):
            ph = 2 * np.pi * f * (1 + det / 100) * tt
            pad += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)) / 2
    pad = lp(pad, 1800 if sec != 'intro' else 1100) * env(n, 0.45, 0.4, 0.85, 0.6, BAR + 0.6)
    add(pad, t0, 0.055 if sec != 'end' else 0.07)
    if sec in ('main', 'outro'):
        # --- arpedjio (8-lik notalar) ---
        arp = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[1] + 12, notes[0] + 24, notes[2] + 12, notes[1] + 12, notes[2] + 12]
        for i, m in enumerate(arp):
            st = t0 + i * BEAT / 2
            nn = int(SR * 0.42); tt = np.arange(nn) / SR
            f = midi(m)
            pl = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 9)
            add(lp(pl, 6000), st, 0.11, pan=-0.35 if i % 2 else 0.35)
        # --- bas ---
        for st, ln in ((0, 1.4), (1.5, 0.45), (2, 1.4), (3.5, 0.45)):
            nn = int(SR * ln * BEAT); tt = np.arange(nn) / SR
            f = midi(root - 12)
            bs = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env(nn, 0.008, 0.15, 0.6, 0.08, ln * BEAT)
            add(lp(bs, 600), t0 + st * BEAT, 0.20)
        # --- ritm ---
        for beat in range(4):
            st = t0 + beat * BEAT
            if beat in (0, 2) or (sec == 'main' and beat == 3 and b % 2):  # kick
                nn = int(SR * 0.32); tt = np.arange(nn) / SR
                fr = 45 + 75 * np.exp(-tt * 28)
                kick = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 9)
                add(kick, st, 0.42)
            if beat in (1, 3):  # clap
                nn = int(SR * 0.18); tt = np.arange(nn) / SR
                cl = bp(rng.standard_normal(nn), 900, 4500) * np.exp(-tt * 22)
                add(cl, st, 0.07)
            for h in (0.5,):  # hi-hat (offbeat)
                nn = int(SR * 0.06); tt = np.arange(nn) / SR
                hh = hp(rng.standard_normal(nn), 7000) * np.exp(-tt * 70)
                add(hh, st + h * BEAT, 0.075, pan=0.2)

# --- intro riser (0.5–5 s) va o‘tish “whoosh”lari ---
nn = int(SR * 4.4); tt = np.arange(nn) / SR
noise = rng.standard_normal(nn)
riser = sum(bp(noise, 300 + 2500 * (k / 6), 600 + 3500 * (k / 6)) * ((tt / 4.4) ** 2) * (tt / 4.4 > k / 7) for k in range(7)) / 4
add(riser, 0.6, 0.12)
for st in (15.0, 30.0, 43.0, 55.0, 65.0):
    nn = int(SR * 0.7); tt = np.arange(nn) / SR
    w = bp(rng.standard_normal(nn), 500, 5000) * np.sin(np.pi * tt / 0.7) ** 2
    add(w, st - 0.45, 0.05)
# yakuniy akkord (Am add9) — 72 s dan sekin so‘nadi
nn = int(SR * 3.2); tt = np.arange(nn) / SR
fin = sum(np.sin(2 * np.pi * midi(m) * tt) for m in (57, 64, 69, 71, 72)) * np.exp(-tt * 1.1)
add(lp(fin, 2500), 71.9, 0.07)

mix = np.stack([L, R], 1)
mix *= np.clip(np.minimum(t_all / 0.6, (DUR - t_all) / 1.8), 0, 1)[:, None]  # fade in/out
mix = np.tanh(mix * 1.3) / np.tanh(1.3)                                  # yumshoq limiter
mix /= np.max(np.abs(mix)) / 0.89
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else 'music.wav', SR, (mix * 32767).astype(np.int16))
print('ok', DUR, 's')
