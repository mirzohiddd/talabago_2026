"""TalabaGo Support (administrator) API. Har bir endpoint get_admin orqali himoyalangan."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .. import common as C
from ..config import Settings, get_settings
from ..deps import get_admin, get_store, platform_settings
from ..schemas import Attachment, In, ProfileIn
from ..storage import JsonStore
from ..telegram import esc, notify_user
from ..uploads import delete_media, save_upload
from .content import ad_state

router = APIRouter(prefix='', tags=['support-admin'], dependencies=[Depends(get_admin)])


def _find(items: list, item_id: str, what: str = 'Topilmadi') -> dict:
    x = next((i for i in items if i['id'] == item_id), None)
    if not x:
        raise HTTPException(404, what)
    return x


# ============================================================ ro‘yxatlar
@router.get('/crm/users')
def users(store: JsonStore = Depends(get_store)):
    return [C.public_user(u) for u in C.by_date_desc(store.read('users'))]


@router.get('/crm/jobs')
def jobs(store: JsonStore = Depends(get_store)):
    return C.by_date_desc(store.read('jobs'))


@router.get('/crm/houses')
def houses(store: JsonStore = Depends(get_store)):
    return C.by_date_desc(store.read('houses'))


@router.get('/crm/applications')
def applications(store: JsonStore = Depends(get_store)):
    return C.by_date_desc(store.read('applications'))


@router.get('/crm/rental-requests')
def rental_requests(store: JsonStore = Depends(get_store)):
    return C.by_date_desc(store.read('requests'))


@router.get('/crm/progress')
def all_progress(store: JsonStore = Depends(get_store)):
    return store.read('progress')


@router.get('/crm/complaints')
def complaints(store: JsonStore = Depends(get_store)):
    return C.by_date_desc(store.read('complaints'))


# Support paneli avtomatik yangilanishi: har bir kolleksiyaning o‘zgarish belgisi (JSON o‘qilmaydi — juda arzon).
# Panel shu endpointni tez-tez so‘raydi va faqat belgisi o‘zgargan ro‘yxatlarni qayta yuklaydi.
WATCHED = ('users', 'jobs', 'houses', 'applications', 'requests', 'courses', 'progress', 'tickets', 'complaints', 'settings', 'ads')


@router.get('/crm/changes')
def changes(store: JsonStore = Depends(get_store)):
    return {'versions': store.versions(*WATCHED), 'serverTime': C.now_iso()}


@router.get('/crm/support/tickets')
def tickets(store: JsonStore = Depends(get_store)):
    return C.by_date_desc(store.read('tickets'), 'updatedAt')


@router.get('/crm/courses')
def all_courses(store: JsonStore = Depends(get_store)):
    return store.read('courses')


# ============================================================ foydalanuvchilar
class AdminUserPatch(ProfileIn):
    status: Literal['active', 'blocked'] | None = None


@router.patch('/crm/users/{user_id}')
def patch_user(user_id: str, body: AdminUserPatch, store: JsonStore = Depends(get_store)):
    patch = body.model_dump(exclude_unset=True)
    with store.tx('users') as db:
        u = _find(db['users'], user_id, 'Foydalanuvchi topilmadi')
        if patch.get('phone') and any(C.phone_key(x.get('phone')) == C.phone_key(patch['phone']) and x['id'] != user_id for x in db['users']):
            raise HTTPException(409, 'Bu telefon raqam boshqa hisobda ishlatilgan')
        u.update(patch)
        u['updatedAt'] = C.now_iso()
    return C.public_user(u)


# ============================================================ moderatsiya
class RejectIn(In):
    reason: str = Field(min_length=3, max_length=500)


class ListingPatch(In):
    model_config = ConfigDict(extra='allow')
    status: Literal['pending', 'active', 'rejected', 'closed'] | None = None


EDITABLE = {
    'jobs': {'title', 'company', 'salary', 'salaryPeriod', 'district', 'city', 'schedule', 'category', 'description', 'type', 'format', 'workTime', 'phone', 'telegram'},
    'houses': {'title', 'price', 'district', 'city', 'address', 'rooms', 'freeSpots', 'capacity', 'description', 'type', 'audience', 'occupancy', 'phone', 'telegram'},
}
NUMERIC = {'salary', 'price', 'rooms', 'freeSpots', 'capacity'}


def _moderation(coll: str, owner_key: str, label: str, link: str):
    def _notify(db, item, icon, title, text):
        C.add_notification(db['notifications'], item[owner_key], icon, title, text, link)
        owner = next((u for u in db['users'] if u['id'] == item[owner_key]), None)
        notify_user(C.tg_chat(owner), f'<b>{title}</b>\n{esc(text)}', link)

    def approve(item_id: str, store: JsonStore = Depends(get_store)):
        with store.tx(coll, 'notifications', 'users') as db:
            item = _find(db[coll], item_id)
            item.update(status='active', rejectReason=None, approvedAt=C.now_iso(), updatedAt=C.now_iso())
            _notify(db, item, 'check', f'{label} tasdiqlandi', item['title'])
        return item

    def reject(item_id: str, body: RejectIn, store: JsonStore = Depends(get_store)):
        with store.tx(coll, 'notifications', 'users') as db:
            item = _find(db[coll], item_id)
            item.update(status='rejected', rejectReason=body.reason, updatedAt=C.now_iso())
            _notify(db, item, 'x', f'{label} rad etildi', f'{item["title"]}: {body.reason}')
        return item

    def patch(item_id: str, body: ListingPatch, store: JsonStore = Depends(get_store)):
        data = body.model_dump(exclude_unset=True)
        clean = {}
        for k, v in data.items():
            if k == 'status' or k in EDITABLE[coll]:
                if k in NUMERIC:
                    try:
                        v = int(v)
                    except (TypeError, ValueError) as e:
                        raise HTTPException(422, f'{k}: son kiriting') from e
                    if v < 0:
                        raise HTTPException(422, f'{k}: manfiy bo‘lmasin')
                elif isinstance(v, str):
                    v = v.strip()[:3000]
                clean[k] = v
        with store.tx(coll) as db:
            item = _find(db[coll], item_id)
            item.update(clean, updatedAt=C.now_iso())
            if clean.get('status') == 'active' and not item.get('approvedAt'):
                item['approvedAt'] = C.now_iso()
        return item

    def remove(item_id: str, store: JsonStore = Depends(get_store)):
        with store.tx(coll, 'saved') as db:
            item = _find(db[coll], item_id)
            db[coll] = [x for x in db[coll] if x['id'] != item_id]
            for entry in db['saved'].values():
                if item_id in entry.get(coll, []):
                    entry[coll].remove(item_id)
            others = {p for x in db[coll] for p in (x.get('photos') or [])}
        for p in set(item.get('photos') or []) - others:
            delete_media(store.media_dir, p)

    base = f'/crm/{coll}'
    router.add_api_route(base + '/{item_id}/approve', approve, methods=['POST'])
    router.add_api_route(base + '/{item_id}/reject', reject, methods=['POST'])
    router.add_api_route(base + '/{item_id}', patch, methods=['PATCH'])
    router.add_api_route(base + '/{item_id}', remove, methods=['DELETE'], status_code=204)


_moderation('jobs', 'employerId', 'Vakansiya', '/employer/new')
_moderation('houses', 'ownerId', 'Uy e’loni', '/landlord/new')


# ============================================================ kurslar
class QuizQ(BaseModel):
    q: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0, le=5)


class LessonModel(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=2, max_length=160)
    summary: str = Field('', max_length=300)
    status: Literal['draft', 'published'] = 'draft'
    order: int = 0
    durationMin: int = Field(10, ge=1, le=300)
    video: dict | None = None
    text: str = Field('', max_length=20000)
    vocab: list[dict] = Field(default_factory=list, max_length=200)
    translations: list[dict] = Field(default_factory=list, max_length=200)
    quiz: list[QuizQ] = Field(default_factory=list, max_length=20)

    @field_validator('video')
    @classmethod
    def _v(cls, v):
        if v and not C.is_media_url(v.get('url')):
            raise ValueError('Video /media/ orqali yuklanishi kerak')
        return v


class CourseModel(BaseModel):
    model_config = ConfigDict(extra='ignore')
    title: str = Field(min_length=2, max_length=120)
    subtitle: str = Field('', max_length=200)
    description: str = Field('', max_length=2000)
    level: str = Field('', max_length=40)
    status: Literal['draft', 'published'] = 'published'
    lessons: list[LessonModel] = Field(default_factory=list, max_length=200)


@router.put('/crm/courses/{course_id}')
def save_course(course_id: str, body: CourseModel, store: JsonStore = Depends(get_store)):
    ids = [l.id for l in body.lessons]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, 'Dars ID’lari takrorlanmasin')
    with store.tx('courses') as db:
        c = _find(db['courses'], course_id, 'Kurs topilmadi')
        lessons = []
        for i, l in enumerate(body.lessons):
            d = l.model_dump()
            d['order'] = i + 1
            lessons.append(d)
        c.update(body.model_dump(exclude={'lessons'}), lessons=lessons, updatedAt=C.now_iso())
    return c


# ============================================================ support
class ReplyIn(In):
    text: str = Field('', max_length=4000)
    attachment: Attachment | None = None
    status: Literal['in_review', 'answered', 'resolved'] = 'answered'


class TicketPatch(In):
    status: Literal['new', 'in_review', 'answered', 'resolved']


@router.post('/crm/support/tickets/{ticket_id}/messages')
def reply(ticket_id: str, body: ReplyIn, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
    if not body.text.strip() and not body.attachment:
        raise HTTPException(422, 'Xabar bo‘sh')
    at = C.now_iso()
    with store.tx('tickets', 'notifications', 'users') as db:
        t = _find(db['tickets'], ticket_id, 'Murojaat topilmadi')
        t['messages'].append({'id': C.new_id('m'), 'from': 'support', 'text': body.text.strip(), 'at': at, 'author': admin.get('name') or admin['username'],
                              'attachment': body.attachment.model_dump() if body.attachment else None})
        t.update(status=body.status, updatedAt=at, unreadByUser=(t.get('unreadByUser') or 0) + 1, unreadBySupport=0)
        C.add_notification(db['notifications'], t['userId'], 'life', 'Support javob berdi', f'“{t["subject"]}” murojaatingizga javob keldi.', f'/{t["role"]}/support/{t["id"]}')
        u = next((x for x in db['users'] if x['id'] == t['userId']), None)
    notify_user(C.tg_chat(u), f'💬 <b>TalabaGo Support javob berdi</b>\n{esc(t["subject"])}\n\n{esc(body.text[:500])}', f'/{t["role"]}/support/{t["id"]}')
    return t


@router.patch('/crm/support/tickets/{ticket_id}')
def ticket_status(ticket_id: str, body: TicketPatch, store: JsonStore = Depends(get_store)):
    at = C.now_iso()
    text = {'resolved': 'Murojaat hal qilindi deb yopildi.', 'in_review': 'Murojaat qayta ochildi.'}.get(body.status)
    with store.tx('tickets') as db:
        t = _find(db['tickets'], ticket_id, 'Murojaat topilmadi')
        if text and t['status'] != body.status:
            t['messages'].append({'id': C.new_id('m'), 'from': 'system', 'text': text, 'at': at})
        t.update(status=body.status, updatedAt=at)
    return t


@router.post('/crm/support/tickets/{ticket_id}/read', status_code=204)
def ticket_read(ticket_id: str, store: JsonStore = Depends(get_store)):
    with store.tx('tickets') as db:
        _find(db['tickets'], ticket_id)['unreadBySupport'] = 0


# ============================================================ shikoyatlar
class ComplaintPatch(In):
    status: Literal['new', 'in_review', 'resolved', 'dismissed'] | None = None
    note: str | None = Field(None, max_length=1000)
    priority: Literal['high', 'medium', 'low'] | None = None


@router.patch('/crm/complaints/{item_id}')
def patch_complaint(item_id: str, body: ComplaintPatch, store: JsonStore = Depends(get_store)):
    with store.tx('complaints') as db:
        c = _find(db['complaints'], item_id, 'Shikoyat topilmadi')
        if body.status:
            c['status'] = body.status
        if body.priority:
            c['priority'] = body.priority
        if body.note and body.note.strip():
            c.setdefault('notes', []).append({'at': C.now_iso(), 'text': body.note.strip()})
        c['updatedAt'] = C.now_iso()
    return c


# ============================================================ sozlamalar
class SettingsIn(In):
    profile: dict = Field(default_factory=dict)
    platform: dict = Field(default_factory=dict)
    notifications: dict = Field(default_factory=dict)
    system: dict = Field(default_factory=dict)


DEFAULT_SETTINGS = {
    'profile': {'name': '', 'email': '', 'avatar': None},
    'platform': {'name': 'TalabaGo', 'logo': None},
    'notifications': {'newTicket': True, 'newListing': True, 'newComplaint': True, 'dailyDigest': False},
    'system': {'maintenance': False, 'registrationOpen': True, 'moderation': True, 'adsEnabled': True},
}


@router.get('/crm/settings')
def get_settings_(store: JsonStore = Depends(get_store)):
    s = platform_settings(store)
    return {k: {**v, **(s.get(k) or {})} for k, v in DEFAULT_SETTINGS.items()}


@router.put('/crm/settings')
def put_settings(body: SettingsIn, store: JsonStore = Depends(get_store)):
    out = {}
    for sec, defaults in DEFAULT_SETTINGS.items():
        src = getattr(body, sec) or {}
        sec_out = {}
        for k, dv in defaults.items():
            v = src.get(k, dv)
            if isinstance(dv, bool):
                v = bool(v)
            elif k in ('logo', 'avatar'):
                v = v if (v is None or C.is_media_url(v)) else None
            else:
                v = str(v or '')[:120]
            sec_out[k] = v
        out[sec] = sec_out
    if not out['platform']['name'].strip():
        raise HTTPException(422, 'Platforma nomi bo‘sh bo‘lmasin')
    with store.tx('settings') as db:
        db['settings'].clear()
        db['settings'].update(out)
    return out


# ============================================================ fayllar
@router.post('/crm/files', status_code=201)
async def admin_upload(file: UploadFile = File(...), kind: str = Form('file'), settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    if kind not in ('lesson', 'shot', 'logo', 'ad', 'photo', 'file'):
        raise HTTPException(400, 'Noto‘g‘ri fayl turi')
    return await save_upload(file, kind, store.media_dir, settings)


# ============================================================ reklamalar
class AdIn(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    type: Literal['image', 'video']
    title: str = Field('', max_length=80)
    description: str = Field('', max_length=160)
    link: str = Field('', max_length=500)
    placements: list[str] = Field(min_length=1, max_length=30)
    startAt: str
    endAt: str
    enabled: bool = True
    order: int | None = Field(None, ge=1, le=999)
    mediaMeta: dict = Field(default_factory=dict)

    @field_validator('link')
    @classmethod
    def _link(cls, v):
        if v and not v.startswith(('https://', 'http://')):
            raise ValueError('Havola http(s):// bilan boshlansin')
        return v

    @field_validator('placements')
    @classmethod
    def _pl(cls, v):
        if not all(isinstance(p, str) and (p == 'all' or p.startswith('/')) and len(p) < 80 for p in v):
            raise ValueError('Joylashuv noto‘g‘ri')
        return v


def _parse_ad(data: str) -> AdIn:
    try:
        ad = AdIn(**json.loads(data))
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(422, f'Reklama ma’lumotlari noto‘g‘ri: {e}') from e
    from .content import _parse
    s, e = _parse(ad.startAt), _parse(ad.endAt)
    if not s or not e or e <= s:
        raise HTTPException(422, 'Tugash vaqti boshlanishdan keyin bo‘lsin')
    return ad


def _reorder(ads: list, ad_id: str, position: int | None) -> None:
    rest = sorted([a for a in ads if a['id'] != ad_id], key=lambda a: (a.get('order') or 999, a.get('createdAt') or ''))
    me = next(a for a in ads if a['id'] == ad_id)
    idx = min(max(1, position or len(rest) + 1), len(rest) + 1) - 1
    rest.insert(idx, me)
    for k, a in enumerate(rest):
        a['order'] = k + 1


async def _ad_media(file: UploadFile, poster: UploadFile | None, ad: AdIn, settings, store) -> dict:
    saved = await save_upload(file, 'ad', store.media_dir, settings)
    is_video = saved['mime'].startswith('video/')
    if is_video != (ad.type == 'video'):
        delete_media(store.media_dir, saved['url'])
        raise HTTPException(422, 'Fayl turi reklama turiga mos emas')
    media = {'src': saved['url'], 'mime': saved['mime'], 'name': saved['name'], 'size': saved['size'],
             'width': saved.get('width') or ad.mediaMeta.get('width'), 'height': saved.get('height') or ad.mediaMeta.get('height'),
             'duration': ad.mediaMeta.get('duration') if is_video else None, 'posterSrc': None}
    if poster is not None and is_video:
        p = await save_upload(poster, 'ad', store.media_dir, settings)
        media['posterSrc'] = p['url']
    return media


@router.get('/ads')
def list_ads(store: JsonStore = Depends(get_store)):
    ads = sorted(store.read('ads'), key=lambda a: (a.get('order') or 999, a.get('createdAt') or ''))
    return [{**a, 'views': a.get('views') or 0, 'clicks': a.get('clicks') or 0, 'state': ad_state(a)} for a in ads]


class OrderIn(In):
    ids: list[str] = Field(max_length=500)


@router.patch('/ads/order')
def order_ads(body: OrderIn, store: JsonStore = Depends(get_store)):
    ids = body.ids
    with store.tx('ads') as db:
        known = {a['id']: a for a in db['ads']}
        if set(ids) != set(known):
            raise HTTPException(422, 'Ro‘yxat to‘liq emas')
        for k, i in enumerate(ids):
            known[i]['order'] = k + 1
    return {'ok': True}


@router.post('/ads', status_code=201)
async def create_ad(data: str = Form(...), file: UploadFile = File(...), poster: UploadFile | None = File(None),
                    settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    ad_in = _parse_ad(data)
    media = await _ad_media(file, poster, ad_in, settings, store)
    now = C.now_iso()
    ad = {'id': C.new_id('ad'), **ad_in.model_dump(exclude={'mediaMeta', 'order'}), 'media': media, 'views': 0, 'clicks': 0, 'createdAt': now, 'updatedAt': now}
    with store.tx('ads') as db:
        db['ads'].append(ad)
        _reorder(db['ads'], ad['id'], ad_in.order)
    return {**ad, 'state': ad_state(ad)}


@router.patch('/ads/{ad_id}')
async def update_ad(ad_id: str, data: str = Form(...), file: UploadFile | None = File(None), poster: UploadFile | None = File(None),
                    settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    ad_in = _parse_ad(data)
    media = await _ad_media(file, poster, ad_in, settings, store) if file is not None else None
    with store.tx('ads') as db:
        ad = _find(db['ads'], ad_id, 'Reklama topilmadi')
        old = ad.get('media') if media else None
        ad.update(ad_in.model_dump(exclude={'mediaMeta', 'order'}), updatedAt=C.now_iso())
        if media:
            ad['media'] = media
        if ad_in.order:
            _reorder(db['ads'], ad_id, ad_in.order)
    if old:
        delete_media(store.media_dir, old.get('src'))
        delete_media(store.media_dir, old.get('posterSrc'))
    return ad


class EnabledIn(In):
    enabled: bool


@router.patch('/ads/{ad_id}/enabled')
def ad_enabled(ad_id: str, body: EnabledIn, store: JsonStore = Depends(get_store)):
    with store.tx('ads') as db:
        ad = _find(db['ads'], ad_id, 'Reklama topilmadi')
        ad.update(enabled=body.enabled, updatedAt=C.now_iso())
    return ad


@router.delete('/ads/{ad_id}', status_code=204)
def delete_ad(ad_id: str, store: JsonStore = Depends(get_store)):
    with store.tx('ads') as db:
        ad = _find(db['ads'], ad_id, 'Reklama topilmadi')
        db['ads'] = [a for a in db['ads'] if a['id'] != ad_id]
        for k, a in enumerate(sorted(db['ads'], key=lambda a: a.get('order') or 999)):
            a['order'] = k + 1
    delete_media(store.media_dir, (ad.get('media') or {}).get('src'))
    delete_media(store.media_dir, (ad.get('media') or {}).get('posterSrc'))