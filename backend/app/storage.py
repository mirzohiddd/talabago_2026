"""
JSON fayl ombori.

* Har bir kolleksiya — alohida fayl: DATA_DIR/db/<nom>.json
* Yozish: avval vaqtinchalik faylga, fsync, so‘ng os.replace (atomik) — yarim yozilgan fayl qolmaydi.
* Qulf: jarayon ichida RLock + jarayonlar orasida fcntl.flock (bir nechta uvicorn worker uchun).
* Zaxira: o‘zgartirishdan oldingi holat DATA_DIR/backups/<nom>/ ga (BACKUP_INTERVAL_SECONDS da ko‘pi bilan bir marta),
  oxirgi BACKUP_KEEP nusxa saqlanadi.
* Buzilgan fayl: <nom>.corrupt-<vaqt>.json ga ko‘chiriladi va eng so‘nggi butun zaxiradan tiklanadi.
"""
from __future__ import annotations

import copy
import fcntl
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

log = logging.getLogger('talabago.storage')

LIST_COLLECTIONS = (
    'users', 'admins', 'jobs', 'houses', 'applications', 'requests', 'courses', 'progress',
    'tickets', 'complaints', 'notifications', 'ads',
)
DICT_COLLECTIONS = ('saved', 'settings', 'meta')


class StorageError(RuntimeError):
    pass


class JsonStore:
    def __init__(self, data_dir: Path, backup_keep: int = 30, backup_interval: int = 300):
        self.dir = Path(data_dir)
        self.db_dir = self.dir / 'db'
        self.backup_dir = self.dir / 'backups'
        self.media_dir = self.dir / 'media'
        for d in (self.db_dir, self.backup_dir, self.media_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.backup_keep = backup_keep
        self.backup_interval = backup_interval
        self._lock = threading.RLock()
        self._lock_path = self.db_dir / '.lock'
        self._lock_path.touch(exist_ok=True)
        self._cache: dict[str, tuple[int, int, Any]] = {}
        self._last_backup: dict[str, float] = {}

    # ------------------------------------------------------------------ yordamchi
    def _path(self, name: str) -> Path:
        if name not in LIST_COLLECTIONS and name not in DICT_COLLECTIONS:
            raise StorageError(f'Noma’lum kolleksiya: {name}')
        return self.db_dir / f'{name}.json'

    @staticmethod
    def _empty(name: str):
        return {} if name in DICT_COLLECTIONS else []

    @contextmanager
    def _file_lock(self, exclusive: bool) -> Iterator[None]:
        with self._lock:
            with open(self._lock_path, 'r+') as fh:
                fcntl.flock(fh, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                try:
                    yield
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)

    def _load(self, name: str) -> Any:
        """Qulf ostida chaqiriladi. Fayl o‘zgarmagan bo‘lsa keshdan qaytaradi."""
        path = self._path(name)
        if not path.exists():
            return self._empty(name)
        st = path.stat()
        cached = self._cache.get(name)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2]
        try:
            with open(path, encoding='utf-8') as fh:
                data = json.load(fh)
            if not isinstance(data, type(self._empty(name))):
                raise ValueError('kutilmagan tur')
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
            data = self._recover(name, exc)
            st = path.stat()
        self._cache[name] = (st.st_mtime_ns, st.st_size, data)
        return data

    def _recover(self, name: str, exc: Exception) -> Any:
        path = self._path(name)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        corrupt = path.with_name(f'{name}.corrupt-{stamp}.json')
        shutil.move(path, corrupt)
        log.error('%s.json buzilgan (%s) → %s ga ko‘chirildi', name, exc, corrupt.name)
        for b in sorted((self.backup_dir / name).glob('*.json'), reverse=True):
            try:
                data = json.loads(b.read_text(encoding='utf-8'))
                self._atomic_write(path, data)
                log.warning('%s.json zaxiradan tiklandi: %s', name, b.name)
                return data
            except Exception:  # noqa: BLE001 — keyingi zaxirani sinaymiz
                continue
        raise StorageError(f'{name}.json buzilgan va butun zaxira topilmadi (fayl: {corrupt.name})')

    def _atomic_write(self, path: Path, data: Any) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False)
        fd, tmp = tempfile.mkstemp(prefix=f'.{path.stem}-', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            dfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def _backup(self, name: str, force: bool = False) -> None:
        path = self._path(name)
        if not path.exists():
            return
        now = time.time()
        if not force and now - self._last_backup.get(name, 0) < self.backup_interval:
            return
        target = self.backup_dir / name
        target.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        shutil.copy2(path, target / f'{stamp}.json')
        self._last_backup[name] = now
        for old in sorted(target.glob('*.json'))[:-self.backup_keep]:
            old.unlink(missing_ok=True)

    # ------------------------------------------------------------------ ommaviy API
    def read(self, name: str) -> Any:
        """Kolleksiyaning nusxasi (o‘zgartirish omborga ta’sir qilmaydi)."""
        with self._file_lock(exclusive=False):
            return copy.deepcopy(self._load(name))

    def read_many(self, *names: str) -> dict[str, Any]:
        with self._file_lock(exclusive=False):
            return {n: copy.deepcopy(self._load(n)) for n in names}

    @contextmanager
    def tx(self, *names: str) -> Iterator[dict[str, Any]]:
        """
        Tranzaksiya: `with store.tx('jobs', 'notifications') as db: db['jobs'].append(...)`
        Blok xatosiz tugasa — o‘zgargan kolleksiyalar atomik yoziladi; xato bo‘lsa — hech narsa yozilmaydi.
        """
        with self._file_lock(exclusive=True):
            originals = {n: self._load(n) for n in names}
            work = {n: copy.deepcopy(v) for n, v in originals.items()}
            yield work
            for n in names:
                if work[n] != originals[n]:
                    self._backup(n)
                    path = self._path(n)
                    self._atomic_write(path, work[n])
                    st = path.stat()
                    self._cache[n] = (st.st_mtime_ns, st.st_size, work[n])

    def snapshot(self) -> Path:
        """Barcha kolleksiyalarning to‘liq zaxirasi (CLI: python -m app.cli backup)."""
        with self._file_lock(exclusive=False):
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
            target = self.backup_dir / f'full-{stamp}'
            target.mkdir(parents=True, exist_ok=True)
            for p in self.db_dir.glob('*.json'):
                shutil.copy2(p, target / p.name)
            return target
