"""Local Karen Core v1 memory store. Model output never grants write permission."""

from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import sqlite3
import uuid

from conversations import Conversations


class MemoryStore:
    def __init__(self, path=None):
        self.path = Conversations(path).path
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS core_memories (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, content TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('confirmed','inferred')),
                sensitive INTEGER NOT NULL CHECK(sensitive IN (0,1)),
                fingerprint TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                expires_at TEXT)''')
            db.execute('CREATE INDEX IF NOT EXISTS core_memories_project ON core_memories(project,updated_at)')
            db.execute('''CREATE TABLE IF NOT EXISTS core_memory_usage (
                id TEXT PRIMARY KEY, memory_id TEXT NOT NULL, chat_id TEXT NOT NULL,
                backend TEXT NOT NULL, used_at TEXT NOT NULL)''')
            # Additive journal: legacy clients keep the same table and contract.
            db.executescript('''
                CREATE TABLE IF NOT EXISTS core_memory_versions (
                    revision INTEGER PRIMARY KEY AUTOINCREMENT, memory_id TEXT NOT NULL,
                    project TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL,
                    sensitive INTEGER NOT NULL, recorded_at TEXT NOT NULL, expires_at TEXT);
                CREATE INDEX IF NOT EXISTS core_memory_versions_id
                    ON core_memory_versions(memory_id,revision);
                INSERT INTO core_memory_versions
                    (memory_id,project,content,status,sensitive,recorded_at,expires_at)
                    SELECT id,project,content,status,sensitive,updated_at,expires_at FROM core_memories m
                    WHERE NOT EXISTS (SELECT 1 FROM core_memory_versions v WHERE v.memory_id=m.id);
                CREATE TRIGGER IF NOT EXISTS core_memory_insert AFTER INSERT ON core_memories BEGIN
                    INSERT INTO core_memory_versions
                        (memory_id,project,content,status,sensitive,recorded_at,expires_at)
                        VALUES (NEW.id,NEW.project,NEW.content,NEW.status,NEW.sensitive,NEW.updated_at,NEW.expires_at);
                END;
                CREATE TRIGGER IF NOT EXISTS core_memory_update AFTER UPDATE ON core_memories BEGIN
                    INSERT INTO core_memory_versions
                        (memory_id,project,content,status,sensitive,recorded_at,expires_at)
                        VALUES (NEW.id,NEW.project,NEW.content,NEW.status,NEW.sensitive,NEW.updated_at,NEW.expires_at);
                END;
                CREATE TRIGGER IF NOT EXISTS core_memory_delete AFTER DELETE ON core_memories BEGIN
                    DELETE FROM core_memory_versions WHERE memory_id=OLD.id;
                    DELETE FROM core_memory_usage WHERE memory_id=OLD.id;
                END;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _project(value):
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 64 or re.search(r'[\x00-\x1f]', value):
            raise ValueError('Proyecto inválido (1 a 64 caracteres).')
        return value.strip()

    @staticmethod
    def _content(value):
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 4000 or '\x00' in value:
            raise ValueError('Recuerdo inválido (1 a 4.000 caracteres).')
        from karen_core2.privacy import ASSIGNMENT
        if ASSIGNMENT.search(value) or 'PRIVATE KEY' in value:
            raise ValueError('No se guardan credenciales en memoria conversacional.')
        return value.strip()

    @staticmethod
    def _fingerprint(project, content):
        normalized = ' '.join(content.casefold().split())
        return hashlib.sha256((project + '\0' + normalized).encode('utf-8')).hexdigest()

    @staticmethod
    def _row(row):
        item = dict(row)
        item['sensitive'] = bool(item['sensitive'])
        return item

    def add(self, project, content, *, confirmed=True, sensitive=False,
            allow_sensitive=False, retention_days=None, _connection=None):
        project, content = self._project(project), self._content(content)
        if type(confirmed) is not bool or type(sensitive) is not bool:
            raise ValueError('Estado y sensibilidad deben ser booleanos.')
        if sensitive and not allow_sensitive:
            raise PermissionError('El almacenamiento sensible está desactivado.')
        if retention_days is not None and (type(retention_days) is not int or not 1 <= retention_days <= 3650):
            raise ValueError('Retención inválida (1 a 3.650 días).')
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=retention_days)).isoformat() if retention_days else None
        fingerprint = self._fingerprint(project, content)
        with (self.connect() if _connection is None else nullcontext(_connection)) as db:
            row = db.execute('SELECT * FROM core_memories WHERE fingerprint=?', (fingerprint,)).fetchone()
            if row:
                if row['expires_at'] and row['expires_at'] <= now.isoformat():
                    db.execute('''UPDATE core_memories SET content=?, status=?, sensitive=?,
                        updated_at=?, expires_at=? WHERE id=?''',
                        (content, 'confirmed' if confirmed else 'inferred', int(sensitive),
                         now.isoformat(), expires, row['id']))
                    return self._row(db.execute('SELECT * FROM core_memories WHERE id=?', (row['id'],)).fetchone())
                if row['sensitive'] and not allow_sensitive:
                    raise PermissionError('Se requiere acceso sensible explícito.')
                # An explicit sensitive write must never return a public duplicate.
                if (sensitive and not row['sensitive']) or (confirmed and row['status'] == 'inferred'):
                    db.execute('''UPDATE core_memories SET sensitive=?, status=?, updated_at=? WHERE id=?''',
                               (int(bool(row['sensitive']) or sensitive),
                                'confirmed' if confirmed else row['status'], now.isoformat(), row['id']))
                    return self._row(db.execute('SELECT * FROM core_memories WHERE id=?', (row['id'],)).fetchone())
                return self._row(row)
            memory_id = uuid.uuid4().hex
            db.execute('''INSERT INTO core_memories VALUES (?,?,?,?,?,?,?,?,?)''',
                       (memory_id, project, content, 'confirmed' if confirmed else 'inferred',
                        int(sensitive), fingerprint, now.isoformat(), now.isoformat(), expires))
            return self._row(db.execute('SELECT * FROM core_memories WHERE id=?', (memory_id,)).fetchone())

    def list(self, project, query='', *, include_sensitive=False, limit=100):
        project = self._project(project)
        if not isinstance(query, str) or len(query) > 200:
            raise ValueError('Búsqueda inválida.')
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Límite inválido.')
        needle = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        with self.connect() as db:
            rows = db.execute('''SELECT * FROM core_memories WHERE project=?
                AND (expires_at IS NULL OR expires_at>?)
                AND (? OR sensitive=0) AND content LIKE ? ESCAPE '\\'
                ORDER BY updated_at DESC,id DESC LIMIT ?''',
                (project, datetime.now(timezone.utc).isoformat(), int(include_sensitive),
                 '%' + needle + '%', limit)).fetchall()
        return [self._row(row) for row in rows]

    def get(self, memory_id, *, include_sensitive=False):
        with self.connect() as db:
            row = db.execute('''SELECT * FROM core_memories WHERE id=?
                AND (expires_at IS NULL OR expires_at>?)''',
                (memory_id, datetime.now(timezone.utc).isoformat())).fetchone()
        if not row or (row['sensitive'] and not include_sensitive):
            return None
        return self._row(row)

    def edit(self, memory_id, content, *, confirmed=None, allow_sensitive=False):
        content = self._content(content)
        if confirmed is not None and type(confirmed) is not bool:
            raise ValueError('Estado inválido.')
        with self.connect() as db:
            row = db.execute('SELECT * FROM core_memories WHERE id=?', (memory_id,)).fetchone()
            if not row:
                raise KeyError('Recuerdo desconocido.')
            if row['sensitive'] and not allow_sensitive:
                raise PermissionError('Se requiere acceso sensible explícito.')
            try:
                db.execute('''UPDATE core_memories SET content=?, fingerprint=?, status=?, updated_at=? WHERE id=?''',
                           (content, self._fingerprint(row['project'], content),
                            row['status'] if confirmed is None else 'confirmed' if confirmed else 'inferred',
                            datetime.now(timezone.utc).isoformat(), memory_id))
            except sqlite3.IntegrityError as exc:
                raise ValueError('Ya existe ese recuerdo en el proyecto.') from exc
            return self._row(db.execute('SELECT * FROM core_memories WHERE id=?', (memory_id,)).fetchone())

    def delete(self, memory_id, *, allow_sensitive=False):
        with self.connect() as db:
            row = db.execute('SELECT sensitive FROM core_memories WHERE id=?', (memory_id,)).fetchone()
            if not row:
                return False
            if row['sensitive'] and not allow_sensitive:
                raise PermissionError('Se requiere acceso sensible explícito.')
            db.execute('DELETE FROM core_memories WHERE id=?', (memory_id,))
            return True

    def export_json(self, project, *, include_sensitive=False):
        project = self._project(project)
        with self.connect() as db:
            rows = db.execute('''SELECT * FROM core_memories WHERE project=?
                AND (expires_at IS NULL OR expires_at>?) AND (? OR sensitive=0)
                ORDER BY updated_at DESC,id DESC''',
                (project, datetime.now(timezone.utc).isoformat(), int(include_sensitive))).fetchall()
        return json.dumps({'contract': 1, 'project': project,
                           'memories': [self._row(row) for row in rows]},
                          ensure_ascii=False, indent=2)

    def log_transfer(self, rows, chat_id, backend):
        if (not isinstance(rows, list) or not 1 <= len(rows) <= 3 or
            any(not isinstance(row, tuple) or len(row) != 2 or
                not isinstance(row[0], str) or not re.fullmatch(r'[0-9a-f]{32}', row[0]) or
                not isinstance(row[1], str) for row in rows) or
            not isinstance(chat_id, str) or not re.fullmatch(r'(?:[0-9a-f]{32}|openclaw-[0-9a-f]{32})', chat_id) or
            backend not in {'ollama', 'karen'}):
            raise ValueError('Registro de uso inválido.')
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for memory_id, content in rows:
                current = db.execute('''SELECT content,status,sensitive,expires_at FROM core_memories
                    WHERE id=?''', (memory_id,)).fetchone()
                if (not current or current['content'] != content or current['status'] != 'confirmed' or
                    current['sensitive'] or
                    (current['expires_at'] and current['expires_at'] <= now)):
                    raise ValueError('La memoria cambió antes del envío; prepara de nuevo.')
                db.execute('INSERT INTO core_memory_usage VALUES (?,?,?,?,?)',
                           (uuid.uuid4().hex, memory_id, chat_id, backend, now))


