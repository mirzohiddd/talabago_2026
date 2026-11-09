"""
Oddiy in-memory sliding-window rate limiter.
Eslatma: bir nechta worker/server bo‘lsa har biri o‘z hisobini yuritadi — production’da reverse proxy
(nginx limit_req) yoki Redis asosidagi limiter bilan to‘ldirish tavsiya etiladi.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import get_settings

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


LOCAL = {'127.0.0.1', '::1', 'localhost'}


def client_ip(request: Request) -> str:
    """
    Haqiqiy mijoz IP’si. So‘rov lokal proxy’dan (Vite / cloudflared / nginx) kelsa — Cloudflare’ning CF-Connecting-IP
    yoki X-Forwarded-For’dagi birinchi manzil ishlatiladi. Tashqaridan to‘g‘ridan-to‘g‘ri kelgan so‘rovda sarlavhalarga ishonilmaydi.
    """
    host = request.client.host if request.client else 'unknown'
    if host in LOCAL:
        cf = request.headers.get('cf-connecting-ip')
        if cf:
            return cf.strip()
        xff = request.headers.get('x-forwarded-for')
        if xff:
            return xff.split(',')[0].strip()
    return host


def hit(key: str, limit: int, window: float) -> float:
    """So‘rovni hisoblaydi. Limitdan oshsa — necha soniyadan keyin qayta urinish mumkinligini qaytaradi, aks holda 0."""
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return max(1.0, window - (now - q[0]))
        q.append(now)
        return 0.0


def check(key: str, limit: int, window: float) -> None:
    if not get_settings().RATE_LIMIT_ENABLED:
        return
    retry = hit(key, limit, window)
    if retry:
        raise HTTPException(429, detail='Juda ko‘p so‘rov. Birozdan so‘ng urinib ko‘ring.', headers={'Retry-After': str(int(retry))})


def limit(name: str, count: int, window: float):
    """FastAPI dependency: IP bo‘yicha cheklov."""
    def dep(request: Request) -> None:
        check(f'{name}:{client_ip(request)}', count, window)
    return dep


def reset() -> None:
    with _lock:
        _hits.clear()


def recent(key: str, window: float) -> tuple[int, float]:
    """(oxirgi `window` soniyadagi urinishlar soni, eng eskisi tugashiga qolgan soniya)."""
    now = time.monotonic()
    with _lock:
        q = _hits.get(key)
        if not q:
            return 0, 0.0
        while q and now - q[0] > window:
            q.popleft()
        return len(q), (window - (now - q[0])) if q else 0.0


def record(key: str) -> None:
    with _lock:
        _hits[key].append(time.monotonic())


def guard_failures(key: str, max_fails: int, window: float) -> None:
    """Ketma-ket xato urinishlar (login) uchun bloklash."""
    if not get_settings().RATE_LIMIT_ENABLED:
        return
    n, retry = recent(key, window)
    if n >= max_fails:
        raise HTTPException(429, detail='Juda ko‘p noto‘g‘ri urinish. Keyinroq qayta urinib ko‘ring.',
                            headers={'Retry-After': str(max(1, int(retry)))})
