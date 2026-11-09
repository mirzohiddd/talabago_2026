"""
Xavfsiz fayl yuklash:
* tur fayl kengaytmasi bo‘yicha emas, ichidagi "magic bytes" bo‘yicha aniqlanadi;
* rasmlar Pillow bilan qayta kodlanadi (WEBP) — EXIF/GPS va yashirin qo‘shimchalar o‘chadi;
* nomlar tasodifiy (uuid), foydalanuvchi bergan nom faqat ko‘rsatish uchun saqlanadi;
* hajm cheklovi o‘qish jarayonida tekshiriladi.
"""
from __future__ import annotations

import io
import secrets
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 40_000_000

KINDS = {
    # kind: (ruxsat etilgan turlar, maks. MB kaliti)
    'photo': ({'image'}, 'MAX_IMAGE_MB'),
    'shot': ({'image'}, 'MAX_IMAGE_MB'),
    'logo': ({'image'}, 'MAX_IMAGE_MB'),
    'cv': ({'pdf', 'doc', 'docx'}, 'MAX_DOC_MB'),
    'ad': ({'image', 'video'}, 'MAX_VIDEO_MB'),
    'lesson': ({'video', 'image'}, 'MAX_VIDEO_MB'),
    'file': ({'image', 'pdf'}, 'MAX_IMAGE_MB'),
}
MIME = {'pdf': 'application/pdf', 'doc': 'application/msword', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'mp4': 'video/mp4', 'webm': 'video/webm', 'webp': 'image/webp'}


def sniff(head: bytes) -> tuple[str, str] | None:
    """(guruh, kengaytma) — fayl boshidagi baytlar bo‘yicha."""
    if head[:3] == b'\xff\xd8\xff' or head[:8] == b'\x89PNG\r\n\x1a\n' or (head[:4] == b'RIFF' and head[8:12] == b'WEBP') or head[:6] in (b'GIF87a', b'GIF89a'):
        return 'image', 'img'
    if head[:5] == b'%PDF-':
        return 'pdf', 'pdf'
    if head[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return 'doc', 'doc'
    if head[:4] == b'PK\x03\x04':
        return 'docx', 'docx'
    if head[4:8] == b'ftyp':
        return 'video', 'mp4'
    if head[:4] == b'\x1a\x45\xdf\xa3':
        return 'video', 'webm'
    return None


async def save_upload(file: UploadFile, kind: str, media_dir: Path, settings) -> dict:
    if kind not in KINDS:
        raise HTTPException(400, 'Noto‘g‘ri fayl turi')
    allowed, mb_key = KINDS[kind]
    max_bytes = getattr(settings, mb_key) * 1024 * 1024
    buf = io.BytesIO()
    while chunk := await file.read(1024 * 1024):
        buf.write(chunk)
        if buf.tell() > max_bytes:
            raise HTTPException(413, f'Fayl juda katta (maks. {getattr(settings, mb_key)} MB)')
    data = buf.getvalue()
    if not data:
        raise HTTPException(400, 'Fayl bo‘sh')
    kind_ext = sniff(data[:16])
    if not kind_ext or kind_ext[0] not in allowed:
        raise HTTPException(415, 'Bu turdagi fayl qabul qilinmaydi')
    group, ext = kind_ext
    folder = media_dir / kind
    folder.mkdir(parents=True, exist_ok=True)
    name = secrets.token_urlsafe(16)
    meta: dict = {}
    if group == 'image':
        try:
            img = Image.open(io.BytesIO(data))
            img.verify()
            img = Image.open(io.BytesIO(data))
            img = ImageOps.exif_transpose(img)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA' if 'A' in img.getbands() else 'RGB')
            limit = 2400 if kind in ('ad', 'lesson') else 1920
            img.thumbnail((limit, limit))
            out = io.BytesIO()
            img.save(out, 'WEBP', quality=86, method=4)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(415, 'Rasmni o‘qib bo‘lmadi') from exc
        data, ext = out.getvalue(), 'webp'
        meta = {'width': img.width, 'height': img.height}
    elif group == 'docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if '[Content_Types].xml' not in z.namelist() or not any(n.startswith('word/') for n in z.namelist()):
                    raise ValueError
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(415, 'Word fayli emas') from exc
    path = folder / f'{name}.{ext}'
    path.write_bytes(data)
    original = Path(file.filename or 'file').name[:120]
    return {'url': f'/media/{kind}/{path.name}', 'name': original, 'size': len(data),
            'mime': MIME.get(ext, f'image/{ext}' if group == 'image' else 'application/octet-stream'), **meta}


def delete_media(media_dir: Path, url: str | None) -> None:
    """Faqat /media/... ichidagi faylni o‘chiradi (path traversal’dan himoya)."""
    if not url or not url.startswith('/media/'):
        return
    target = (media_dir / url[len('/media/'):]).resolve()
    if media_dir.resolve() in target.parents and target.is_file():
        target.unlink(missing_ok=True)