def memory_command(prompt, store):
    """Handle explicit chat commands locally; never pass them to a model."""
    if not re.match(r'^/memoria(?:\s|$)', prompt.strip(), re.IGNORECASE):
        return None
    command = prompt.strip()[8:].strip()
    action, _, argument = command.partition(' ')
    action, argument = action.lower(), argument.strip()
    try:
        if action in {'guardar', 'buscar', 'editar'}:
            left, separator, right = argument.partition('|')
            if not separator or not left.strip() or not right.strip():
                raise ValueError('Usa proyecto o ID | texto.')
            if action == 'guardar':
                saved = store.add(left, right, confirmed=True)
                return f"Memoria guardada en {saved['project']}. ID: {saved['id']}."
            if action == 'editar':
                saved = store.edit(left.strip(), right)
                return f"Memoria editada. ID: {saved['id']}."
            argument, query = left.strip(), right.strip()
        else:
            query = ''
        if action in {'listar', 'buscar'}:
            rows = store.list(argument, query, limit=10)
            if not rows:
                return 'No encontré recuerdos en ese proyecto.'
            return '\n'.join(f"{row['id']} [{row['status']}]: {row['content'][:1000]}"
                             for row in rows)
        if action == 'borrar':
            if not re.fullmatch(r'[0-9a-f]{32}', argument):
                raise ValueError('Indica el ID completo del recuerdo.')
            return 'Memoria borrada.' if store.delete(argument) else 'No encontré ese recuerdo.'
        return ('Comandos: /memoria guardar PROYECTO | TEXTO; '
                '/memoria listar PROYECTO; /memoria buscar PROYECTO | TEXTO; '
                '/memoria editar ID | TEXTO; /memoria borrar ID.')
    except (ValueError, KeyError, PermissionError) as exc:
        return f'Memoria: {exc}'
    except sqlite3.Error:
        return 'Memoria: no se pudo acceder al almacén local.'
