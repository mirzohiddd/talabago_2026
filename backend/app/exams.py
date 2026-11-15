"""Kurs yakuniy testi (jami 2 urinish) va QR-kodli PDF sertifikat.

Talaba: barcha darslarni tugatgach yakuniy testni topshiradi. Javoblar faqat serverda tekshiriladi (to‘g‘ri javoblar
talabaga yuborilmaydi). O‘tgan bo‘lsa — sertifikat yaratiladi. Sertifikat ommaviy havola (tasodifiy kod) orqali
PDF va tekshirish sahifasi sifatida ochiladi; Support uni bekor qilishi mumkin.
"""
from __future__ import annotations

import html
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from . import common as C
from . import ratelimit
from .certificate import format_date, render_pdf
from .config import Settings, get_settings
from .deps import get_current_user, get_store, require_role
from .schemas import ExamSubmitIn
from .storage import JsonStore
from .telegram import esc, notify_user

router = APIRouter(tags=['exams'])
student = require_role('student')


def published_lessons(course: dict) -> list[dict]:
    return [l for l in course.get('lessons', []) if l.get('status') == 'published']


def final_test(course: dict) -> dict | None:
    t = course.get('finalTest') or None
    if not t or t.get('status') != 'published' or not t.get('questions'):
        return None
    return t


def attempts_of(exams: list[dict], user_id: str, course_id: str) -> list[dict]:
    """Hisobga olinadigan urinishlar (Support “qayta topshirishga ruxsat” bergan eski urinishlar — voided)."""
    return sorted([e for e in exams if e['userId'] == user_id and e['courseId'] == course_id and not e.get('voided')], key=lambda e: e['createdAt'])


def max_attempts(test: dict) -> int:
    return int(test.get('maxAttempts') or C.EXAM_MAX_ATTEMPTS)


def pass_percent(test: dict) -> int:
    return int(test.get('passPercent') or C.EXAM_PASS_PERCENT)


def verify_url(request: Request, settings: Settings, code: str) -> str:
    base = (settings.PUBLIC_API_URL or str(request.base_url)).rstrip('/')
    return f'{base}/api/v1/certificates/{code}/page'


def _attempt_view(e: dict) -> dict:
    return {k: e[k] for k in ('id', 'score', 'total', 'percent', 'passed', 'createdAt')}


def cert_view(c: dict) -> dict:
    return {k: c.get(k) for k in ('id', 'code', 'courseId', 'courseTitle', 'fullName', 'percent', 'issuedAt', 'status')}


def _course_and_test(store: JsonStore, course_id: str) -> tuple[dict, dict]:
    course = next((c for c in store.read('courses') if c['id'] == course_id and c.get('status') == 'published'), None)
    if not course:
        raise HTTPException(404, 'Kurs topilmadi')
    test = final_test(course)
    if not test:
        raise HTTPException(404, 'Bu kurs uchun yakuniy test hali tayyorlanmagan')
    return course, test


def _eligible(store: JsonStore, user_id: str, course: dict) -> tuple[bool, int, int]:
    lessons = published_lessons(course)
    p = next((x for x in store.read('progress') if x['userId'] == user_id and x['courseId'] == course['id']), None)
    done = len([l for l in lessons if p and l['id'] in p.get('completed', [])])
    return done >= len(lessons), done, len(lessons)


