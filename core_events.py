"""Persistent bounded event contract and live client activity for Karen Core v1.

Activity heartbeats are advisory, never permission grants or resource locks.
Event consumers use sequence cursors and detect retention gaps after restarts.
"""

from contextlib import closing
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from typing import Literal, TypedDict

SCHEMA = Path(__file__).resolve().parent / 'desktop-pet' / 'shared' / 'core-events.sql'
CoreState = Literal['IDLE', 'LISTENING', 'TRANSCRIBING', 'THINKING', 'SPEAKING', 'ERROR']
STATES = {'IDLE', 'LISTENING', 'TRANSCRIBING', 'THINKING', 'SPEAKING', 'ERROR'}


class CoreEvent(TypedDict):
    seq: int
    topic: str
    entity_id: str
    action: str
    at: str


def install_events(db):
    version = db.execute("SELECT value FROM core_meta WHERE key='events_version'").fetchone()
    if version and version[0] != '1':
        raise ValueError('Versión de eventos Core no compatible.')
    if version:
        return
    # One transaction; failed installation cannot leave half-created triggers.
    db.executescript('BEGIN IMMEDIATE;\n' + SCHEMA.read_text(encoding='utf-8') + '\nCOMMIT;')


def read_events(db, after=0, limit=100):
    if type(after) is not int or not 0 <= after <= 2**63 - 1:
        raise ValueError('Cursor de eventos inválido.')
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Límite de eventos inválido.')
    first, last = db.execute('SELECT MIN(seq),MAX(seq) FROM core_events').fetchone()
    rows = db.execute('SELECT seq,topic,entity_id,action,at FROM core_events WHERE seq>? ORDER BY seq LIMIT ?',
                      (after, limit)).fetchall()
    events = [dict(zip(('seq', 'topic', 'entity_id', 'action', 'at'), row)) for row in rows]
    return {'contract': 1, 'events': events, 'cursor': events[-1]['seq'] if events else after,
            'reset_required': bool(first and after < first - 1) or bool(last is not None and after > last),
            'limit': limit}


def read_activity(db, now=None):
    now = time.time() if now is None else now
    rows = db.execute('SELECT client_id,interface,state,updated_at FROM core_activity '
                      'WHERE updated_at>? AND updated_at<=? ORDER BY interface,client_id',
                      (now - 15, now + 1)).fetchall()
    return {'contract': 1, 'clients': [dict(zip(('client_id', 'interface', 'state', 'updated_at'), row))
                                     for row in rows], 'stale_after_seconds': 15}


class CoreActivity:
    """One background heartbeat per classic client; UI calls never open SQLite."""

    def __init__(self, path, on_error=None):
        self.path = Path(path)
        self.client_id = uuid.uuid4().hex
        self.state: CoreState = 'IDLE'
        self.remote = []
        self.on_error = on_error or (lambda: None)
        self.stop = threading.Event()
        self.changed = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name='karen-core-activity')
        self.thread.start()

    def set_state(self, state: CoreState):
        if state not in STATES:
            raise ValueError('Estado Core inválido.')
        if self.state != state:
            self.state = state
            self.changed.set()

    def _run(self):
        failed = False
        while not self.stop.is_set():
            self.changed.clear()
            try:
                with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=0.2)) as db, db:
                    db.execute('INSERT INTO core_activity VALUES (?,?,?,?) ON CONFLICT(client_id) '
                               'DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at',
                               (self.client_id, 'classic', self.state, time.time()))
                    db.execute('DELETE FROM core_activity WHERE updated_at<?', (time.time() - 86400,))
                    self.remote = [c for c in read_activity(db)['clients'] if c['client_id'] != self.client_id]
                failed = False
            except (OSError, sqlite3.Error):
                self.remote = []
                if not failed:
                    self.on_error()
                failed = True
            self.changed.wait(5)
        try:
            with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=0.2)) as db, db:
                db.execute('DELETE FROM core_activity WHERE client_id=?', (self.client_id,))
        except (OSError, sqlite3.Error):
            pass  # An unclean close expires from the public view after 15 seconds.

    def close(self):
        self.stop.set()
        self.changed.set()
