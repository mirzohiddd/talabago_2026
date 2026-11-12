"""Ish va uy e’lonlari, arizalar, ijara so‘rovlari, saqlanganlar."""

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import common as C
from .. import ratelimit
from ..deps import get_current_user, get_store, platform_settings, require_role
from ..schemas import ActiveIn, AppStatusIn, ApplyIn, HouseIn, JobIn, OccupancyIn, ReqStatusIn, RentRequestIn
from ..storage import JsonStore
from ..telegram import esc, notify_admins, notify_user
from ..uploads import delete_media

router = APIRouter(tags=['listings'])
student = require_role('student')
employer = require_role('employer')
landlord = require_role('landlord')

KIND = {
    'job': {'coll': 'jobs', 'owner': 'employerId', 'prefix': 'j', 'related': 'applications', 'rel_key': 'jobId', 'saved': 'jobs', 'label': 'Vakansiya'},
    'house': {'coll': 'houses', 'owner': 'ownerId', 'prefix': 'h', 'related': 'requests', 'rel_key': 'houseId', 'saved': 'houses', 'label': 'Uy e’loni'},
}


def _truthy(v) -> bool:
    return str(v).lower() in ('1', 'true', 'yes', 'on')


def _saved(store: JsonStore, user_id: str, key: str) -> list[str]:
    return list((store.peek('saved')['saved'].get(user_id) or {}).get(key, []))  # nusxa — kesh o‘zgarmaydi


def _initial_status(store: JsonStore) -> tuple[str, str | None]:
    if platform_settings(store)['system']['moderation']:
        return 'pending', None
    return 'active', C.now_iso()