@router.get('/courses/{course_id}/exam')
def exam(course_id: str, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    course, test = _course_and_test(store, course_id)
    db = store.read_many('exams', 'certificates')
    tries = attempts_of(db['exams'], user['id'], course_id)
    cert = next((c for c in db['certificates'] if c['userId'] == user['id'] and c['courseId'] == course_id and c.get('status') == 'valid'), None)
    ok, done, total = _eligible(store, user['id'], course)
    left = max(0, max_attempts(test) - len(tries))
    return {
        'courseId': course_id, 'courseTitle': course['title'],
        'questions': [{'q': q['q'], 'options': q['options']} for q in test['questions']],   # to‘g‘ri javoblarsiz
        'passPercent': pass_percent(test), 'maxAttempts': max_attempts(test), 'attempts': [_attempt_view(e) for e in tries],
        'attemptsLeft': 0 if cert else left, 'eligible': ok, 'lessonsDone': done, 'lessonsTotal': total,
        'passed': bool(cert), 'certificate': cert_view(cert) if cert else None,
    }


@router.post('/courses/{course_id}/exam/submit', dependencies=[Depends(ratelimit.limit('exam', 10, 3600))])
def submit(course_id: str, body: ExamSubmitIn, user: dict = Depends(student), store: JsonStore = Depends(get_store)):
    course, test = _course_and_test(store, course_id)
    ok, _, _ = _eligible(store, user['id'], course)
    if not ok:
        raise HTTPException(409, 'Yakuniy testdan oldin barcha darslarni tugating')
    qs = test['questions']
    if len(body.answers) != len(qs):
        raise HTTPException(422, f'Barcha {len(qs)} ta savolga javob bering')
    if any(a is None for a in body.answers):
        raise HTTPException(422, 'Barcha savollarga javob bering')
    now = C.now_iso()
    with store.tx('exams', 'certificates', 'notifications') as db:
        if any(c['userId'] == user['id'] and c['courseId'] == course_id and c.get('status') == 'valid' for c in db['certificates']):
            raise HTTPException(409, 'Siz bu testdan o‘tgansiz — sertifikat allaqachon berilgan')
        tries = attempts_of(db['exams'], user['id'], course_id)
        if len(tries) >= max_attempts(test):
            raise HTTPException(409, f'Urinishlar tugadi ({max_attempts(test)} ta). Qayta topshirish uchun Support’ga murojaat qiling')
        score = sum(1 for q, a in zip(qs, body.answers) if q.get('answer') == a)
        percent = round(score / len(qs) * 100)
        passed = percent >= pass_percent(test)
        attempt = {'id': C.new_id('ex'), 'userId': user['id'], 'courseId': course_id, 'answers': body.answers, 'score': score, 'total': len(qs),
                   'percent': percent, 'passed': passed, 'attemptNo': len(tries) + 1, 'createdAt': now}
        db['exams'].insert(0, attempt)
        cert = None
        if passed:
            cert = {'id': C.new_id('cert'), 'code': 'TG-' + secrets.token_hex(5).upper(), 'userId': user['id'], 'courseId': course_id,
                    'courseTitle': course['title'], 'fullName': C.full_name(user), 'percent': percent, 'examId': attempt['id'],
                    'issuedAt': now, 'status': 'valid'}
            db['certificates'].insert(0, cert)
            C.add_notification(db['notifications'], user['id'], 'check', 'Sertifikat tayyor', f'“{course["title"]}” kursi — {percent}%', f'/student/courses/{course_id}/exam')
        left = 0 if passed else max(0, max_attempts(test) - len(tries) - 1)
    if cert:
        notify_user(C.tg_chat(user), f'🎓 <b>Tabriklaymiz!</b>\n“{esc(course["title"])}” kursi bo‘yicha sertifikatingiz tayyor ({percent}%).', f'/student/courses/{course_id}/exam')
    return {'attempt': _attempt_view(attempt), 'certificate': cert_view(cert) if cert else None, 'attemptsLeft': left, 'passPercent': pass_percent(test)}


@router.get('/me/certificates')
def my_certificates(user: dict = Depends(get_current_user), store: JsonStore = Depends(get_store)):
    return [cert_view(c) for c in C.by_date_desc(store.read('certificates'), 'issuedAt') if c['userId'] == user['id']]


# ============================================================ ommaviy: tekshirish va PDF
def _by_code(store: JsonStore, code: str) -> dict:
    c = next((x for x in store.read('certificates') if x.get('code') == code.upper()), None)
    if not c:
        raise HTTPException(404, 'Sertifikat topilmadi')
    return c


@router.get('/certificates/{code}', dependencies=[Depends(ratelimit.limit('cert', 120, 600))])
def verify(code: str, store: JsonStore = Depends(get_store)):
    c = _by_code(store, code)
    return {**cert_view(c), 'valid': c.get('status') == 'valid'}


@router.get('/certificates/{code}/pdf', dependencies=[Depends(ratelimit.limit('cert', 120, 600))])
def certificate_pdf(code: str, request: Request, store: JsonStore = Depends(get_store), settings: Settings = Depends(get_settings)):
    c = _by_code(store, code)
    pdf = render_pdf(c, verify_url(request, settings, c['code']))
    return Response(pdf, media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="TalabaGo_sertifikat_{c["code"]}.pdf"',
                                                                 'Cache-Control': 'no-store'})


@router.get('/certificates/{code}/page', response_class=HTMLResponse, dependencies=[Depends(ratelimit.limit('cert', 120, 600))])
def certificate_page(code: str, store: JsonStore = Depends(get_store)):
    c = next((x for x in store.read('certificates') if x.get('code') == code.upper()), None)
    e = html.escape
    if not c:
        body, color, title = '<p>Bunday raqamli sertifikat topilmadi.</p>', '#dc2626', 'Sertifikat topilmadi'
    elif c.get('status') != 'valid':
        body, color, title = f'<p><b>{e(c["code"])}</b> raqamli sertifikat bekor qilingan.</p>', '#dc2626', 'Sertifikat bekor qilingan'
    else:
        body = (f'<p class="n">{e(c["fullName"])}</p><p>“{e(c["courseTitle"])}” kursini muvaffaqiyatli tamomlagan.</p>'
                f'<p>Yakuniy test natijasi: <b>{c["percent"]}%</b></p><p>Berilgan sana: {e(format_date(c["issuedAt"]))}</p>'
                f'<p class="m">Raqam: {e(c["code"])}</p><a href="pdf">PDF’ni ochish</a>')
        color, title = '#10B981', '✓ Sertifikat haqiqiy'
    page = f'''<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TalabaGo — sertifikatni tekshirish</title><style>
body{{margin:0;background:#fff;color:#111;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:16px}}
.c{{max-width:460px;width:100%;border:3px solid #111;border-radius:24px;padding:28px;box-shadow:10px 10px 0 #10B981}}
h1{{font-size:22px;margin:0 0 16px;color:{color}}} .b{{font-weight:800;font-size:15px;color:#065f46;letter-spacing:.04em}}
.n{{font-size:24px;font-weight:800;margin:4px 0 8px}} .m{{color:#5a6069;font-size:14px}}
a{{display:inline-block;margin-top:12px;background:#10B981;color:#fff;font-weight:700;padding:12px 18px;border-radius:12px;text-decoration:none;border:2px solid #111}}
</style></head><body><div class="c"><p class="b">TalabaGo</p><h1>{title}</h1>{body}</div></body></html>'''
    return HTMLResponse(page, headers={'Cache-Control': 'no-store'})
