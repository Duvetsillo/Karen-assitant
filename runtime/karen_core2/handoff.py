"""Structured development requests in existing SQLite; no private Codex session access."""
from datetime import datetime, timezone
import json
from pathlib import PurePosixPath
import re
import uuid

from .privacy import ASSIGNMENT, fingerprint, seal, unseal

STATES = {'pending', 'active', 'needs_validation', 'complete', 'blocked'}


class Handoffs:
    def __init__(self, memory_store):
        self.store = memory_store
        with self.store.connect() as db:
            row = db.execute("SELECT value FROM core_meta WHERE key='handoff_version'").fetchone()
            if row and row[0] != '1':
                raise ValueError('Versión de handoff incompatible.')
            db.execute("INSERT OR IGNORE INTO core_meta VALUES('handoff_version','1')")
            db.execute('''CREATE TABLE IF NOT EXISTS core2_handoffs (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, status TEXT NOT NULL,
                priority TEXT NOT NULL, updated_at TEXT NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL)''')

    @staticmethod
    def validate(data):
        required = {'id', 'project', 'description', 'priority', 'context', 'acceptance', 'status',
                    'files', 'test_results', 'date', 'blockers'}
        if not isinstance(data, dict) or set(data) != required:
            raise ValueError('Campos del handoff inválidos.')
        if not isinstance(data['id'], str) or not re.fullmatch('[0-9a-f]{32}', data['id']):
            raise ValueError('ID de handoff inválido.')
        if (not isinstance(data['status'], str) or data['status'] not in STATES or
                not isinstance(data['priority'], str) or data['priority'] not in {'low', 'normal', 'high'}):
            raise ValueError('Estado o prioridad inválido.')
        for key in ('project', 'description', 'context', 'date'):
            if not isinstance(data[key], str) or len(data[key]) > 8000 or '\0' in data[key]:
                raise ValueError('Texto de handoff inválido.')
        if not data['project'].strip() or not data['description'].strip():
            raise ValueError('Proyecto y descripción son obligatorios.')
        datetime.fromisoformat(data['date'])
        for key in ('acceptance', 'files', 'test_results', 'blockers'):
            if (not isinstance(data[key], list) or len(data[key]) > 50 or
                    any(not isinstance(item, str) or not item.strip() or len(item) > 2000 or '\0' in item for item in data[key])):
                raise ValueError('Lista de handoff inválida.')
        if not data['acceptance'] or data['status'] == 'complete' and not data['test_results']:
            raise ValueError('Requiere criterios de aceptación; completar requiere resultados de pruebas.')
        for name in data['files']:
            path = PurePosixPath(name)
            if path.is_absolute() or '\\' in name or ':' in name or any(p in {'.', '..'} or p.startswith('.') for p in path.parts):
                raise ValueError('Archivos del handoff deben ser rutas relativas públicas del proyecto.')
        raw = json.dumps(data, ensure_ascii=False)
        if len(raw.encode('utf-8')) > 65536 or ASSIGNMENT.search(raw) or 'PRIVATE KEY' in raw:
            raise ValueError('Handoff demasiado grande o con posibles credenciales.')

    def create(self, *, project, description, acceptance, priority='normal', context='', files=None):
        data = {'id': uuid.uuid4().hex, 'project': project, 'description': description, 'priority': priority,
                'context': context, 'acceptance': acceptance, 'status': 'pending', 'files': [] if files is None else files,
                'test_results': [], 'date': datetime.now(timezone.utc).isoformat(), 'blockers': []}
        self.validate(data)
        with self.store.connect() as db:
            db.execute('INSERT INTO core2_handoffs VALUES(?,?,?,?,?,?,?)',
                       (data['id'], project, 'pending', priority, data['date'], fingerprint(data), seal(data)))
        return self.read(data['id'])

    def read(self, identity):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
            raise ValueError('ID de handoff inválido.')
        with self.store.connect() as db:
            row = db.execute('SELECT hash,payload FROM core2_handoffs WHERE id=?', (identity,)).fetchone()
        if not row:
            raise ValueError('Handoff desconocido.')
        return {'task': unseal(row['payload']), 'hash': row['hash'], 'trust': 'reported_data'}

    def list(self):
        with self.store.connect() as db:
            return [dict(row) for row in db.execute(
                'SELECT id,project,status,priority,updated_at,hash FROM core2_handoffs ORDER BY updated_at DESC LIMIT 100')]

    def update(self, *, id, expected_hash, status, test_results, blockers):
        if (not isinstance(id, str) or not re.fullmatch('[0-9a-f]{32}', id) or
                not isinstance(expected_hash, str) or not re.fullmatch('[0-9a-f]{64}', expected_hash)):
            raise ValueError('ID o hash de handoff inválido.')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT hash,payload FROM core2_handoffs WHERE id=?', (id,)).fetchone()
            if not row or row['hash'] != expected_hash:
                raise ValueError('Handoff desconocido o modificado; vuelve a leer.')
            data = unseal(row['payload'])
            data.update(status=status, test_results=test_results, blockers=blockers, date=datetime.now(timezone.utc).isoformat())
            self.validate(data)
            db.execute('UPDATE core2_handoffs SET status=?,updated_at=?,hash=?,payload=? WHERE id=?',
                       (status, data['date'], fingerprint(data), seal(data), id))
        return self.read(id)


def command(bridge, text):
    if not (text == '/handoff' or text.startswith('/handoff ')):
        return None
    parts = text.split(maxsplit=2)
    action = parts[1] if len(parts) > 1 else 'list'
    args = json.loads(parts[2]) if len(parts) > 2 else {}
    if not isinstance(args, dict):
        raise ValueError('Handoff requiere un objeto JSON.')
    allowed = {'list': (bridge.list, set(), set()), 'read': (bridge.read, {'identity'}, {'identity'}),
               'create': (bridge.create, {'project', 'description', 'acceptance'},
                          {'project', 'description', 'acceptance', 'priority', 'context', 'files'}),
               'update': (bridge.update, {'id', 'expected_hash', 'status', 'test_results', 'blockers'},
                          {'id', 'expected_hash', 'status', 'test_results', 'blockers'})}
    if action not in allowed:
        raise ValueError('Operación handoff desconocida.')
    handler, required, fields = allowed[action]
    if required - args.keys() or args.keys() - fields:
        raise ValueError('Parámetros handoff ausentes o desconocidos.')
    return json.dumps(handler(**args), ensure_ascii=False, indent=2)
