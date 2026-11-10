"""Umumiy yordamchilar: ID, vaqt, telefon, foydalanuvchini tashqi ko‘rinishga keltirish, bildirishnoma."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

ROLES = ('student', 'employer', 'landlord')
JOB_TYPES = ('hourly', 'daily', 'permanent')
JOB_FORMATS = ('online', 'offline')
SALARY_PERIODS = ('hour', 'day', 'week', 'month')
WORK_TIMES = ('morning', 'day', 'evening', 'night', 'weekend', 'flexible')
HOUSE_TYPES = ('flat', 'room', 'dorm', 'house')
AUDIENCES = ('any', 'male', 'female')
OCCUPANCY = ('free', 'occupied')
RENT_TERMS = ('1', '3', '6', '12')
SHIFTS = ('day', 'evening', 'distance', 'online')
TICKET_TYPES = ('technical', 'account', 'job', 'housing', 'courses', 'other')
TICKET_STATUSES = ('new', 'in_review', 'answered', 'resolved')
COMPLAINT_STATUSES = ('new', 'in_review', 'resolved', 'dismissed')
LISTING_STATUSES = ('pending', 'active', 'rejected', 'closed')
APPLICATION_STATUSES = ('sent', 'viewed', 'interview', 'accepted', 'declined')
REQUEST_STATUSES = ('sent', 'viewed', 'accepted', 'declined')
SALARY_MIN = {'1': 1_000_000, '3': 3_000_000, '5': 5_000_000}
PRICE_MAX = {'1': 1_000_000, '2': 2_000_000, '3': 3_000_000, '5': 5_000_000}
QUIZ_PASS = 3

PRIVATE_USER_FIELDS = ('passwordHash', 'telegramId', 'tokenVersion')  # hech qachon API javobida chiqmaydi


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def new_id(prefix: str) -> str:
    return f'{prefix}_{secrets.token_hex(6)}'


# +998 dan keyingi ruxsat etilgan kodlar (frontend: shared/phone.js bilan bir xil)
PHONE_CODES = frozenset({'20', '33', '50', '55', '61', '62', '65', '66', '67', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79',
                         '80', '87', '88', '90', '91', '92', '93', '94', '95', '97', '98', '99'})


def phone_digits(v: str | None) -> str:
    s = (v or '').strip()
    if s.startswith('+998'):
        return re.sub(r'\D', '', s[4:])
    d = re.sub(r'\D', '', s)
    if len(d) > 9 and d.startswith('998'):  # “998 90 …” — xalqaro shakl; 9 raqamli “99 8…” raqami buzilmaydi
        d = d[3:]
    return d


def phone_problem(v: str | None) -> str | None:
    """None — to‘g‘ri; aks holda o‘zbekcha sabab."""
    d = phone_digits(v)
    if not d:
        return 'Telefon raqamini kiriting'
    if len(d) != 9:
        return 'Telefon raqam to‘liq emas: +998 dan keyin 9 ta raqam kiriting'
    if d[:2] not in PHONE_CODES:
        return 'Operator kodi noto‘g‘ri (masalan: 90, 91, 93, 94, 97, 99, 33, 88)'
    return None


def normalize_phone(v: str | None) -> str | None:
    """“+998 90 123 45 67” yoki None (noto‘g‘ri / to‘liq emas)"""
    if phone_problem(v):
        return None
    d = phone_digits(v)
    return f'+998 {d[:2]} {d[2:5]} {d[5:7]} {d[7:]}'


def phone_key(v: str | None) -> str:
    return re.sub(r'\D', '', v or '')[-9:]


def full_name(u: dict | None) -> str:
    return ' '.join(x for x in [(u or {}).get('firstName'), (u or {}).get('lastName')] if x)


def public_user(u: dict) -> dict:
    out = {k: v for k, v in u.items() if k not in PRIVATE_USER_FIELDS}
    out['telegramLinked'] = bool(u.get('telegramId'))
    out['hasPassword'] = bool(u.get('passwordHash'))
    return out


def student_card(u: dict | None) -> dict | None:
    if not u:
        return None
    keys = ('id', 'phone', 'telegram', 'university', 'faculty', 'course', 'shift', 'skills', 'cv', 'about', 'city', 'district', 'birthDate')
    return {'name': full_name(u), **{k: u.get(k) for k in keys}, 'skills': u.get('skills') or []}


def matches(item: dict, q: str | None, fields: list[str]) -> bool:
    if not q:
        return True
    s = q.lower().strip()
    return any(s in str(item.get(f) or '').lower() for f in fields)


def by_date_desc(items: list[dict], key: str = 'createdAt') -> list[dict]:
    return sorted(items, key=lambda x: x.get(key) or '', reverse=True)


def push_status(x: dict, status: str, note: str | None = None, **extra) -> None:
    at = now_iso()
    entry = {'status': status, 'at': at}
    if note:
        entry['note'] = note
    x['history'] = [*(x.get('history') or []), entry]
    x.update(extra, status=status, updatedAt=at)


def add_notification(db_notifications: list, user_id: str, icon: str, title: str, text: str = '', link: str = '') -> dict:
    n = {'id': new_id('n'), 'userId': user_id, 'icon': icon, 'title': title, 'text': text, 'link': link, 'read': False, 'createdAt': now_iso()}
    db_notifications.insert(0, n)
    del db_notifications[5000:]  # cheksiz o‘smasligi uchun
    return n


def tg_chat(u: dict | None):
    """Foydalanuvchining Telegram chat ID’si — faqat u Telegram xabarlarini o‘chirmagan bo‘lsa."""
    if not u or u.get('notifyTelegram') is False or u.get('status') == 'blocked':
        return None
    return u.get('telegramId')


def blocked_ids(users: list[dict]) -> set[str]:
    return {u['id'] for u in users if u.get('status') == 'blocked'}


def monthly_estimate(j: dict) -> float:
    return (j.get('salary') or 0) * {'hour': 160, 'day': 22, 'week': 4, 'month': 1}.get(j.get('salaryPeriod'), 1)


def is_media_url(v) -> bool:
    return isinstance(v, str) and v.startswith('/media/') and '..' not in v