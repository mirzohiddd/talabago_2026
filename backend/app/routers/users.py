"""Joriy foydalanuvchi profili, nomzod profili, bildirishnomalar, shikoyatlar, fayl yuklash, ommaviy sozlamalar."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .. import common as C
from .. import ratelimit
from ..config import Settings, get_settings
from ..deps import get_current_user, get_store, platform_settings
from ..schemas import ComplaintIn, ProfileIn
from ..storage import JsonStore
from ..telegram import esc, notify_admins
from ..uploads import save_upload

router = APIRouter(tags=['users'])


@router.get('/users/me')
def me(user: dict = Depends(get_current_user)):
    return C.public_user(user)


@router.patch('/users/me')
def update_me(body: ProfileIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    patch = body.model_dump(exclude_unset=True)
    if 'firstName' in patch and (not patch['firstName'] or len(patch['firstName']) < 2):
        raise HTTPException(422, 'Ism kamida 2 belgi')
    if 'phone' in patch and not patch['phone']:
        raise HTTPException(422, 'Telefon majburiy')
    with store.tx('users') as db:
        if patch.get('phone') and any(C.phone_key(x.get('phone')) == C.phone_key(patch['phone']) and x['id'] != user['id'] for x in db['users']):
            raise HTTPException(409, 'Bu telefon raqam boshqa hisobda ishlatilgan')
        u = next(x for x in db['users'] if x['id'] == user['id'])
        u.update(patch)
        u['updatedAt'] = C.now_iso()
    return C.public_user(u)


@router.get('/users/{user_id}/public')
def public_profile(user_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    """Nomzod profili: faqat o‘zi, yoki unga ariza/so‘rov yuborgan e’lon egasi ko‘ra oladi."""
    db = store.read_many('users', 'jobs', 'houses', 'applications', 'requests')
    target = next((u for u in db['users'] if u['id'] == user_id), None)
    if not target:
        raise HTTPException(404, 'Topilmadi')
    allowed = user_id == user['id']
    if user['role'] == 'employer':
        mine = {j['id'] for j in db['jobs'] if j['employerId'] == user['id']}
        allowed |= any(a['studentId'] == user_id and a['jobId'] in mine for a in db['applications'])
    if user['role'] == 'landlord':
        mine = {h['id'] for h in db['houses'] if h['ownerId'] == user['id']}
        allowed |= any(r['studentId'] == user_id and r['houseId'] in mine for r in db['requests'])
    if not allowed:
        raise HTTPException(403, 'Ruxsat yo‘q')
    return C.student_card(target)


# ------------------------------------------------------------------ bildirishnomalar
@router.get('/notifications')
def notifications(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    if user.get('notifyApp') is False:  # foydalanuvchi Sozlamalarda ilova bildirishnomalarini o‘chirgan
        return []
    return C.by_date_desc([n for n in store.read('notifications') if n['userId'] == user['id']])[:100]


@router.post('/notifications/read-all', status_code=204)
def read_all(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    with store.tx('notifications') as db:
        for n in db['notifications']:
            if n['userId'] == user['id']:
                n['read'] = True


# ------------------------------------------------------------------ shikoyat
@router.post('/complaints', status_code=201, dependencies=[Depends(ratelimit.limit('complaint', 10, 3600))])
def complain(body: ComplaintIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    db0 = store.read_many('jobs', 'houses', 'users')
    coll = {'job': 'jobs', 'house': 'houses', 'user': 'users'}[body.target.type]
    target = next((x for x in db0[coll] if x['id'] == body.target.id), None)
    if not target:
        raise HTTPException(404, 'Shikoyat obyekti topilmadi')
    label = target.get('title') or C.full_name(target)
    now = C.now_iso()
    item = {'id': C.new_id('cp'), 'subject': body.category, 'category': body.category, 'priority': 'medium', 'message': body.message,
            'status': 'new', 'target': {'type': body.target.type, 'id': body.target.id, 'label': label},
            'from': {'id': user['id'], 'name': C.full_name(user), 'role': user['role']}, 'notes': [], 'createdAt': now, 'updatedAt': now}
    with store.tx('complaints') as db:
        db['complaints'].insert(0, item)
    notify_admins(f'⚠️ <b>Yangi shikoyat</b>\n{esc(body.category)}: {esc(label)}', f'/complaints?id={item["id"]}')
    return item


# ------------------------------------------------------------------ fayl yuklash
@router.post('/files', status_code=201, dependencies=[Depends(ratelimit.limit('upload', 60, 600))])
async def upload(file: UploadFile = File(...), kind: str = Form('file'), user: dict = Depends(get_current_user),
                 settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    if kind not in ('photo', 'shot', 'cv', 'logo', 'file'):
        raise HTTPException(400, 'Noto‘g‘ri fayl turi')
    return await save_upload(file, kind, store.media_dir, settings)


# ------------------------------------------------------------------ ommaviy konfiguratsiya
@router.get('/public/config')
def public_config(settings: Settings = Depends(get_settings), store: JsonStore = Depends(get_store)):
    s = platform_settings(store)
    return {'platformName': (s.get('platform') or {}).get('name') or 'TalabaGo', 'logo': (s.get('platform') or {}).get('logo'),
            'registrationOpen': s['system']['registrationOpen'], 'maintenance': s['system']['maintenance'],
            'telegramLogin': bool(settings.BOT_TOKEN)}
