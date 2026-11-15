"""O‘zaro baholash: ish yakunlangach (ariza holati “completed”) talaba va ish beruvchi bir-birini 1–5 yulduz va izoh bilan baholaydi.

Bitta ariza bo‘yicha har bir tomon faqat bir marta baholaydi (takroriy — 409). Support yashirgan baholar o‘rtacha bahoga kirmaydi.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import common as C
from ..deps import get_current_user, get_store
from ..schemas import ReviewIn
from ..storage import JsonStore
from ..telegram import notify_user

router = APIRouter(tags=['reviews'])


def rating_summary(reviews: list[dict], user_id: str) -> dict:
    vis = [r for r in reviews if r['toId'] == user_id and not r.get('hidden')]
    return {'avg': round(sum(r['stars'] for r in vis) / len(vis), 1) if vis else None, 'count': len(vis)}


def ratings_map(store: JsonStore) -> dict:
    """{userId: {avg, count}} — reviews.json o‘zgarguncha keshlanadi."""
    def build(rs):
        acc: dict[str, list[int]] = {}
        for r in rs:
            if not r.get('hidden'):
                acc.setdefault(r['toId'], []).append(r['stars'])
        return {k: {'avg': round(sum(v) / len(v), 1), 'count': len(v)} for k, v in acc.items()}
    return store.derived('reviews', 'ratings', build)


def _review_view(r: dict, users: dict) -> dict:
    u = users.get(r['fromId'])
    return {'id': r['id'], 'stars': r['stars'], 'comment': r.get('comment') or '', 'fromRole': r['fromRole'], 'fromName': C.full_name(u) if u else '—',
            'createdAt': r['createdAt'], 'applicationId': r['applicationId']}


def _parties(db: dict, app_id: str, user: dict) -> tuple[dict, dict, str]:
    a = next((x for x in db['applications'] if x['id'] == app_id), None)
    job = a and next((j for j in db['jobs'] if j['id'] == a['jobId']), None)
    if not a or not job or user['id'] not in (a['studentId'], job.get('employerId')):
        raise HTTPException(404, 'Ariza topilmadi')
    target = job['employerId'] if user['id'] == a['studentId'] else a['studentId']
    return a, job, target


@router.get('/applications/{app_id}/reviews')
def app_reviews(app_id: str, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    db = store.read_many('applications', 'jobs', 'reviews', 'users')
    a, job, target = _parties(db, app_id, user)
    users = {u['id']: u for u in db['users']}
    mine = next((r for r in db['reviews'] if r['applicationId'] == app_id and r['fromId'] == user['id']), None)
    theirs = next((r for r in db['reviews'] if r['applicationId'] == app_id and r['fromId'] == target and not r.get('hidden')), None)
    return {'canReview': a['status'] == 'completed' and not mine and bool(job.get('employerId')),
            'status': a['status'], 'mine': _review_view(mine, users) if mine else None, 'theirs': _review_view(theirs, users) if theirs else None}


@router.post('/applications/{app_id}/review', status_code=201)
def create_review(app_id: str, body: ReviewIn, user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    with store.tx('applications', 'jobs', 'reviews', 'notifications', 'users') as db:
        a, job, target = _parties(db, app_id, user)
        if a['status'] != 'completed':
            raise HTTPException(409, 'Baholash ish yakunlangandan keyin ochiladi')
        if not target:
            raise HTTPException(409, 'Bu e’lon egasining akkaunti yo‘q')
        if any(r['applicationId'] == app_id and r['fromId'] == user['id'] for r in db['reviews']):
            raise HTTPException(409, 'Siz allaqachon baho qo‘ygansiz')
        r = {'id': C.new_id('rv'), 'applicationId': app_id, 'jobId': job['id'], 'fromId': user['id'], 'toId': target,
             'fromRole': 'student' if user['id'] == a['studentId'] else 'employer', 'stars': body.stars, 'comment': body.comment.strip(),
             'hidden': False, 'createdAt': C.now_iso()}
        db['reviews'].insert(0, r)
        to = next((u for u in db['users'] if u['id'] == target), None)
        link = '/student/applications' if r['fromRole'] == 'employer' else '/employer/applications'
        C.add_notification(db['notifications'], target, 'star', f'Sizga {body.stars}★ baho qo‘yildi', f'{C.full_name(user)} · {job["title"]}', link)
    notify_user(C.tg_chat(to), f'⭐ <b>Sizga {body.stars} yulduzli baho qo‘yildi</b>', link)
    return _review_view(r, {user['id']: user})


@router.get('/users/{user_id}/reviews')
def user_reviews(user_id: str, _: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    db = store.read_many('reviews', 'users')
    users = {u['id']: u for u in db['users']}
    if user_id not in users:
        raise HTTPException(404, 'Foydalanuvchi topilmadi')
    items = [r for r in C.by_date_desc(db['reviews']) if r['toId'] == user_id and not r.get('hidden')]
    return {**rating_summary(db['reviews'], user_id), 'items': [_review_view(r, users) for r in items[:50]]}
