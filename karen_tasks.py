"""Local task runner. Trusted code registers tools; model output never grants permission.

Only tool names and argument hashes are persisted. A caller must supply the exact
plan again to continue a task. Running tasks are never retried after a crash.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import threading
import time
import uuid


DEFAULT_PATH = Path(__file__).resolve().parent / '.private' / 'karen-tasks.sqlite3'
PERMISSIONS = {'read', 'reversible', 'sensitive', 'destructive'}


def task_database_path(path=None):
    if path is not None:
        return Path(path)
    configured = os.getenv('KAREN_TASKS_DB')
    if configured:
        if not Path(configured).is_absolute():
            raise ValueError('KAREN_TASKS_DB debe ser una ruta absoluta.')
        return Path(configured)
    return Path(DEFAULT_PATH)


def _now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ToolSpec:
    permission: str
    handler: object
    validate: object = None
    verify: object = None
    timeout: float = 20.0

    def __post_init__(self):
        if self.permission not in PERMISSIONS or not callable(self.handler):
            raise ValueError('Herramienta o permiso inválido.')
        if self.validate is not None and not callable(self.validate):
            raise ValueError('Validador inválido.')
        if self.verify is not None and not callable(self.verify):
            raise ValueError('Verificador inválido.')
        if not isinstance(self.timeout, (int, float)) or not 0 < self.timeout <= 300:
            raise ValueError('Timeout inválido.')


class TaskEngine:
    def __init__(self, tools, path=None):
        if not isinstance(tools, dict) or any(
            not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', name) or not isinstance(spec, ToolSpec)
            for name, spec in tools.items()
        ):
            raise ValueError('Registro de herramientas inválido.')
        self.tools = dict(tools)
        self.path = task_database_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_dir = self.path.parent / (self.path.name + '.locks')
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS task_jobs (
                    id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, plan_hash TEXT NOT NULL,
                    status TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS task_steps (
                    task_id TEXT NOT NULL, ordinal INTEGER NOT NULL, tool TEXT NOT NULL,
                    permission TEXT NOT NULL, args_hash TEXT NOT NULL, status TEXT NOT NULL,
                    PRIMARY KEY(task_id, ordinal),
                    FOREIGN KEY(task_id) REFERENCES task_jobs(id));
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    ordinal INTEGER, state TEXT NOT NULL, at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES task_jobs(id));
            ''')
        self._recover_interrupted()

    @contextmanager
    def _job_lock(self, task_id):
        if not isinstance(task_id, str) or not re.fullmatch(r'[0-9a-f]{32}', task_id):
            raise KeyError('Tarea desconocida.')
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        with (self.lock_dir / (task_id + '.lock')).open('a+b') as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN} and getattr(exc, 'winerror', None) != 33:
                    raise
                yield False
                return
            try:
                yield True
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _recover_interrupted(self):
        with self._connect() as db:
            running = [row['id'] for row in db.execute("SELECT id FROM task_jobs WHERE status='running'")]
        for task_id in running:
            with self._job_lock(task_id) as owned:
                if not owned:
                    continue
                with self._connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute("SELECT status FROM task_jobs WHERE id=?", (task_id,)).fetchone()
                    if not row or row['status'] != 'running':
                        continue
                    active = db.execute("SELECT ordinal,permission FROM task_steps WHERE task_id=? AND status='running'",
                                        (task_id,)).fetchone()
                    status = 'uncertain' if active and active['permission'] != 'read' else 'interrupted'
                    if active:
                        db.execute('UPDATE task_steps SET status=? WHERE task_id=? AND ordinal=?',
                                   (status, task_id, active['ordinal']))
                    db.execute('UPDATE task_jobs SET status=?,updated_at=? WHERE id=?',
                               (status, _now(), task_id))
                    self._event(db, task_id, active['ordinal'] if active else None, status)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _plan(self, steps):
        if not isinstance(steps, (list, tuple)) or not 1 <= len(steps) <= 32:
            raise ValueError('El plan requiere entre 1 y 32 pasos.')
        canonical = []
        for item in steps:
            if not isinstance(item, dict) or set(item) != {'tool', 'args'}:
                raise ValueError('Paso inválido.')
            name, args = item['tool'], item['args']
            if not isinstance(name, str) or name not in self.tools or not isinstance(args, dict):
                raise ValueError('Herramienta fuera de la lista permitida.')
            raw = json.dumps(args, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
            if len(raw) > 16384:
                raise ValueError('Argumentos demasiado largos.')
            if self.tools[name].validate:
                self.tools[name].validate(dict(args))
            canonical.append((name, raw))
        packed = json.dumps(canonical, ensure_ascii=False, separators=(',', ':'))
        digest = hashlib.sha256(packed.encode('utf-8')).hexdigest()
        return digest, canonical

    def create(self, steps, *, idempotency_key=None):
        digest, canonical = self._plan(steps)
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str) or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', idempotency_key)
        ):
            raise ValueError('Clave de idempotencia inválida.')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if idempotency_key:
                existing = db.execute('SELECT id,plan_hash FROM task_jobs WHERE idempotency_key=?',
                                      (idempotency_key,)).fetchone()
                if existing:
                    if existing['plan_hash'] != digest:
                        raise ValueError('La clave de idempotencia pertenece a otro plan.')
                    return existing['id']
            identity, now = uuid.uuid4().hex, _now()
            db.execute('INSERT INTO task_jobs VALUES (?,?,?,?,?,?,?,?)',
                       (identity, idempotency_key, digest, 'pending', 0, 0, now, now))
            for ordinal, (name, raw) in enumerate(canonical):
                db.execute('INSERT INTO task_steps VALUES (?,?,?,?,?,?)',
                           (identity, ordinal, name, self.tools[name].permission,
                            hashlib.sha256(raw.encode('utf-8')).hexdigest(), 'pending'))
            self._event(db, identity, None, 'pending')
            return identity

    @staticmethod
    def _event(db, task_id, ordinal, state):
        db.execute('INSERT INTO task_events (task_id,ordinal,state,at) VALUES (?,?,?,?)',
                   (task_id, ordinal, state, _now()))

    def inspect(self, task_id):
        with self._connect() as db:
            row = db.execute('SELECT * FROM task_jobs WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError('Tarea desconocida.')
            result = dict(row)
            result.pop('plan_hash')
            result.pop('idempotency_key')
            result['cancel_requested'] = bool(result['cancel_requested'])
            result['steps'] = [dict(step) for step in db.execute(
                'SELECT ordinal,tool,permission,status FROM task_steps WHERE task_id=? ORDER BY ordinal',
                (task_id,))]
            return result

    def events(self, task_id):
        with self._connect() as db:
            if not db.execute('SELECT 1 FROM task_jobs WHERE id=?', (task_id,)).fetchone():
                raise KeyError('Tarea desconocida.')
            return [dict(row) for row in db.execute(
                'SELECT ordinal,state,at FROM task_events WHERE task_id=? ORDER BY id', (task_id,))]

    def uncertain_jobs(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Límite inválido.')
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,status,cursor,updated_at FROM task_jobs WHERE status='uncertain' "
                'ORDER BY updated_at DESC LIMIT ?', (limit,))]

    def review_uncertain(self, task_id, outcome):
        """Record a human's external check; never execute or replay a tool."""
        if not isinstance(outcome, str) or outcome not in {'applied', 'not_applied'}:
            raise ValueError('Resultado de revisión inválido.')
        with self._job_lock(task_id) as owned:
            if not owned:
                raise RuntimeError('La tarea sigue ejecutándose.')
            with self._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT status FROM task_jobs WHERE id=?', (task_id,)).fetchone()
                if row is None:
                    raise KeyError('Tarea desconocida.')
                if row['status'] != 'uncertain':
                    raise ValueError('Solo se revisan tareas con estado uncertain.')
                status = 'reviewed_' + outcome
                db.execute('UPDATE task_jobs SET status=?,updated_at=? WHERE id=?',
                           (status, _now(), task_id))
                self._event(db, task_id, None, status)
        return self.inspect(task_id)

    def cancel(self, task_id):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM task_jobs WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError('Tarea desconocida.')
            if row['status'] in {'pending', 'awaiting_approval'}:
                db.execute("UPDATE task_jobs SET status='canceled',cancel_requested=1,updated_at=? WHERE id=?",
                           (_now(), task_id))
                self._event(db, task_id, None, 'canceled')
            elif row['status'] == 'running':
                db.execute('UPDATE task_jobs SET cancel_requested=1,updated_at=? WHERE id=?', (_now(), task_id))
                self._event(db, task_id, None, 'cancel_requested')
        return self.inspect(task_id)

    def _finish(self, task_id, ordinal, status, *, advance=False):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE task_steps SET status=? WHERE task_id=? AND ordinal=?',
                       (status, task_id, ordinal))
            db.execute('UPDATE task_jobs SET status=?,cursor=cursor+?,updated_at=? WHERE id=?',
                       (status if status != 'step_completed' else 'running', int(advance), _now(), task_id))
            self._event(db, task_id, ordinal, status)

    def _execute(self, spec, args, task_id):
        output = queue.Queue(maxsize=1)
        stop = threading.Event()

        def worker():
            try:
                output.put(('ok', spec.handler(dict(args), stop)))
            except Exception as exc:
                output.put(('error', type(exc).__name__))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        deadline = time.monotonic() + spec.timeout
        while thread.is_alive():
            thread.join(min(0.05, max(0, deadline - time.monotonic())))
            with self._connect() as db:
                cancelled = db.execute('SELECT cancel_requested FROM task_jobs WHERE id=?',
                                       (task_id,)).fetchone()[0]
            if cancelled:
                stop.set()
            if time.monotonic() >= deadline:
                stop.set()
                return 'timeout', None
        return output.get_nowait()

    def run(self, task_id, steps, *, approve=None):
        with self._job_lock(task_id) as owned:
            if not owned:
                return self.inspect(task_id)
            return self._run_locked(task_id, steps, approve=approve)

    def _run_locked(self, task_id, steps, *, approve=None):
        digest, canonical = self._plan(steps)
        results = []  # In-memory only; tool results never enter the task database.
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM task_jobs WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise KeyError('Tarea desconocida.')
            if row['plan_hash'] != digest:
                raise ValueError('El plan no coincide con la tarea guardada.')
            if row['status'] not in {'pending', 'awaiting_approval'}:
                return self.inspect(task_id)
            if row['cancel_requested']:
                return self.inspect(task_id)
            cursor = row['cursor']
            db.execute("UPDATE task_jobs SET status='running',updated_at=? WHERE id=?", (_now(), task_id))
            self._event(db, task_id, None, 'running')
        for ordinal in range(cursor, len(canonical)):
            with self._connect() as db:
                if db.execute('SELECT cancel_requested FROM task_jobs WHERE id=?',
                              (task_id,)).fetchone()[0]:
                    self._finish(task_id, ordinal, 'canceled')
                    return self.inspect(task_id)
            name = canonical[ordinal][0]
            spec, args = self.tools[name], steps[ordinal]['args']
            if spec.permission != 'read':
                if approve is None:
                    self._finish(task_id, ordinal, 'awaiting_approval')
                    return self.inspect(task_id)
                try:
                    granted = approve({'task_id': task_id, 'step': ordinal, 'tool': name,
                                       'permission': spec.permission, 'args': dict(args)})
                except Exception:
                    self._finish(task_id, ordinal, 'awaiting_approval')
                    return self.inspect(task_id)
                if not granted:
                    self._finish(task_id, ordinal, 'denied')
                    return self.inspect(task_id)
                with self._connect() as db:
                    self._event(db, task_id, ordinal, 'approved')
            with self._connect() as db:
                cancelled = bool(db.execute('SELECT cancel_requested FROM task_jobs WHERE id=?',
                                            (task_id,)).fetchone()[0])
                if not cancelled:
                    db.execute('UPDATE task_steps SET status=? WHERE task_id=? AND ordinal=?',
                               ('running', task_id, ordinal))
                    self._event(db, task_id, ordinal, 'running')
            if cancelled:
                self._finish(task_id, ordinal, 'canceled')
                return self.inspect(task_id)
            outcome, result = self._execute(spec, args, task_id)
            with self._connect() as db:
                cancelled = bool(db.execute('SELECT cancel_requested FROM task_jobs WHERE id=?',
                                            (task_id,)).fetchone()[0])
            if outcome == 'ok' and not cancelled and spec.verify:
                try:
                    verified = spec.verify(dict(args), result) is True
                except Exception:
                    verified = False
                if not verified:
                    outcome = 'verification_failed'
            if outcome != 'ok' or cancelled:
                state = ('canceled' if spec.permission == 'read' and cancelled else
                         'failed' if spec.permission == 'read' else 'uncertain')
                self._finish(task_id, ordinal, state)
                return self.inspect(task_id)
            self._finish(task_id, ordinal, 'step_completed', advance=True)
            results.append({'step': ordinal, 'tool': name, 'result': result})
        with self._connect() as db:
            db.execute("UPDATE task_jobs SET status='completed',updated_at=? WHERE id=?", (_now(), task_id))
            self._event(db, task_id, None, 'completed')
        completed = self.inspect(task_id)
        completed['results'] = results
        return completed
