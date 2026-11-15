"""Talaba ↔ ish beruvchi chati. Har bir ish arizasiga bitta suhbat (ariza yuborilganda ochiladi).

Faqat suhbat ishtirokchilari (arizani yuborgan talaba va vakansiya egasi) o‘qiy va yoza oladi.
O‘qilgan holat: har bir xabarda readAt; suhbatda har bir ishtirokchi uchun o‘qilmaganlar soni (unread).
Bildirishnoma: qabul qiluvchida o‘qilmagan xabar 0 dan 1 ga o‘tganda (har xabarda spam bo‘lmasligi uchun).
Support xabarni yashirishi yoki suhbatni bloklashi mumkin (admin_extra.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from . import common as C
from . import ratelimit
from .deps import get_current_user, get_store
from .schemas import ChatMessageIn
from .storage import JsonStore
from .telegram import esc, notify_user

router = APIRouter(tags=['chat'])
ROLE_PATH = {'student': '/student/chats', 'employer': '/employer/chats'}
HIDDEN_TEXT = 'Xabar Support tomonidan yashirildi'


def new_chat(app: dict, job: dict) -> dict:
    now = C.now_iso()
    return {'id': C.new_id('ch'), 'applicationId': app['id'], 'jobId': job['id'], 'studentId': app['studentId'], 'employerId': job['employerId'],
            'unread': {app['studentId']: 0, job['employerId']: 0}, 'lastMessage': None, 'locked': False, 'createdAt': now, 'updatedAt': now}


def ensure_chats(db: dict, user: dict) -> bool:
    """Foydalanuvchining arizalari uchun yo‘q suhbatlarni yaratadi (chat funksiyasidan oldingi arizalar ham). O‘zgarish bo‘lsa True."""
    have = {c['applicationId'] for c in db['chats']}
    jobs = {j['id']: j for j in db['jobs']}
    added = False
    for a in db['applications']:
        if a['id'] in have or a['status'] == 'withdrawn':
            continue
        job = jobs.get(a['jobId'])
        if not job or not job.get('employerId'):          # admin e’loni — egasining akkaunti yo‘q, javobni Support beradi
            continue
        if user['id'] not in (a['studentId'], job['employerId']):
            continue
        db['chats'].insert(0, new_chat(a, job))
        added = True
    return added


def _member(chat: dict, user: dict) -> bool:
    return user['id'] in (chat['studentId'], chat['employerId'])


def _other(chat: dict, user_id: str) -> str:
    return chat['employerId'] if user_id == chat['studentId'] else chat['studentId']


def _msg_view(m: dict) -> dict:
    out = {k: m.get(k) for k in ('id', 'chatId', 'fromId', 'text', 'createdAt', 'readAt')}
    if m.get('hidden'):
        out.update(text=HIDDEN_TEXT, hidden=True)
    return out


def _chat_view(c: dict, me: str, users: dict, jobs: dict, apps: dict) -> dict:
    other = users.get(_other(c, me))
    job = jobs.get(c['jobId']) or {}
    app = apps.get(c['applicationId']) or {}
    last = c.get('lastMessage')
    return {
        'id': c['id'], 'applicationId': c['applicationId'], 'applicationStatus': app.get('status'),
        'job': {'id': job.get('id'), 'title': job.get('title'), 'company': job.get('company')},
        'other': {'id': other['id'], 'name': C.full_name(other), 'role': other.get('role'), 'blocked': other.get('status') == 'blocked'} if other else None,
        'lastMessage': {**last, 'text': HIDDEN_TEXT if last.get('hidden') else last.get('text')} if last else None,
        'unread': (c.get('unread') or {}).get(me, 0), 'locked': bool(c.get('locked')), 'updatedAt': c['updatedAt'], 'createdAt': c['createdAt'],
    }


@router.get('/chats')
def my_chats(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    if user['role'] not in ROLE_PATH:
        return []
    db = store.peek('chats', 'applications', 'jobs')
    if ensure_chats({**db, 'chats': list(db['chats'])}, user):        # yangi suhbat kerak bo‘lsagina yoziladi (polling arzon)
        with store.tx('chats', 'applications', 'jobs') as w:
            ensure_chats(w, user)
        db = store.peek('chats', 'applications', 'jobs')
    mine = [c for c in db['chats'] if _member(c, user)]
    jobs = {j['id']: j for j in db['jobs']}
    apps = {a['id']: a for a in db['applications']}
    users = {u['id']: u for u in store.read('users')}
    return [_chat_view(c, user['id'], users, jobs, apps) for c in C.by_date_desc(mine, 'updatedAt')]


@router.get('/chats/unread')
def unread(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    n = sum((c.get('unread') or {}).get(user['id'], 0) for c in store.peek('chats')['chats'] if _member(c, user))
    return {'count': n}


@router.post('/applications/{app_id}/chat')
def open_for_application(app_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    """Ariza kartasidagi “Chat” tugmasi: suhbatni topadi yoki yaratadi."""
    with store.tx('chats', 'applications', 'jobs') as db:
        a = next((x for x in db['applications'] if x['id'] == app_id), None)
        job = a and next((j for j in db['jobs'] if j['id'] == a['jobId']), None)
        if not a or not job or user['id'] not in (a['studentId'], job.get('employerId')):
            raise HTTPException(404, 'Ariza topilmadi')
        if not job.get('employerId'):
            raise HTTPException(409, 'Bu e’lon Support orqali boshqariladi — savollar uchun “Texnik yordam” bo‘limiga yozing')
        c = next((x for x in db['chats'] if x['applicationId'] == app_id), None)
        if not c:
            c = new_chat(a, job)
            db['chats'].insert(0, c)
        jobs = {job['id']: job}
        apps = {a['id']: a}
    users = {u['id']: u for u in store.read('users')}
    return _chat_view(c, user['id'], users, jobs, apps)


def _get_chat(db: dict, chat_id: str, user: dict) -> dict:
    c = next((x for x in db['chats'] if x['id'] == chat_id), None)
    if not c or not _member(c, user):
        raise HTTPException(404, 'Suhbat topilmadi')
    return c


@router.get('/chats/{chat_id}')
def chat_detail(chat_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    db = store.read_many('chats', 'applications', 'jobs', 'users')
    c = _get_chat(db, chat_id, user)
    return _chat_view(c, user['id'], {u['id']: u for u in db['users']}, {j['id']: j for j in db['jobs']}, {a['id']: a for a in db['applications']})


@router.get('/chats/{chat_id}/messages')
def messages(chat_id: str, request: Request, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    """Xabarlar tarixi (eskidan yangiga). ?after=<ISO> — faqat shundan keyingilari (polling uchun)."""
    db = store.peek('chats', 'messages')
    _get_chat(db, chat_id, user)
    after = request.query_params.get('after') or ''
    out = [_msg_view(m) for m in db['messages'] if m['chatId'] == chat_id and (not after or m['createdAt'] > after)]
    return sorted(out, key=lambda m: m['createdAt'])[-500:]


@router.post('/chats/{chat_id}/messages', status_code=201, dependencies=[Depends(ratelimit.limit('chat-msg', 40, 60))])
def send(chat_id: str, body: ChatMessageIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    now = C.now_iso()
    with store.tx('chats', 'messages', 'notifications', 'users', 'jobs') as db:
        c = _get_chat(db, chat_id, user)
        if c.get('locked'):
            raise HTTPException(403, 'Suhbat Support tomonidan cheklangan')
        other_id = _other(c, user['id'])
        other = next((u for u in db['users'] if u['id'] == other_id), None)
        if not other or other.get('status') == 'blocked':
            raise HTTPException(403, 'Suhbatdosh bloklangan — xabar yuborib bo‘lmaydi')
        m = {'id': C.new_id('m'), 'chatId': chat_id, 'fromId': user['id'], 'text': body.text.strip(), 'createdAt': now, 'readAt': None}
        db['messages'].append(m)
        unread = c.setdefault('unread', {})
        first_unread = unread.get(other_id, 0) == 0
        unread[other_id] = unread.get(other_id, 0) + 1
        c['lastMessage'] = {'id': m['id'], 'fromId': user['id'], 'text': m['text'][:160], 'at': now}
        c['updatedAt'] = now
        job = next((j for j in db['jobs'] if j['id'] == c['jobId']), {}) or {}
        link = f'{ROLE_PATH.get(other.get("role"), "/")}/{chat_id}'
        if first_unread:
            C.add_notification(db['notifications'], other_id, 'message', f'Yangi xabar: {C.full_name(user)}', m['text'][:120], link)
    if first_unread:
        notify_user(C.tg_chat(other), f'💬 <b>{esc(C.full_name(user))}</b> ({esc(job.get("title", ""))})\n{esc(m["text"][:300])}', link)
    return _msg_view(m)


@router.post('/chats/{chat_id}/read', status_code=204)
def mark_read(chat_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    now = C.now_iso()
    with store.tx('chats', 'messages') as db:
        c = _get_chat(db, chat_id, user)
        if not (c.get('unread') or {}).get(user['id']):
            return
        for m in db['messages']:
            if m['chatId'] == chat_id and m['fromId'] != user['id'] and not m.get('readAt'):
                m['readAt'] = now
        c.setdefault('unread', {})[user['id']] = 0
