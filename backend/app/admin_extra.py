"""Support CRM: kurs yakuniy testlari, urinishlar, sertifikatlar, chatlar nazorati, baholar nazorati. Barcha endpointlar get_admin bilan himoyalangan."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import common as C
from .config import Settings, get_settings
from .deps import get_admin, get_store
from .storage import JsonStore
from .chat import HIDDEN_TEXT
from .exams import cert_view, verify_url

router = APIRouter(tags=['support-admin'], dependencies=[Depends(get_admin)])


def _find(items: list[dict], item_id: str, msg: str = 'Topilmadi') -> dict:
    x = next((i for i in items if i['id'] == item_id), None)
    if not x:
        raise HTTPException(404, msg)
    return x


def _names(users: list[dict]) -> dict[str, str]:
    return {u['id']: C.full_name(u) for u in users}


# ============================================================ yakuniy test
class ExamQ(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    q: str = Field(min_length=3, max_length=400)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0, le=5)

    @model_validator(mode='after')
    def _check(self):
        self.options = [o.strip() for o in self.options]
        if any(not o for o in self.options):
            raise ValueError('Javob variantlari bo‘sh bo‘lmasin')
        if self.answer >= len(self.options):
            raise ValueError('To‘g‘ri javob variantlar ichidan tanlanishi kerak')
        return self


class FinalTestIn(BaseModel):
    model_config = ConfigDict(extra='ignore')
    status: Literal['draft', 'published'] = 'draft'
    passPercent: int = Field(C.EXAM_PASS_PERCENT, ge=10, le=100)
    maxAttempts: int = Field(C.EXAM_MAX_ATTEMPTS, ge=1, le=5)
    questions: list[ExamQ] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def _pub(self):
        if self.status == 'published' and len(self.questions) < 3:
            raise ValueError('Nashr qilish uchun kamida 3 ta savol kiriting')
        return self


@router.get('/crm/courses/{course_id}/final-test')
def get_final_test(course_id: str, store: JsonStore = Depends(get_store)):
    c = _find(store.read('courses'), course_id, 'Kurs topilmadi')
    t = c.get('finalTest') or {}
    return {'status': t.get('status', 'draft'), 'passPercent': t.get('passPercent', C.EXAM_PASS_PERCENT),
            'maxAttempts': t.get('maxAttempts', C.EXAM_MAX_ATTEMPTS), 'questions': t.get('questions', []), 'updatedAt': t.get('updatedAt')}


@router.put('/crm/courses/{course_id}/final-test')
def save_final_test(course_id: str, body: FinalTestIn, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
    with store.tx('courses') as db:
        c = _find(db['courses'], course_id, 'Kurs topilmadi')
        c['finalTest'] = {**body.model_dump(), 'updatedAt': C.now_iso(), 'updatedBy': admin.get('username')}
        c['updatedAt'] = C.now_iso()
    return c['finalTest']


# ============================================================ urinishlar va sertifikatlar
@router.get('/crm/exams')
def exam_attempts(store: JsonStore = Depends(get_store)):
    db = store.read_many('exams', 'users', 'courses')
    names = _names(db['users'])
    courses = {c['id']: c['title'] for c in db['courses']}
    return [{k: v for k, v in e.items() if k != 'answers'} | {'userName': names.get(e['userId'], '—'), 'courseTitle': courses.get(e['courseId'], e['courseId'])}
            for e in C.by_date_desc(db['exams'])]


class ResetIn(BaseModel):
    userId: str = Field(min_length=1, max_length=40)
    courseId: str = Field(min_length=1, max_length=60)


@router.post('/crm/exams/reset')
def reset_attempts(body: ResetIn, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
    """Talabaga testni qayta topshirishga ruxsat: hisobdagi urinishlar “voided” bo‘ladi (tarix saqlanadi)."""
    n = 0
    with store.tx('exams', 'notifications') as db:
        for e in db['exams']:
            if e['userId'] == body.userId and e['courseId'] == body.courseId and not e.get('voided') and not e.get('passed'):
                e.update(voided=True, voidedAt=C.now_iso(), voidedBy=admin.get('username'))
                n += 1
        if n:
            C.add_notification(db['notifications'], body.userId, 'check', 'Yakuniy testni qayta topshirishingiz mumkin', 'Support yangi urinishlar berdi', f'/student/courses/{body.courseId}/exam')
    if not n:
        raise HTTPException(409, 'Bekor qilinadigan urinish yo‘q')
    return {'reset': n}


@router.get('/crm/certificates')
def certificates(request: Request, store: JsonStore = Depends(get_store), settings: Settings = Depends(get_settings)):
    return [{**cert_view(c), 'userId': c['userId'], 'revokedAt': c.get('revokedAt'), 'revokeReason': c.get('revokeReason'),
             'verifyUrl': verify_url(request, settings, c['code'])} for c in C.by_date_desc(store.read('certificates'), 'issuedAt')]


class CertPatch(BaseModel):
    status: Literal['valid', 'revoked']
    reason: str = Field('', max_length=300)


@router.patch('/crm/certificates/{cert_id}')
def patch_certificate(cert_id: str, body: CertPatch, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
    with store.tx('certificates') as db:
        c = _find(db['certificates'], cert_id, 'Sertifikat topilmadi')
        if body.status == 'valid' and any(x['userId'] == c['userId'] and x['courseId'] == c['courseId'] and x['status'] == 'valid' and x['id'] != c['id']
                                          for x in db['certificates']):
            raise HTTPException(409, 'Bu talabada shu kurs bo‘yicha boshqa amaldagi sertifikat bor')
        c['status'] = body.status
        if body.status == 'revoked':
            c.update(revokedAt=C.now_iso(), revokedBy=admin.get('username'), revokeReason=body.reason.strip())
    return c


# ============================================================ chatlar nazorati
@router.get('/crm/chats')
def chats(store: JsonStore = Depends(get_store)):
    db = store.read_many('chats', 'messages', 'users', 'jobs')
    names = _names(db['users'])
    jobs = {j['id']: j['title'] for j in db['jobs']}
    counts: dict[str, int] = {}
    for m in db['messages']:
        counts[m['chatId']] = counts.get(m['chatId'], 0) + 1
    return [{'id': c['id'], 'applicationId': c['applicationId'], 'jobId': c['jobId'], 'jobTitle': jobs.get(c['jobId'], '—'),
             'studentId': c['studentId'], 'studentName': names.get(c['studentId'], '—'), 'employerId': c['employerId'], 'employerName': names.get(c['employerId'], '—'),
             'messages': counts.get(c['id'], 0), 'lastMessage': c.get('lastMessage'), 'locked': bool(c.get('locked')),
             'createdAt': c['createdAt'], 'updatedAt': c['updatedAt']} for c in C.by_date_desc(db['chats'], 'updatedAt')]


@router.get('/crm/chats/{chat_id}/messages')
def chat_messages(chat_id: str, store: JsonStore = Depends(get_store)):
    db = store.read_many('chats', 'messages')
    _find(db['chats'], chat_id, 'Suhbat topilmadi')
    return sorted([m for m in db['messages'] if m['chatId'] == chat_id], key=lambda m: m['createdAt'])


class LockIn(BaseModel):
    locked: bool


@router.patch('/crm/chats/{chat_id}')
def lock_chat(chat_id: str, body: LockIn, store: JsonStore = Depends(get_store)):
    with store.tx('chats') as db:
        c = _find(db['chats'], chat_id, 'Suhbat topilmadi')
        c['locked'] = body.locked
    return c


class HideIn(BaseModel):
    hidden: bool
    note: str = Field('', max_length=300)


@router.patch('/crm/messages/{msg_id}')
def hide_message(msg_id: str, body: HideIn, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
    with store.tx('messages', 'chats') as db:
        m = _find(db['messages'], msg_id, 'Xabar topilmadi')
        m.update(hidden=body.hidden, moderatedBy=admin.get('username'), moderatedAt=C.now_iso())
        c = next((x for x in db['chats'] if x['id'] == m['chatId']), None)
        if c and (c.get('lastMessage') or {}).get('id') == m['id']:
            c['lastMessage']['hidden'] = body.hidden
    return {**m, 'shownAs': HIDDEN_TEXT if body.hidden else m['text']}


# ============================================================ baholar nazorati
@router.get('/crm/reviews')
def reviews(store: JsonStore = Depends(get_store)):
    db = store.read_many('reviews', 'users', 'jobs')
    names = _names(db['users'])
    jobs = {j['id']: j['title'] for j in db['jobs']}
    return [{**r, 'fromName': names.get(r['fromId'], '—'), 'toName': names.get(r['toId'], '—'), 'jobTitle': jobs.get(r.get('jobId'), '—')}
            for r in C.by_date_desc(db['reviews'])]


@router.patch('/crm/reviews/{review_id}')
def moderate_review(review_id: str, body: HideIn, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
    with store.tx('reviews') as db:
        r = _find(db['reviews'], review_id, 'Baho topilmadi')
        r.update(hidden=body.hidden, moderationNote=body.note.strip(), moderatedBy=admin.get('username'), moderatedAt=C.now_iso())
    return r
