"""Foydalanuvchilar umumiy soni: boshlang‘ich (tiklanmagan) hisob + keyin ro‘yxatdan o‘tgan haqiqiy foydalanuvchilar.

Render’dagi eski JSON baza yo‘qolgan: unda USERS_BASELINE (41) ta haqiqiy foydalanuvchi bo‘lgan, ularning profillari
tiklanmagan va soxta profil YARATILMAYDI. Shuning uchun:

    jami = max(USERS_BASELINE, boshlang‘ich paytda bazada bo‘lganlar) + boshlang‘ich paytdan KEYIN ro‘yxatdan o‘tganlar

Boshlang‘ich payt (since) bir marta belgilanadi va meta.json’da saqlanadi (DATA_DIR — doimiy disk). Disk yo‘q / meta yo‘qolgan
holatda ham natija o‘zgarmasligi uchun USERS_BASELINE_AT muhit o‘zgaruvchisi bilan qat’iy belgilab qo‘yish mumkin (ustun turadi).
Boshlang‘ich paytda bazada bor foydalanuvchilar 41 ning ichida hisoblanadi — ikki marta qo‘shilmaydi.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import common as C
from .config import Settings

log = logging.getLogger('talabago')
META_KEY = 'usersBaseline'


def _ts(v) -> float | None:
    """ISO vaqt → soniya. Noto‘g‘ri/yo‘q qiymat → None."""
    if not v or not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()


def _env_since(settings: Settings) -> str | None:
    v = (settings.USERS_BASELINE_AT or '').strip()
    if not v:
        return None
    if _ts(v) is None:
        log.warning('USERS_BASELINE_AT noto‘g‘ri (ISO kerak, masalan 2026-11-12T00:00:00Z) — e’tiborga olinmadi')
        return None
    return v


def ensure_user_baseline(db: dict, settings: Settings) -> dict:
    """Ishga tushishda (store.tx ichida) bir marta: boshlang‘ich hisobni meta.json’ga yozish. Mavjud bo‘lsa — o‘zgartirmaydi."""
    meta = db['meta']
    cur = meta.get(META_KEY)
    if isinstance(cur, dict) and _ts(cur.get('since')) is not None:
        return cur
    since = _env_since(settings) or C.now_iso()
    s = _ts(since)
    existing = sum(1 for u in db['users'] if (_ts(u.get('createdAt')) or 0) <= s)
    meta[META_KEY] = {'count': int(settings.USERS_BASELINE), 'since': since, 'existingAtStart': existing, 'createdAt': C.now_iso()}
    log.info('Foydalanuvchilar boshlang‘ich hisobi o‘rnatildi: %s (since %s, bazada %s ta)', settings.USERS_BASELINE, since, existing)
    return meta[META_KEY]


def user_totals(meta: dict, users: list, settings: Settings) -> dict:
    """Dashboard uchun hisob. Rollar va haftalik statistika — faqat bazadagi haqiqiy yozuvlardan (frontend hisoblaydi)."""
    b = meta.get(META_KEY) if isinstance(meta.get(META_KEY), dict) else {}
    count = int(settings.USERS_BASELINE)
    since = _env_since(settings) or b.get('since')
    s = _ts(since)
    if s is None:                                   # hali o‘rnatilmagan (bootstrap ishlamagan) — bazadagilar boshlang‘ich hisobda
        existing, new = len(users), 0
    else:
        new = sum(1 for u in users if (_ts(u.get('createdAt')) or 0) > s)
        existing = int(b.get('existingAtStart', len(users) - new)) if b.get('since') == since else len(users) - new
    base = max(count, existing)
    return {
        'total': base + new,
        'baseline': count,
        'since': since,
        'existingAtStart': existing,
        'unrecovered': max(0, count - existing),    # profili tiklanmagan eski foydalanuvchilar (faqat son)
        'newSinceBaseline': new,
        'inDatabase': len(users),
    }


def storage_info(settings: Settings) -> dict:
    """Render’da DATA_DIR doimiy diskda (alohida mount) ekanini tekshirish. Lokal muhitda — None (noma’lum, ogohlantirish yo‘q)."""
    import os
    from pathlib import Path
    if not os.environ.get('RENDER'):
        return {'platform': 'local', 'persistent': None}
    p = Path(settings.DATA_DIR).resolve()
    mounted = any(os.path.ismount(x) for x in [p, *p.parents] if str(x) != '/')
    return {'platform': 'render', 'persistent': mounted}
