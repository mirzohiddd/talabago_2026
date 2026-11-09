import json
import time

import pytest

from app.security import create_token, decode_token, hash_password, verify_password
from app.storage import JsonStore, StorageError
from app.telegram import InitDataError, sign_init_data, verify_init_data
from datetime import timedelta


def test_atomic_write_and_rollback(tmp_path):
    s = JsonStore(tmp_path, backup_keep=3, backup_interval=0)
    with s.tx('users') as db:
        db['users'].append({'id': 'u1'})
    assert s.read('users') == [{'id': 'u1'}]
    with pytest.raises(RuntimeError):
        with s.tx('users') as db:
            db['users'].append({'id': 'u2'})
            raise RuntimeError('boom')
    assert s.read('users') == [{'id': 'u1'}], 'xato bo‘lsa hech narsa yozilmaydi'
    assert not list((tmp_path / 'db').glob('*.tmp'))


def test_read_returns_copy(tmp_path):
    s = JsonStore(tmp_path)
    with s.tx('jobs') as db:
        db['jobs'].append({'id': 'j1'})
    x = s.read('jobs')
    x.append({'id': 'hack'})
    assert len(s.read('jobs')) == 1


def test_backups_rotate_and_recover_from_corruption(tmp_path):
    s = JsonStore(tmp_path, backup_keep=3, backup_interval=0)
    for i in range(6):
        with s.tx('users') as db:
            db['users'].append({'id': f'u{i}'})
    backups = sorted((tmp_path / 'backups' / 'users').glob('*.json'))
    assert len(backups) == 3
    (tmp_path / 'db' / 'users.json').write_text('{"buzilgan', encoding='utf-8')
    s2 = JsonStore(tmp_path, backup_keep=3, backup_interval=0)
    restored = s2.read('users')
    assert [u['id'] for u in restored] == ['u0', 'u1', 'u2', 'u3', 'u4']  # oxirgi zaxira (o‘zgartirishdan oldingi holat)
    assert list((tmp_path / 'db').glob('users.corrupt-*.json'))


def test_corruption_without_backup_raises(tmp_path):
    s = JsonStore(tmp_path)
    (tmp_path / 'db' / 'jobs.json').write_text('[1,', encoding='utf-8')
    with pytest.raises(StorageError):
        s.read('jobs')


def test_unknown_collection(tmp_path):
    with pytest.raises(StorageError):
        JsonStore(tmp_path).read('../etc/passwd')


def test_password_hash():
    h = hash_password('maxfiy-parol')
    assert h.startswith('scrypt$') and 'maxfiy' not in h
    assert verify_password('maxfiy-parol', h)
    assert not verify_password('boshqa', h)
    assert not verify_password('x', None)
    assert hash_password('a' * 8) != hash_password('a' * 8)  # tuz (salt) har safar boshqa


def test_jwt_type_and_expiry():
    tok, _ = create_token('k' * 40, 'u1', 'user', timedelta(minutes=5))
    assert decode_token('k' * 40, tok, 'user')['sub'] == 'u1'
    assert decode_token('k' * 40, tok, 'admin') is None, 'foydalanuvchi tokeni admin sifatida o‘tmaydi'
    assert decode_token('boshqa' * 10, tok, 'user') is None
    old, _ = create_token('k' * 40, 'u1', 'user', timedelta(seconds=-1))
    assert decode_token('k' * 40, old, 'user') is None


def test_init_data_verification():
    bot = '42:ABC'
    data = sign_init_data({'id': 5, 'first_name': 'Ali', 'username': 'ali_dev'}, bot)
    assert verify_init_data(data, bot)['id'] == 5
    with pytest.raises(InitDataError):
        verify_init_data(data, '42:WRONG')
    with pytest.raises(InitDataError):
        verify_init_data(data.replace('Ali', 'Vali'), bot)
    with pytest.raises(InitDataError):
        verify_init_data(sign_init_data({'id': 5}, bot, auth_date=int(time.time()) - 100000), bot, max_age=86400)
    with pytest.raises(InitDataError):
        verify_init_data('', bot)
