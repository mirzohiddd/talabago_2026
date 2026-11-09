"""Parol xeshlash (scrypt), JWT va ruxsat tekshiruvi uchun yordamchilar."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1
JWT_ALG = 'HS256'


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=128 * 1024 * 1024, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f'scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt)}${b64(dk)}'


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        # vaqt bo‘yicha farq bilan foydalanuvchi borligini oshkor qilmaslik uchun baribir hisoblaymiz
        hashlib.scrypt(b'x', salt=b'0' * 16, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=128 * 1024 * 1024, dklen=32)
        return False
    try:
        algo, n, r, p, salt, dk = stored.split('$')
        if algo != 'scrypt':
            return False
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), maxmem=128 * 1024 * 1024, dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


def create_token(secret: str, sub: str, typ: str, ttl: timedelta, **claims) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    exp = now + ttl
    token = jwt.encode({'sub': sub, 'typ': typ, 'iat': now, 'exp': exp, 'jti': secrets.token_hex(8), **claims}, secret, algorithm=JWT_ALG)
    return token, exp


def decode_token(secret: str, token: str, typ: str) -> dict | None:
    try:
        data = jwt.decode(token, secret, algorithms=[JWT_ALG], options={'require': ['exp', 'sub', 'typ']})
    except jwt.PyJWTError:
        return None
    return data if data.get('typ') == typ else None