# ============================================================ ommaviy ro‘yxatlar
@router.get('/jobs')
def list_jobs(request: Request, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    f = dict(request.query_params)
    db = store.peek('jobs', 'applications')  # faqat o‘qiladi — javob yangi dict’lardan
    blocked = _blocked(store)
    saved = set(_saved(store, user['id'], 'jobs'))
    applied = {a['jobId'] for a in db['applications'] if a['studentId'] == user['id'] and a['status'] != 'withdrawn'}
    salary_min = C.SALARY_MIN.get(f.get('salary', ''), 0)
    work_time = f.get('workTime') or f.get('work_time')
    out = []
    for j in db['jobs']:
        if j['status'] != 'active' or j['employerId'] in blocked:
            continue
        if any(f.get(k) not in (None, '', 'all') and j.get(k) != f[k] for k in ('type', 'format', 'city', 'district')):
            continue
        if work_time not in (None, '', 'all') and j.get('workTime') != work_time:
            continue
        if salary_min and C.monthly_estimate(j) < salary_min:
            continue
        if _truthy(f.get('saved')) and j['id'] not in saved:
            continue
        if not C.matches(j, f.get('q'), ['title', 'company', 'category', 'district', 'city']):
            continue
        out.append({**C.public_listing(j), 'saved': j['id'] in saved, 'applied': j['id'] in applied})
    return C.by_date_desc(out)


def _blocked(store: JsonStore) -> frozenset:
    """Bloklangan foydalanuvchilar ID’lari — users.json o‘zgarguncha keshlanadi (har so‘rovda butun ro‘yxat nusxalanmaydi)"""
    return store.derived('users', 'blocked', lambda us: frozenset(C.blocked_ids(us)))


def _owner_card(u: dict | None) -> dict | None:
    return {'id': u['id'], 'name': C.full_name(u), 'phone': u.get('phone'), 'telegram': u.get('telegram')} if u else None


def _house_owner(store: JsonStore, h: dict) -> dict | None:
    return C.listing_owner_card(h, store.get('users', h['ownerId']) if h.get('ownerId') else None)


@router.get('/houses')
def list_houses(request: Request, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    f = dict(request.query_params)
    db = store.peek('houses', 'requests')
    blocked = _blocked(store)
    owners: dict[str, dict | None] = {}
    saved = set(_saved(store, user['id'], 'houses'))
    requested = {r['houseId'] for r in db['requests'] if r['studentId'] == user['id'] and r['status'] != 'withdrawn'}
    pmax = C.PRICE_MAX.get(f.get('price', ''))
    rooms = f.get('rooms')
    only_free = _truthy(f.get('onlyFree') or f.get('only_free'))
    out = []
    for h in db['houses']:
        if h['status'] != 'active' or h['ownerId'] in blocked:
            continue
        if any(f.get(k) not in (None, '', 'all') and h.get(k) != f[k] for k in ('type', 'district', 'city')):
            continue
        if pmax and h['price'] > pmax:
            continue
        if rooms not in (None, '', 'all') and not (h['rooms'] >= 3 if rooms == '3' else str(h['rooms']) == rooms):
            continue
        aud = f.get('audience')
        if aud not in (None, '', 'all') and h.get('audience') not in ('any', aud):
            continue
        if only_free and not (h.get('occupancy') == 'free' and (h.get('freeSpots') or 0) > 0):
            continue
        if _truthy(f.get('saved')) and h['id'] not in saved:
            continue
        if not C.matches(h, f.get('q'), ['title', 'district', 'address', 'city']):
            continue
        if C.is_admin_listing(h):
            owner = _house_owner(store, h)
        else:
            if h['ownerId'] not in owners:
                owners[h['ownerId']] = _owner_card(store.get('users', h['ownerId']))
            owner = owners[h['ownerId']]
        out.append({**C.public_listing(h), 'owner': owner, 'saved': h['id'] in saved, 'requested': h['id'] in requested})
    return C.by_date_desc(out)


def _get_visible(store: JsonStore, kind: str, item_id: str, user: dict) -> dict:
    k = KIND[kind]
    item = store.get(k['coll'], item_id)
    hidden = item and item[k['owner']] in _blocked(store)
    mine = bool(item) and item.get(k['owner']) is not None and item[k['owner']] == user['id']
    if not item or ((item['status'] != 'active' or hidden) and not mine):
        raise HTTPException(404, 'E’lon topilmadi')
    return item if mine else C.public_listing(item)


@router.get('/jobs/{item_id}')
def get_job(item_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    return _get_visible(store, 'job', item_id, user)


@router.get('/houses/{item_id}')
def get_house(item_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    h = _get_visible(store, 'house', item_id, user)
    return {**h, 'owner': _house_owner(store, store.get('houses', item_id) or h)}


def _view(kind: str):
    def handler(item_id: str, request: Request, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
        k = KIND[kind]
        if ratelimit.hit(f'view:{kind}:{item_id}:{user["id"]}', 1, 3600):
            return {'ok': True}
        with store.tx(k['coll']) as db:
            item = next((x for x in db[k['coll']] if x['id'] == item_id), None)
            if item and item['status'] == 'active' and item[k['owner']] != user['id']:
                item['views'] = (item.get('views') or 0) + 1
        return {'ok': True}
    return handler


router.add_api_route('/jobs/{item_id}/view', _view('job'), methods=['POST'])
router.add_api_route('/houses/{item_id}/view', _view('house'), methods=['POST'])


def _toggle_save(kind: str):
    def handler(item_id: str, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
        k = KIND[kind]
        _get_visible(store, kind, item_id, user)
        with store.tx('saved') as db:
            entry = db['saved'].setdefault(user['id'], {'jobs': [], 'houses': []})
            lst = entry.setdefault(k['saved'], [])
            if item_id in lst:
                lst.remove(item_id)
                return False
            lst.append(item_id)
            return True
    return handler


router.add_api_route('/jobs/{item_id}/save', _toggle_save('job'), methods=['POST'])
router.add_api_route('/houses/{item_id}/save', _toggle_save('house'), methods=['POST'])


# ============================================================ egasi uchun (CRUD)
def _mine(kind: str, role_dep):
    k = KIND[kind]

    def list_mine(request: Request, user: dict = Depends(role_dep), store: JsonStore = Depends(get_store)):
        f = dict(request.query_params)
        db = store.read_many(k['coll'], k['related'])
        counts: dict[str, int] = {}
        for r in db[k['related']]:
            if r['status'] != 'withdrawn':
                counts[r[k['rel_key']]] = counts.get(r[k['rel_key']], 0) + 1
        items = [x for x in db[k['coll']] if x[k['owner']] == user['id']
                 and f.get('status') in (None, '', 'all', x['status'])
                 and C.matches(x, f.get('q'), ['title', 'district', 'category', 'address'])]
        cnt_key = 'applicationsCount' if kind == 'job' else 'requestsCount'
        return [{**x, cnt_key: counts.get(x['id'], 0)} for x in C.by_date_desc(items)]

    def create(body: JobIn if kind == 'job' else HouseIn, user: dict = Depends(role_dep), store: JsonStore = Depends(get_store)):
        payload = body.model_dump()
        if kind == 'job' and payload['format'] == 'online':
            payload['district'] = None
        status, approved = _initial_status(store)
        now = C.now_iso()
        item = {'id': C.new_id(k['prefix']), k['owner']: user['id'], 'views': 0, **payload, 'status': status, 'rejectReason': None,
                'approvedAt': approved, 'createdAt': now, 'updatedAt': now}
        if kind == 'house':
            item.setdefault('occupancy', 'free')
        with store.tx(k['coll']) as db:
            db[k['coll']].insert(0, item)
        if status == 'pending':
            notify_admins(f'🆕 <b>{k["label"]} tekshiruvda</b>\n{esc(item["title"])} — {esc(C.full_name(user))}', f'/{k["coll"]}?status=pending')
        return item

    def _own(db, item_id, user):
        item = next((x for x in db[k['coll']] if x['id'] == item_id), None)
        if not item or item[k['owner']] != user['id']:
            raise HTTPException(404, 'E’lon topilmadi')
        return item

    def update(item_id: str, body: JobIn if kind == 'job' else HouseIn, user: dict = Depends(role_dep), store: JsonStore = Depends(get_store)):
        payload = body.model_dump()
        if kind == 'job' and payload['format'] == 'online':
            payload['district'] = None
        status, approved = _initial_status(store)
        with store.tx(k['coll']) as db:
            item = _own(db, item_id, user)
            old_photos = set(item.get('photos') or [])
            item.update(payload, rejectReason=None, updatedAt=C.now_iso())
            if item['status'] not in ('closed', 'hidden'):
                item['status'] = status
                item['approvedAt'] = approved or item.get('approvedAt')
            others = {p for x in db[k['coll']] if x['id'] != item_id for p in (x.get('photos') or [])}
        for p in old_photos - set(item.get('photos') or []) - others:
            delete_media(store.media_dir, p)
        return item

    def duplicate(item_id: str, user: dict = Depends(role_dep), store: JsonStore = Depends(get_store)):
        now = C.now_iso()
        status, approved = _initial_status(store)
        with store.tx(k['coll']) as db:
            src = _own(db, item_id, user)
            copy = {**src, 'id': C.new_id(k['prefix']), 'title': f'{src["title"]} (nusxa)'[:120], 'status': status, 'rejectReason': None,
                    'views': 0, 'approvedAt': approved, 'createdAt': now, 'updatedAt': now}
            db[k['coll']].insert(0, copy)
        if status == 'pending':
            notify_admins(f'🆕 <b>{k["label"]} tekshiruvda</b>\n{esc(copy["title"])} — {esc(C.full_name(user))}', f'/{k["coll"]}?status=pending')
        return copy

    def set_active(item_id: str, body: ActiveIn, user: dict = Depends(role_dep), store: JsonStore = Depends(get_store)):
        with store.tx(k['coll']) as db:
            item = _own(db, item_id, user)
            if item['status'] == 'hidden':
                raise HTTPException(409, 'E’lon administrator tomonidan yashirilgan. Support bilan bog‘laning')
            if body.active:
                if item['status'] == 'closed':
                    item['status'] = 'active' if item.get('approvedAt') else 'pending'
            else:
                item['status'] = 'closed'
            item['updatedAt'] = C.now_iso()
        return item

    def remove(item_id: str, user: dict = Depends(role_dep), store: JsonStore = Depends(get_store)):
        with store.tx(k['coll'], 'saved') as db:
            item = _own(db, item_id, user)
            db[k['coll']] = [x for x in db[k['coll']] if x['id'] != item_id]
            for entry in db['saved'].values():
                if item_id in entry.get(k['saved'], []):
                    entry[k['saved']].remove(item_id)
            others = {p for x in db[k['coll']] for p in (x.get('photos') or [])}
        for p in set(item.get('photos') or []) - others:
            delete_media(store.media_dir, p)

    base = '/employer/jobs' if kind == 'job' else '/landlord/houses'
    router.add_api_route(base, list_mine, methods=['GET'])
    router.add_api_route(base, create, methods=['POST'], status_code=201)
    router.add_api_route(base + '/{item_id}', update, methods=['PATCH'])
    router.add_api_route(base + '/{item_id}/duplicate', duplicate, methods=['POST'], status_code=201)
    router.add_api_route(base + '/{item_id}/active', set_active, methods=['PATCH'])
    router.add_api_route(base + '/{item_id}', remove, methods=['DELETE'], status_code=204)


_mine('job', employer)
_mine('house', landlord)


@router.patch('/landlord/houses/{item_id}/occupancy')
def set_occupancy(item_id: str, body: OccupancyIn, user: dict = Depends(landlord), store: JsonStore = Depends(get_store)):
    with store.tx('houses') as db:
        h = next((x for x in db['houses'] if x['id'] == item_id and x['ownerId'] == user['id']), None)
        if not h:
            raise HTTPException(404, 'E’lon topilmadi')
        h['occupancy'] = body.occupancy
        h['updatedAt'] = C.now_iso()
    return h


# ============================================================ ariza / so‘rov yuborish
@router.post('/jobs/{job_id}/apply', status_code=201, dependencies=[Depends(ratelimit.limit('apply', 30, 3600))])
def apply(job_id: str, body: ApplyIn, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    at = C.now_iso()
    with store.tx('jobs', 'applications', 'notifications', 'users') as db:
        job = next((j for j in db['jobs'] if j['id'] == job_id and j['status'] == 'active'), None)
        if not job or job['employerId'] in C.blocked_ids(db['users']):
            raise HTTPException(404, 'Vakansiya topilmadi yoki yopilgan')
        if any(a['jobId'] == job_id and a['studentId'] == user['id'] and a['status'] != 'withdrawn' for a in db['applications']):
            raise HTTPException(409, 'Siz bu vakansiyaga ariza yuborgansiz')
        app = {'id': C.new_id('a'), 'jobId': job_id, 'studentId': user['id'], 'message': body.message, 'status': 'sent',
               'history': [{'status': 'sent', 'at': at}], 'createdAt': at, 'updatedAt': at}
        db['applications'].insert(0, app)
        owner = next((u for u in db['users'] if u['id'] == job['employerId']), None) if job.get('employerId') else None
        if owner:
            C.add_notification(db['notifications'], job['employerId'], 'user', 'Yangi ariza', f'{C.full_name(user)} → {job["title"]}', '/employer/applications')
    if owner:
        notify_user(C.tg_chat(owner), f'📩 <b>Yangi ariza</b>\n{esc(C.full_name(user))} → {esc(job["title"])}', '/employer/applications')
    elif C.is_admin_listing(job):  # Support qo‘shgan e’lon — arizani Support ko‘radi
        notify_admins(f'📩 <b>Admin e’loniga ariza</b>\n{esc(C.full_name(user))} → {esc(job["title"])}', f'/applications?id={app["id"]}')
    return app


@router.post('/houses/{house_id}/requests', status_code=201, dependencies=[Depends(ratelimit.limit('rent', 30, 3600))])
def rent_request(house_id: str, body: RentRequestIn, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    at = C.now_iso()
    with store.tx('houses', 'requests', 'notifications', 'users') as db:
        h = next((x for x in db['houses'] if x['id'] == house_id and x['status'] == 'active'), None)
        if not h or h['ownerId'] in C.blocked_ids(db['users']):
            raise HTTPException(404, 'E’lon topilmadi yoki yopilgan')
        if any(r['houseId'] == house_id and r['studentId'] == user['id'] and r['status'] != 'withdrawn' for r in db['requests']):
            raise HTTPException(409, 'Siz bu uyga so‘rov yuborgansiz')
        req = {'id': C.new_id('r'), 'houseId': house_id, 'studentId': user['id'], 'message': body.message, 'moveIn': body.moveIn,
               'term': body.term, 'status': 'sent', 'history': [{'status': 'sent', 'at': at}], 'createdAt': at, 'updatedAt': at}
        db['requests'].insert(0, req)
        owner = next((u for u in db['users'] if u['id'] == h['ownerId']), None) if h.get('ownerId') else None
        if owner:
            C.add_notification(db['notifications'], h['ownerId'], 'inbox', 'Yangi so‘rov', f'{C.full_name(user)} → {h["title"]}', '/landlord/requests')
    if owner:
        notify_user(C.tg_chat(owner), f'🏠 <b>Yangi ijara so‘rovi</b>\n{esc(C.full_name(user))} → {esc(h["title"])}', '/landlord/requests')
    elif C.is_admin_listing(h):
        notify_admins(f'🏠 <b>Admin e’loniga ijara so‘rovi</b>\n{esc(C.full_name(user))} → {esc(h["title"])}', f'/applications?tab=requests&id={req["id"]}')
    return req


# ============================================================ talabaning arizalari
@router.get('/me/applications')
def my_applications(user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    db = store.read_many('applications', 'jobs')
    jobs = {j['id']: j for j in db['jobs']}
    return [{**a, 'job': C.public_listing(jobs[a['jobId']]) if a['jobId'] in jobs else None} for a in C.by_date_desc([a for a in db['applications'] if a['studentId'] == user['id']])]


@router.get('/me/rental-requests')
def my_requests(user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    db = store.read_many('requests', 'houses')
    houses = {h['id']: h for h in db['houses']}
    return [{**r, 'house': C.public_listing(houses[r['houseId']]) if r['houseId'] in houses else None} for r in C.by_date_desc([r for r in db['requests'] if r['studentId'] == user['id']])]


def _withdraw(coll: str):
    def handler(item_id: str, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
        with store.tx(coll) as db:
            x = next((a for a in db[coll] if a['id'] == item_id and a['studentId'] == user['id']), None)
            if not x:
                raise HTTPException(404, 'Topilmadi')
            if x['status'] in ('accepted', 'declined', 'withdrawn'):
                raise HTTPException(409, 'Bu holatda bekor qilib bo‘lmaydi')
            C.push_status(x, 'withdrawn')
        return x
    return handler


router.add_api_route('/me/applications/{item_id}/withdraw', _withdraw('applications'), methods=['POST'])
router.add_api_route('/me/rental-requests/{item_id}/withdraw', _withdraw('requests'), methods=['POST'])


# ============================================================ kelgan arizalar / so‘rovlar
@router.get('/employer/applications')
def employer_apps(request: Request, user: dict = Depends(employer), store: JsonStore = Depends(get_store)):
    f = dict(request.query_params)
    db = store.read_many('applications', 'jobs', 'users')
    jobs = {j['id']: j for j in db['jobs'] if j['employerId'] == user['id']}
    users = {u['id']: u for u in db['users']}
    out = []
    for a in db['applications']:
        if a['jobId'] not in jobs or a['status'] == 'withdrawn':
            continue
        if f.get('status') not in (None, '', 'all', a['status']) or f.get('job_id') not in (None, '', 'all', a['jobId']):
            continue
        card = C.student_card(users.get(a['studentId']))
        row = {**a, 'job': jobs[a['jobId']], 'student': card}
        if not C.matches({'n': (card or {}).get('name'), 'u': (card or {}).get('university'), 'j': jobs[a['jobId']]['title']}, f.get('q'), ['n', 'u', 'j']):
            continue
        out.append(row)
    return C.by_date_desc(out)


@router.get('/landlord/requests')
def landlord_requests(request: Request, user: dict = Depends(landlord), store: JsonStore = Depends(get_store)):
    f = dict(request.query_params)
    db = store.read_many('requests', 'houses', 'users')
    houses = {h['id']: h for h in db['houses'] if h['ownerId'] == user['id']}
    users = {u['id']: u for u in db['users']}
    out = []
    for r in db['requests']:
        if r['houseId'] not in houses or r['status'] == 'withdrawn':
            continue
        if f.get('status') not in (None, '', 'all', r['status']) or f.get('house_id') not in (None, '', 'all', r['houseId']):
            continue
        card = C.student_card(users.get(r['studentId']))
        if not C.matches({'n': (card or {}).get('name'), 'u': (card or {}).get('university'), 'h': houses[r['houseId']]['title']}, f.get('q'), ['n', 'u', 'h']):
            continue
        out.append({**r, 'house': houses[r['houseId']], 'student': card})
    return C.by_date_desc(out)


APP_TEXT = {'viewed': 'Arizangiz ko‘rib chiqildi', 'interview': 'Sizni suhbatga chaqirishdi', 'accepted': 'Arizangiz qabul qilindi', 'declined': 'Arizangiz rad etildi'}
REQ_TEXT = {'viewed': 'So‘rovingiz ko‘rildi', 'accepted': 'Ijara so‘rovingiz qabul qilindi', 'declined': 'Ijara so‘rovingiz rad etildi'}


@router.patch('/employer/applications/{item_id}')
def set_app_status(item_id: str, body: AppStatusIn, user: dict = Depends(employer), store: JsonStore = Depends(get_store)):
    with store.tx('applications', 'jobs', 'notifications', 'users') as db:
        a = next((x for x in db['applications'] if x['id'] == item_id), None)
        job = a and next((j for j in db['jobs'] if j['id'] == a['jobId']), None)
        if not a or not job or job['employerId'] != user['id'] or a['status'] == 'withdrawn':
            raise HTTPException(404, 'Ariza topilmadi')
        if body.status == 'interview' and not body.interviewAt:
            raise HTTPException(422, 'Suhbat vaqtini kiriting')
        if a['status'] == body.status and body.status == 'viewed':
            return a
        extra = {'interviewAt': body.interviewAt} if body.interviewAt else {}
        C.push_status(a, body.status, body.note, **extra)
        C.add_notification(db['notifications'], a['studentId'], 'x' if body.status == 'declined' else 'check', APP_TEXT[body.status], job['title'], '/student/applications')
        st = next((u for u in db['users'] if u['id'] == a['studentId']), None)
    if body.status != 'viewed':
        notify_user(C.tg_chat(st), f'💼 <b>{APP_TEXT[body.status]}</b>\n{esc(job["title"])}', '/student/applications')
    return a


@router.patch('/landlord/requests/{item_id}')
def set_req_status(item_id: str, body: ReqStatusIn, user: dict = Depends(landlord), store: JsonStore = Depends(get_store)):
    with store.tx('requests', 'houses', 'notifications', 'users') as db:
        r = next((x for x in db['requests'] if x['id'] == item_id), None)
        h = r and next((x for x in db['houses'] if x['id'] == r['houseId']), None)
        if not r or not h or h['ownerId'] != user['id'] or r['status'] == 'withdrawn':
            raise HTTPException(404, 'So‘rov topilmadi')
        if r['status'] == body.status and body.status == 'viewed':
            return r
        C.push_status(r, body.status, body.note)
        C.add_notification(db['notifications'], r['studentId'], 'x' if body.status == 'declined' else 'home', REQ_TEXT[body.status], h['title'], '/student/applications?tab=requests')
        st = next((u for u in db['users'] if u['id'] == r['studentId']), None)
    if body.status != 'viewed':
        notify_user(C.tg_chat(st), f'🏠 <b>{REQ_TEXT[body.status]}</b>\n{esc(h["title"])}', '/student/applications?tab=requests')
    return r