"""Ish beruvchi monitoringi: e’lonlar, ko‘rishlar, arizalar, qiziqishlar (saqlab qo‘yishlar), soha va ish turlari bo‘yicha real statistika.

Manbalar (demo yo‘q): jobs.json (views — umumiy), jobstats.json (kunlik ko‘rish/saqlash — shu funksiya qo‘shilgandan beri),
applications.json (arizalar va holatlari), saved.json (hozir saqlab qo‘yganlar soni), reviews.json (reyting).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from .. import common as C
from ..deps import get_store, require_role
from ..storage import JsonStore
from .reviews import rating_summary

router = APIRouter(tags=['insights'])
employer = require_role('employer')
STATUSES = ('sent', 'viewed', 'interview', 'accepted', 'declined', 'completed')


def _group(rows: list[dict], key: str, labels) -> list[dict]:
    out: dict[str, dict] = {}
    for r in rows:
        k = r.get(key) or 'Boshqa'
        g = out.setdefault(k, {'key': k, 'jobs': 0, 'views': 0, 'applications': 0, 'interests': 0})
        g['jobs'] += 1
        for m in ('views', 'applications', 'interests'):
            g[m] += r[m]
    order = list(labels)
    return sorted(out.values(), key=lambda g: (-g['applications'], -g['views'], order.index(g['key']) if g['key'] in order else 99))


@router.get('/employer/insights')
def insights(days: int = Query(30, ge=7, le=90), user: dict = Depends(employer), store: JsonStore = Depends(get_store)):
    db = store.peek('jobs', 'applications', 'jobstats', 'saved', 'reviews')
    jobs = [j for j in db['jobs'] if j.get('employerId') == user['id']]
    ids = {j['id'] for j in jobs}
    apps = [a for a in db['applications'] if a['jobId'] in ids and a['status'] != 'withdrawn']
    interests: dict[str, int] = {}
    for entry in db['saved'].values():
        for jid in (entry or {}).get('jobs', []):
            if jid in ids:
                interests[jid] = interests.get(jid, 0) + 1
    per_job = []
    for j in C.by_date_desc(jobs):
        ja = [a for a in apps if a['jobId'] == j['id']]
        per_job.append({'id': j['id'], 'title': j['title'], 'status': j['status'], 'category': j.get('category') or '', 'type': j.get('type'),
                        'views': j.get('views') or 0, 'applications': len(ja), 'interests': interests.get(j['id'], 0),
                        'accepted': len([a for a in ja if a['status'] in ('accepted', 'completed')]),
                        'conversion': round(len(ja) / j['views'] * 100, 1) if j.get('views') else None, 'createdAt': j['createdAt']})
    # kunlik qatorlar (oxirgi `days` kun)
    today = datetime.now(timezone.utc).date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    series = {d: {'date': d, 'views': 0, 'applications': 0, 'interests': 0} for d in dates}
    for jid in ids:
        st = db['jobstats'].get(jid) or {}
        for metric, key in (('views', 'views'), ('saves', 'interests')):
            for d, n in (st.get(metric) or {}).items():
                if d in series:
                    series[d][key] += n
    for a in apps:
        d = (a.get('createdAt') or '')[:10]
        if d in series:
            series[d]['applications'] += 1
    total_views = sum(r['views'] for r in per_job)
    total_apps = len(apps)
    return {
        'periodDays': days,
        'totals': {
            'jobs': len(jobs), 'active': len([j for j in jobs if j['status'] == 'active']), 'pending': len([j for j in jobs if j['status'] == 'pending']),
            'closed': len([j for j in jobs if j['status'] in ('closed', 'rejected', 'hidden')]),
            'views': total_views, 'applications': total_apps, 'interests': sum(interests.values()),
            'accepted': len([a for a in apps if a['status'] in ('accepted', 'completed')]),
            'conversion': round(total_apps / total_views * 100, 1) if total_views else None,
            'periodViews': sum(s['views'] for s in series.values()), 'periodApplications': sum(s['applications'] for s in series.values()),
        },
        'timeline': list(series.values()),
        'applicationsByStatus': [{'key': k, 'count': len([a for a in apps if a['status'] == k])} for k in STATUSES],
        'byCategory': _group(per_job, 'category', C.JOB_CATEGORIES),
        'byType': _group(per_job, 'type', C.JOB_TYPES),
        'jobs': per_job,
        'rating': rating_summary(db['reviews'], user['id']),
        'trackingSince': min((d for jid in ids for m in (db['jobstats'].get(jid) or {}).values() for d in m), default=None),
    }
