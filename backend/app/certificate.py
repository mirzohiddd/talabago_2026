"""Kurs sertifikati: A4 (gorizontal) PDF, QR-kod bilan. Tashqi PDF kutubxonasisiz — Pillow rasm sifatida chizadi va PDF’ga saqlaydi.

QR-kod sertifikatni tekshirish sahifasiga olib boradi: {base}/api/v1/certificates/{code}/page
"""
from __future__ import annotations

import io
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import segno
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / 'assets'
W, H = 1754, 1240                       # A4 gorizontal, 150 dpi
GREEN = (16, 185, 129)
DARK_GREEN = (6, 95, 70)
INK = (17, 17, 17)
MUTED = (90, 96, 105)
MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']


@lru_cache
def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(ASSETS / 'fonts' / 'Inter-Regular.ttf'), size)
    font.set_variation_by_name({
        'Regular': 'Regular',
        'SemiBold': 'SemiBold',
        'ExtraBold': 'ExtraBold',
    }.get(weight, 'Regular'))
    return font


def _fit(text: str, weight: str, size: int, max_w: int) -> ImageFont.FreeTypeFont:
    while size > 24 and _font(weight, size).getlength(text) > max_w:
        size -= 2
    return _font(weight, size)


def format_date(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return ''
    return f'{d.day}-{MONTHS[d.month - 1]}, {d.year}-yil'


def qr_image(url: str, size: int) -> Image.Image:
    q = segno.make(url, error='m')
    rows = list(q.matrix)
    n = len(rows) + 8                                    # 4 modulli oq chegara
    img = Image.new('L', (n, n), 255)
    px = img.load()
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            if v:
                px[x + 4, y + 4] = 0
    return img.resize((size, size), Image.NEAREST).convert('RGB')


def render_pdf(cert: dict, verify_url: str) -> bytes:
    """cert: {fullName, courseTitle, percent, issuedAt, code, status}"""
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    # ramka: qora kontur + yashil ichki chiziq
    d.rounded_rectangle((40, 40, W - 40, H - 40), 36, outline=INK, width=8)
    d.rounded_rectangle((70, 70, W - 70, H - 70), 26, outline=GREEN, width=4)
    # burchak nuqtalari (halftone uslubi)
    for cx, cy in ((110, 110), (W - 110, 110)):
        for i in range(7):
            for j in range(7):
                r = max(0, 6 - (i + j) * 0.55)
                if r > 0.8:
                    sx = cx + (i * 22 if cx < W / 2 else -i * 22)
                    sy = cy + (j * 22 if cy < H / 2 else -j * 22)
                    d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(190, 238, 218))
    # logotip
    try:
        logo = Image.open(ASSETS / 'logo.webp').convert('RGBA')
        lw = 420
        logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
        im.paste(logo, ((W - lw) // 2, 120), logo)
        y = 120 + logo.height + 40
    except OSError:
        d.text((W / 2, 170), 'TalabaGo', font=_font('ExtraBold', 72), fill=DARK_GREEN, anchor='mm')
        y = 250
    d.text((W / 2, y + 40), 'SERTIFIKAT', font=_font('ExtraBold', 96), fill=INK, anchor='mm')
    d.line((W / 2 - 170, y + 112, W / 2 + 170, y + 106), fill=GREEN, width=10)
    d.text((W / 2, y + 175), 'Ushbu sertifikat egasi', font=_font('Regular', 38), fill=MUTED, anchor='mm')
    name = cert.get('fullName') or '—'
    d.text((W / 2, y + 265), name, font=_fit(name, 'ExtraBold', 88, W - 360), fill=INK, anchor='mm')
    course = f'“{cert.get("courseTitle") or "Kurs"}” kursini muvaffaqiyatli tamomladi'
    d.text((W / 2, y + 360), course, font=_fit(course, 'SemiBold', 44, W - 360), fill=INK, anchor='mm')
    score = f'Yakuniy test natijasi: {cert.get("percent", 0)}%'
    d.text((W / 2, y + 430), score, font=_font('SemiBold', 38), fill=DARK_GREEN, anchor='mm')
    # pastki qism: sana, raqam, QR
    by = H - 300
    d.text((150, by + 30), 'Berilgan sana', font=_font('Regular', 30), fill=MUTED, anchor='lm')
    d.text((150, by + 78), format_date(cert.get('issuedAt', '')), font=_font('SemiBold', 38), fill=INK, anchor='lm')
    d.text((150, by + 140), 'Sertifikat raqami', font=_font('Regular', 30), fill=MUTED, anchor='lm')
    d.text((150, by + 188), cert.get('code', ''), font=_font('SemiBold', 38), fill=INK, anchor='lm')
    qs = 220
    q = qr_image(verify_url, qs)
    qx, qy = W - 150 - qs, by - 60
    d.rounded_rectangle((qx - 14, qy - 14, qx + qs + 14, qy + qs + 14), 18, outline=INK, width=4)
    im.paste(q, (qx, qy))
    d.text((qx + qs / 2, qy + qs + 36), 'Haqiqiyligini tekshirish', font=_font('Regular', 26), fill=MUTED, anchor='mm')
    if cert.get('status') == 'revoked':
        stamp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        sd.text((W / 2, H / 2), 'BEKOR QILINGAN', font=_font('ExtraBold', 150), fill=(220, 38, 38, 150), anchor='mm')
        im.paste(stamp.rotate(18, resample=Image.BICUBIC), (0, 0), stamp.rotate(18, resample=Image.BICUBIC))
    buf = io.BytesIO()
    im.save(buf, 'PDF', resolution=150.0, title=f'TalabaGo sertifikati {cert.get("code", "")}', author='TalabaGo')
    return buf.getvalue()
