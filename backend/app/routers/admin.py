"""TalabaGo Support (administrator) API. Har bir endpoint get_admin orqali himoyalangan."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .. import common as C
from ..config import Settings, get_settings
from ..deps import get_admin, get_store, platform_settings
from ..schemas import Attachment, HouseIn, In, JobIn, ProfileIn, Str
from ..stats import storage_info, user_totals
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


@router.get('/crm/stats/users')
def user_stats(store: JsonStore = Depends(get_store), settings: Settings = Depends(get_settings)):
    """Jami foydalanuvchilar = boshlang‘ich hisob (41, eski baza — profillari tiklanmagan) + undan keyin ro‘yxatdan o‘tganlar."""
    d = store.read_many('meta', 'users')
    return {**user_totals(d['meta'], d['users'], settings), 'storage': storage_info(settings)}


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
    # 'approved' — 'active' ning sinonimi (saqlashda 'active' bo‘lib qoladi: mavjud ma’lumotlar va ilova shu qiymatni ishlatadi)
    status: Literal['pending', 'active', 'approved', 'rejected', 'hidden', 'closed'] | None = None


# ---------------- admin qo‘shadigan e’lonlar: manba va tekshiruv
class SourceIn(In):
    type: Literal['telegram_channel', 'telegram_group', 'phone', 'other'] = 'telegram_channel'
    name: Str(120) = Field(min_length=2)          # kanal / guruh nomi yoki @username
    url: Str(300) = ''                            # e’lon havolasi (https://t.me/...)
    postedAt: Str(40) = ''                        # manbada joylangan sana (ixtiyoriy)

    @field_validator('url')
    @classmethod
    def _url(cls, v):
        if v and not v.startswith(('https://', 'http://')):
            raise ValueError('Havola https:// bilan boshlansin')
        return v


class VerificationIn(In):
    ownerContacted: bool = False   # admin e’lon egasi bilan bog‘lanib, ma’lumotlarni tasdiqlatdi
    ownerConsent: bool = False     # egasi TalabaGo’da joylashga rozi
    phoneConsent: bool = False     # egasi telefon/Telegram talabalarga ko‘rsatilishiga rozi
    method: Literal['phone', 'telegram', 'in_person', 'other'] = 'phone'
    note: Str(500) = ''


class AdminListingMeta(In):
    source: SourceIn
    verification: VerificationIn = Field(default_factory=VerificationIn)
    contactName: Str(80) = ''
    publish: bool = False          # true — darhol tasdiqlab nashr qilish (rozilik belgilangan bo‘lishi shart)


class AdminJobIn(JobIn, AdminListingMeta):
    """Admin e’loni: majburiy faqat lavozim, ish turi va manba. Qolganlari (maosh, kompaniya, tavsif, aloqa...) ixtiyoriy."""
    company: Str(120) = ''
    format: Literal[C.JOB_FORMATS] = 'offline'
    salary: int | None = Field(None, gt=0, le=1_000_000_000)
    salaryPeriod: Literal[C.SALARY_PERIODS] = 'month'
    salaryNegotiable: bool = False          # “Kelishiladi” — maosh noma’lum
    description: Str(3000) = ''
    address: Str(200) = ''

    _s = field_validator('salary', mode='before')(classmethod(lambda cls, v: None if v in ('', 0, '0') else v))

    @model_validator(mode='after')
    def _negotiable(self):
        if self.salaryNegotiable or self.salary is None:
            self.salary, self.salaryNegotiable = None, True
        return self


class AdminHouseIn(HouseIn, AdminListingMeta):
    """Admin turar joy e’loni: majburiy faqat nom, turi, tuman va manba. Narx noma’lum bo‘lsa — “Kelishiladi”."""
    photos: list[Str(300)] = Field(default_factory=list, max_length=10)   # Telegram e’lonlarida rasm bo‘lmasligi mumkin
    address: Str(200) = ''
    rooms: int = Field(1, ge=1, le=20)
    price: int | None = Field(None, gt=0, le=1_000_000_000)
    priceNegotiable: bool = False
    description: Str(3000) = ''

    _p = field_validator('price', mode='before')(classmethod(lambda cls, v: None if v in ('', 0, '0') else v))

    @model_validator(mode='after')
    def _negotiable(self):
        if self.priceNegotiable or self.price is None:
            self.price, self.priceNegotiable = None, True
        return self


def _publishable(verification: dict | None) -> bool:
    v = verification or {}
    return bool(v.get('ownerContacted') and v.get('ownerConsent'))


def _verification(v: VerificationIn | dict, admin: dict, prev: dict | None = None) -> dict:
    d = v.model_dump() if hasattr(v, 'model_dump') else dict(v)
    out = {**(prev or {}), **d}
    if d.get('ownerContacted') and not (prev or {}).get('ownerContacted'):
        out['verifiedAt'] = C.now_iso()
        out['verifiedBy'] = admin.get('username')
    return out


EDITABLE = {
    'jobs': {'title', 'company', 'salary', 'salaryPeriod', 'district', 'city', 'schedule', 'category', 'description', 'type', 'format', 'workTime', 'phone', 'telegram',
             'address', 'requirements', 'contactName', 'salaryNegotiable'},
    'houses': {'title', 'price', 'district', 'city', 'address', 'rooms', 'freeSpots', 'capacity', 'description', 'type', 'audience', 'occupancy', 'phone', 'telegram',
               'amenities', 'photos', 'area', 'contactName', 'priceNegotiable'},
}
LIST_FIELDS = {'requirements': (20, 200), 'amenities': (20, 40), 'photos': (10, 300)}
NUMERIC = {'salary', 'price', 'rooms', 'freeSpots', 'capacity'}
NEGOTIABLE = {'salary': 'salaryNegotiable', 'price': 'priceNegotiable'}   # bo‘sh qiymat → “Kelishiladi” (faqat admin e’lonida)


def _moderation(coll: str, owner_key: str, label: str, link: str):
    def _notify(db, item, icon, title, text):
        if not item.get(owner_key):          # admin qo‘shgan e’lon — xabar yuboriladigan akkaunt yo‘q
            return
        C.add_notification(db['notifications'], item[owner_key], icon, title, text, link)
        owner = next((u for u in db['users'] if u['id'] == item[owner_key]), None)
        notify_user(C.tg_chat(owner), f'<b>{title}</b>\n{esc(text)}', link)

    def _guard_publish(item):
        if C.is_admin_listing(item) and not _publishable(item.get('verification')):
            raise HTTPException(422, 'Nashr qilishdan oldin e’lon egasi bilan bog‘lanib, roziligini belgilang')

    def approve(item_id: str, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
        with store.tx(coll, 'notifications', 'users') as db:
            item = _find(db[coll], item_id)
            _guard_publish(item)
            item.update(status='active', rejectReason=None, approvedAt=C.now_iso(), updatedAt=C.now_iso(), approvedBy=admin.get('username'))
            _notify(db, item, 'check', f'{label} tasdiqlandi', item['title'])
        return item

    def reject(item_id: str, body: RejectIn, store: JsonStore = Depends(get_store)):
        with store.tx(coll, 'notifications', 'users') as db:
            item = _find(db[coll], item_id)
            item.update(status='rejected', rejectReason=body.reason, updatedAt=C.now_iso())
            _notify(db, item, 'x', f'{label} rad etildi', f'{item["title"]}: {body.reason}')
        return item

    def patch(item_id: str, body: ListingPatch, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
        data = body.model_dump(exclude_unset=True)
        if data.get('status') == 'approved':
            data['status'] = 'active'
        clean = {}
        meta = {}
        for k in ('source', 'verification'):
            if k in data:
                try:
                    meta[k] = (SourceIn if k == 'source' else VerificationIn)(**(data.pop(k) or {}))
                except ValidationError as e:
                    raise HTTPException(422, f'{k}: {e.errors()[0]["msg"]}') from e
        for k, v in data.items():
            if k == 'status' or k in EDITABLE[coll]:
                if k in LIST_FIELDS:
                    mx, ln = LIST_FIELDS[k]
                    if not isinstance(v, list) or len(v) > mx:
                        raise HTTPException(422, f'{k}: ro‘yxat noto‘g‘ri')
                    v = [str(x).strip()[:ln] for x in v if str(x).strip()]
                    if k == 'photos' and (not v or not all(C.is_media_url(p) for p in v)):
                        raise HTTPException(422, 'Rasmlar /media/ orqali yuklanishi kerak')
                elif k in ('phone',) and v:
                    v = C.normalize_phone(v)
                    if not v:
                        raise HTTPException(422, 'Telefon raqam noto‘g‘ri: +998 XX XXX XX XX')
                elif k == 'area':
                    try:
                        v = float(v) if v not in (None, '') else None
                    except (TypeError, ValueError) as e:
                        raise HTTPException(422, 'area: son kiriting') from e
                elif k in ('salaryNegotiable', 'priceNegotiable'):
                    v = bool(v)
                elif k in NEGOTIABLE and v in (None, '', 0, '0'):
                    v = None                                   # tekshiruv pastda: faqat admin e’lonida ruxsat
                elif k in NUMERIC:
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
            if 'source' in meta and C.is_admin_listing(item):
                item['source'] = meta['source'].model_dump()
            if 'verification' in meta and C.is_admin_listing(item):
                item['verification'] = _verification(meta['verification'], admin, item.get('verification'))
            if clean.get('status') == 'active':
                _guard_publish(item)
            for num, flag in NEGOTIABLE.items():
                if num not in clean and flag not in clean:
                    continue
                if not C.is_admin_listing(item):           # egasining e’lonida maosh/narx majburiy (eski qoida)
                    if clean.get(num) is None and num in clean or clean.get(flag):
                        raise HTTPException(422, f'{num}: son kiriting')
                    continue
                if clean.get(flag) or (num in clean and clean[num] is None):
                    clean[num], clean[flag] = None, True
                elif num in clean:
                    clean[flag] = False
            item.update(clean, updatedAt=C.now_iso())
            if clean.get('status') == 'active' and not item.get('approvedAt'):
                item['approvedAt'] = C.now_iso()
        return item

    def create(body: AdminJobIn, store: JsonStore = Depends(get_store), admin: dict = Depends(get_admin)):
        """Admin e’loni (ish beruvchi / uy egasi akkauntisiz) — Telegram kanal/guruhdan olingan, egasi bilan tekshirilgan."""
        payload = body.model_dump(exclude={'source', 'verification', 'contactName', 'publish'})
        if coll == 'jobs' and payload['format'] == 'online':
            payload['district'] = None
        if body.publish and not _publishable(body.verification.model_dump()):
            raise HTTPException(422, 'Darhol nashr qilish uchun egasi bilan bog‘langaningiz va uning roziligini belgilang')
        now = C.now_iso()
        item = {'id': C.new_id('j' if coll == 'jobs' else 'h'), owner_key: None, 'views': 0, **payload,
                'status': 'active' if body.publish else 'pending', 'rejectReason': None, 'approvedAt': now if body.publish else None,
                'approvedBy': admin.get('username') if body.publish else None,
                'createdBy': 'admin', 'adminId': admin['id'], 'contactName': body.contactName,
                'source': body.source.model_dump(), 'verification': _verification(body.verification, admin),
                'createdAt': now, 'updatedAt': now}
        if coll == 'houses':
            item.setdefault('occupancy', 'free')
        with store.tx(coll) as db:
            db[coll].insert(0, item)
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

    # `from __future__ import annotations` — model obyektini to‘g‘ridan-to‘g‘ri beramiz (satr emas)
    create.__annotations__['body'] = AdminJobIn if coll == 'jobs' else AdminHouseIn
    base = f'/crm/{coll}'
    router.add_api_route(base, create, methods=['POST'], status_code=201)
    router.add_api_route(base + '/{item_id}/approve', approve, methods=['POST'])
    router.add_api_route(base + '/{item_id}/reject', reject, methods=['POST'])
    router.add_api_route(base + '/{item_id}', patch, methods=['PATCH'])
    router.add_api_route(base + '/{item_id}', remove, methods=['DELETE'], status_code=204)


_moderation('jobs', 'employerId', 'Vakansiya', '/employer/new')
_moderation('houses', 'ownerId', 'Uy e’loni', '/landlord/new')


# ============================================================ admin e’lonlariga kelgan arizalar
class CrmAppStatusIn(In):
    status: Literal['viewed', 'interview', 'accepted', 'declined']
    note: Str(500) | None = None


def _crm_status(coll: str, parent: str, key: str, texts: dict, link: str):
    def handler(item_id: str, body: CrmAppStatusIn, store: JsonStore = Depends(get_store)):
        if coll == 'requests' and body.status == 'interview':
            raise HTTPException(422, 'Ijara so‘rovida bu holat yo‘q')
        with store.tx(coll, parent, 'notifications', 'users') as db:
            x = _find(db[coll], item_id)
            listing = next((i for i in db[parent] if i['id'] == x[key]), None)
            if not C.is_admin_listing(listing):
                raise HTTPException(403, 'Bu ariza e’lon egasiga tegishli — holatini faqat u o‘zgartiradi')
            if x['status'] == 'withdrawn':
                raise HTTPException(409, 'Talaba bekor qilgan')
            C.push_status(x, body.status, body.note)
            C.add_notification(db['notifications'], x['studentId'], 'x' if body.status == 'declined' else 'check', texts[body.status], listing['title'], link)
            st = next((u for u in db['users'] if u['id'] == x['studentId']), None)
        if body.status != 'viewed':
            notify_user(C.tg_chat(st), f'<b>{texts[body.status]}</b>\n{esc(listing["title"])}', link)
        return x
    return handler


router.add_api_route('/crm/applications/{item_id}', _crm_status('applications', 'jobs', 'jobId', {
    'viewed': 'Arizangiz ko‘rib chiqildi', 'interview': 'Sizni suhbatga chaqirishdi', 'accepted': 'Arizangiz qabul qilindi', 'declined': 'Arizangiz rad etildi'},
    '/student/applications'), methods=['PATCH'])
router.add_api_route('/crm/rental-requests/{item_id}', _crm_status('requests', 'houses', 'houseId', {
    'viewed': 'So‘rovingiz ko‘rildi', 'accepted': 'Ijara so‘rovingiz qabul qilindi', 'declined': 'Ijara so‘rovingiz rad etildi'},
    '/student/applications?tab=requests'), methods=['PATCH'])


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