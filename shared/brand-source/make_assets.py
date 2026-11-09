"""Foydalanuvchi yuborgan logo va illustratsiyalardan shaffof fonli, brend yashiliga (#10B981) moslangan assetlar."""
import numpy as np, cv2, os
from PIL import Image
U = os.path.dirname(os.path.abspath(__file__)) + '/'  # asl rasmlar shu papkada
OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'; os.makedirs(OUT, exist_ok=True)
EMERALD_H = 160 / 2  # OpenCV hue 0..180

def to_rgba(bgr, recolor=True, black_to=None):
    img = bgr.astype(np.float32)
    mn = img.min(axis=2)
    a = np.clip((255 - mn - 10) / (255 - 10 - 20), 0, 1)           # oq → shaffof, chekkalar silliq
    a3 = np.maximum(a, 1e-3)[..., None]
    col = np.clip((img - 255 * (1 - a3)) / a3, 0, 255)               # oq fondan "ajratib olish"
    col = col.astype(np.uint8)
    if recolor:
        hsv = cv2.cvtColor(col, cv2.COLOR_BGR2HSV).astype(np.int32)
        g = (hsv[..., 0] >= 40) & (hsv[..., 0] <= 80) & (hsv[..., 1] > 40)
        hsv[..., 0] = np.where(g, EMERALD_H, hsv[..., 0])
        # yorqinlikni emerald (#10B981, V≈185) ga yaqinlashtirish
        hsv[..., 2] = np.where(g & (hsv[..., 1] > 150), np.clip(hsv[..., 2] * 1.25, 0, 195), hsv[..., 2])
        col = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if black_to is not None:
        dark = col.max(axis=2) < 90
        col[dark] = black_to
    rgba = np.dstack([col[..., ::-1], (a * 255).astype(np.uint8)])
    return rgba

def crop(rgba, pad=6):
    ys, xs = np.where(rgba[..., 3] > 12)
    y0, y1, x0, x1 = max(ys.min() - pad, 0), ys.max() + pad, max(xs.min() - pad, 0), xs.max() + pad
    return rgba[y0:y1 + 1, x0:x1 + 1]

def save(rgba, name, width=None):
    im = Image.fromarray(rgba, 'RGBA')
    if width and im.width > width: im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(f'{OUT}/{name}.webp', 'WEBP', quality=90, method=6)
    return im

# ---------- Logo ----------
logo = cv2.imread(U + 'logo-original.png')
L = crop(to_rgba(logo, black_to=(0x11, 0x11, 0x11)), pad=4)
full = save(L, 'logo', 1200); full.save(f'{OUT}/logo.png')
# T belgisi: "a" harfidan chapdagi komponentlar (T + qalpoq + aylana)
mask = (L[..., 3] > 40).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
xa = None
cols = [i for i in range(1, n) if st[i][4] > 300]
right_of_T = sorted([st[i][0] for i in cols if st[i][0] > L.shape[1] * 0.22])
cut = right_of_T[0] - 6
T = L[:, :cut].copy()
keep = np.isin(lab[:, :cut], [i for i in cols if st[i][0] < cut])
T[..., 3] = np.where(keep, T[..., 3], 0)
T = crop(T, pad=4)
h, w = T.shape[:2]; s = max(h, w)
sq = np.zeros((s, s, 4), np.uint8); sq[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = T
save(sq, 'logo-mark', 512)
Image.fromarray(sq, 'RGBA').resize((512, 512), Image.LANCZOS).save(f'{OUT}/logo-mark.png')
print('logo', full.size, 'mark', sq.shape, 'cut', cut)

# ---------- Personajlar ----------
chars = cv2.imread(U + 'illustrations-characters.png')
CH = ['student', 'student-laptop', 'worker', 'building', 'office-worker']
xs = [0, 335, 850, 1215, 1625, 2172]
for i, nm in enumerate(CH):
    save(crop(to_rgba(chars[150:600, xs[i]:xs[i + 1]])), nm, 520)

# ---------- Ikonkalar (1–5-qatorlar; 6-qator sifatsiz — ishlatilmaydi) ----------
icons = cv2.imread(U + 'illustrations-icons.png')
ROWS = [(312, 500), (500, 668), (668, 792), (792, 905)]
COLS = [0, 300, 545, 795, 1045, 1300]
NAMES = [['laptop', 'books', 'briefcase', 'house', 'keys'],
         ['desk-lamp', 'calendar', 'checklist', 'stats', 'mail'],
         ['search-job', 'search-house', 'support', 'trophy', 'translate'],
         ['video', 'quiz', 'dictionary', 'code', 'office']]
for r, (y0, y1) in enumerate(ROWS):
    for c in range(5):
        cell = icons[y0:y1, COLS[c]:COLS[c + 1]]
        save(crop(to_rgba(cell)), NAMES[r][c], 360)
print(sorted(os.listdir(OUT)))
