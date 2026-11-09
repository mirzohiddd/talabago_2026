"""Kurslar (talaba), Support murojaatlari (foydalanuvchi), reklamalarning ommaviy qismi."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import common as C
from .. import ratelimit
from ..deps import get_current_user, get_store, platform_settings, require_role
from ..schemas import CompleteLessonIn, MessageIn, TicketIn
from ..storage import JsonStore
from ..telegram import esc, notify_admins

router = APIRouter(tags=['content'])
student = require_role('student')
TYPE_LABEL = {'technical': 'Texnik muammo', 'account': 'Akkaunt', 'job': 'Ish/ariza', 'housing': 'Turar joy', 'courses': 'Kurslar', 'other': 'Boshqa'}
ROLE_LABEL = {'student': 'Talaba', 'employer': 'Ish beruvchi', 'landlord': 'Uy egasi'}


# ============================================================ kurslar
def _published(course: dict) -> list[dict]:
    return sorted([l for l in course.get('lessons', []) if l.get('status') == 'published'], key=lambda l: l.get('order', 0))


def _public_lesson(l: dict) -> dict:
    return l  # test javoblari talaba tomonida darhol tekshirish uchun kerak; ball server tomonda qayta hisoblanadi


@router.get('/courses')
def courses(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    db = store.read_many('courses', 'progress')
    out = []
    for c in db['courses']:
        if c.get('status') != 'published':
            continue
        lessons = _published(c)
        p = next((x for x in db['progress'] if x['userId'] == user['id'] and x['courseId'] == c['id']), None)
        done = len([l for l in lessons if p and l['id'] in p['completed']])
        out.append({**c, 'lessons': [_public_lesson(l) for l in lessons], 'done': done,
                    'percent': round(done / len(lessons) * 100) if lessons else 0})
    return out


@router.get('/courses/{course_id}/progress')
def progress(course_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    p = next((x for x in store.read('progress') if x['userId'] == user['id'] and x['courseId'] == course_id), None)
    return p or {'completed': [], 'scores': {}}


@router.post('/courses/{course_id}/lessons/{lesson_id}/complete')
def complete(course_id: str, lesson_id: str, body: CompleteLessonIn, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    course = next((c for c in store.read('courses') if c['id'] == course_id and c.get('status') == 'published'), None)
    if not course:
        raise HTTPException(404, 'Kurs topilmadi')
    lessons = _published(course)
    idx = next((i for i, l in enumerate(lessons) if l['id'] == lesson_id), None)
    if idx is None:
        raise HTTPException(404, 'Dars topilmadi')
    lesson = lessons[idx]
    quiz = lesson.get('quiz') or []
    if body.answers is not None:
        score = sum(1 for q, a in zip(quiz, body.answers) if q.get('answer') == a)
    elif quiz:
        raise HTTPException(422, 'Test javoblarini yuboring')
    else:
        score = 0
    if quiz and score < min(C.QUIZ_PASS, len(quiz)):
        raise HTTPException(422, f'Dars yakunlanishi uchun kamida {min(C.QUIZ_PASS, len(quiz))} ta to‘g‘ri javob kerak')
    with store.tx('progress') as db:
        p = next((x for x in db['progress'] if x['userId'] == user['id'] and x['courseId'] == course_id), None)
        if not p:
            p = {'id': C.new_id('pg'), 'userId': user['id'], 'courseId': course_id, 'completed': [], 'scores': {}}
            db['progress'].append(p)
        if idx > 0 and lessons[idx - 1]['id'] not in p['completed'] and lesson_id not in p['completed']:
            raise HTTPException(409, 'Avval oldingi darsni yakunlang')
        if lesson_id not in p['completed']:
            p['completed'].append(lesson_id)
        p['scores'][lesson_id] = max(score, p['scores'].get(lesson_id, 0))
        p['updatedAt'] = C.now_iso()
    return {**p, 'score': score}


# ============================================================ support (foydalanuvchi)
def _own_ticket(db: dict, ticket_id: str, user: dict) -> dict:
    t = next((x for x in db['tickets'] if x['id'] == ticket_id and x['userId'] == user['id']), None)
    if not t:
        raise HTTPException(404, 'Murojaat topilmadi')
    return t


def _user_view(t: dict) -> dict:
    return {k: v for k, v in t.items() if k not in ('unreadBySupport', 'internal')}


@router.get('/support/tickets')
def my_tickets(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    return [_user_view(t) for t in C.by_date_desc([t for t in store.read('tickets') if t['userId'] == user['id']], 'updatedAt')]


@router.get('/support/tickets/{ticket_id}')
def my_ticket(ticket_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    return _user_view(_own_ticket({'tickets': store.read('tickets')}, ticket_id, user))


@router.post('/support/tickets', status_code=201, dependencies=[Depends(ratelimit.limit('ticket', 10, 3600))])
def create_ticket(body: TicketIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    at = C.now_iso()
    t = {'id': C.new_id('t'), 'userId': user['id'], 'role': user['role'], 'type': body.type, 'subject': body.subject, 'status': 'new',
         'createdAt': at, 'updatedAt': at, 'unreadByUser': 0, 'unreadBySupport': 1,
         'messages': [
             {'id': C.new_id('m'), 'from': 'user', 'text': body.text, 'at': at, 'attachment': body.attachment.model_dump() if body.attachment else None},
             {'id': C.new_id('m'), 'from': 'system', 'text': 'Murojaatingiz qabul qilindi. Javob shu chatda chiqadi.', 'at': at},
         ]}
    with store.tx('tickets') as db:
        db['tickets'].insert(0, t)
    if (platform_settings(store).get('notifications') or {}).get('newTicket', True):
        notify_admins(
            f'🆘 <b>Yangi Support murojaati</b>\n'
            f'<b>{esc(body.subject)}</b> · {TYPE_LABEL[body.type]}\n'
            f'👤 {esc(C.full_name(user))} ({ROLE_LABEL[user["role"]]}) · {esc(user.get("phone") or "")} {esc(user.get("telegram") or "")}\n\n'
            f'{esc(body.text[:500])}' + ('\n📎 Skrinshot biriktirilgan' if body.attachment else ''),
            f'/support/{t["id"]}')
    return _user_view(t)


@router.post('/support/tickets/{ticket_id}/messages', dependencies=[Depends(ratelimit.limit('ticket-msg', 60, 600))])
def send_message(ticket_id: str, body: MessageIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    if not body.text.strip() and not body.attachment:
        raise HTTPException(422, 'Xabar bo‘sh')
    at = C.now_iso()
    with store.tx('tickets') as db:
        t = _own_ticket(db, ticket_id, user)
        t['messages'].append({'id': C.new_id('m'), 'from': 'user', 'text': body.text.strip(), 'at': at,
                              'attachment': body.attachment.model_dump() if body.attachment else None})
        if t['status'] in ('resolved', 'answered'):
            t['status'] = 'in_review'
        t['updatedAt'] = at
        t['unreadBySupport'] = (t.get('unreadBySupport') or 0) + 1
    notify_admins(f'💬 <b>Support: yangi xabar</b>\n{esc(t["subject"])} — {esc(C.full_name(user))}\n\n{esc(body.text[:400])}', f'/support/{t["id"]}')
    return _user_view(t)


@router.post('/support/tickets/{ticket_id}/read', status_code=204)
def mark_read(ticket_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    with store.tx('tickets') as db:
        _own_ticket(db, ticket_id, user)['unreadByUser'] = 0


# ============================================================ reklamalar (ommaviy)
def _parse(s: str | None) -> datetime | None:
    """ISO sana. Vaqt zonasi ko‘rsatilmagan bo‘lsa — UTC deb olinadi (aware/naive solishtirish xatosi bo‘lmasin)."""
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00')) if isinstance(s, str) and s else None
    except ValueError:
        return None
    return d.replace(tzinfo=timezone.utc) if d and d.tzinfo is None else d


def ad_state(ad: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    start, end = _parse(ad.get('startAt')), _parse(ad.get('endAt'))
    if end and now >= end:
        return 'expired'
    if not ad.get('enabled'):
        return 'inactive'
    if start and now < start:
        return 'scheduled'
    return 'live'


def public_ad(a: dict) -> dict:
    keys = ('id', 'type', 'order', 'enabled', 'title', 'description', 'link', 'placements', 'startAt', 'endAt', 'createdAt', 'media')
    return {k: a.get(k) for k in keys}


@router.get('/ads/active')
def active_ads(placement: str | None = None, store: JsonStore = Depends(get_store)):
    """Mini App carousel: faqat hozir aktiv (server vaqti, UTC) va shu sahifaga biriktirilgan reklamalar."""
    if not platform_settings(store)['system']['adsEnabled']:
        return []
    now = datetime.now(timezone.utc)
    ads = [a for a in store.read('ads') if ad_state(a, now) in ('live', 'scheduled') and (not placement or placement in (a.get('placements') or []) or 'all' in (a.get('placements') or []))]
    return [public_ad(a) for a in sorted(ads, key=lambda a: (a.get('order') or 999, a.get('createdAt') or ''))]


def _track(field: str):
    def handler(ad_id: str, request: Request, store: JsonStore = Depends(get_store)):
        if ratelimit.hit(f'ad-{field}:{ad_id}:{ratelimit.client_ip(request)}', 1, 600 if field == 'views' else 5):
            return None
        if not platform_settings(store)['system']['adsEnabled']:
            return None
        with store.tx('ads') as db:
            a = next((x for x in db['ads'] if x['id'] == ad_id), None)
            if a and ad_state(a) == 'live':  # faqat hozir ko‘rsatilayotgan reklama hisoblanadi (server vaqti)
                a[field] = (a.get(field) or 0) + 1
    return handler


router.add_api_route('/ads/{ad_id}/view', _track('views'), methods=['POST'], status_code=204)
router.add_api_route('/ads/{ad_id}/click', _track('clicks'), methods=['POST'], status_code=204)
