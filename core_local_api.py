"""Opt-in, loopback-only, read-only Karen Core HTTP contract v1.

This is a local client bridge. Remote transport and tool execution are out of scope.
"""

import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import re
import secrets
import sqlite3
from datetime import datetime, timezone
import hashlib
import uuid
from urllib.parse import parse_qsl, urlsplit

from conversations import DEFAULT_PATH
from karen_tasks import task_database_path
from karen_alerts import DEFAULT_PATH as DEFAULT_ALERT_PATH


TOKEN_FILE = Path(__file__).resolve().parent / '.private' / 'core-api.dpapi'
CLIENTS_FILE = Path(__file__).resolve().parent / '.private' / 'core-api-clients.sqlite3'
CHAT_ID = re.compile(r'[0-9a-f]{32}')
CONVERSATION_ID = re.compile(r'(?:openclaw-)?[0-9a-f]{32}')


class InvalidRequest(Exception):
    pass


def _crypt(data, decrypt=False):
    # Reuse the existing Windows-user DPAPI implementation. No plaintext file.
    from icloud_calendar import crypt
    return crypt(data, decrypt=decrypt)


def save_token(token_file=TOKEN_FILE):
    token_file = Path(token_file)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    encrypted = _crypt(token.encode('ascii'))
    temporary = token_file.with_suffix('.tmp')
    try:
        temporary.write_bytes(encrypted)
        temporary.replace(token_file)
    finally:
        temporary.unlink(missing_ok=True)
    return token


def load_token(token_file=TOKEN_FILE):
    token_file = Path(token_file)
    if not token_file.is_file():
        raise FileNotFoundError('Falta token Core API. Ejecuta: python core_local_api.py init')
    token = _crypt(token_file.read_bytes(), decrypt=True).decode('ascii')
    if len(token) < 32:
        raise ValueError('Token Core API inválido.')
    return token


class ClientRegistry:
    """Per-client read credentials; only hashes enter the registry."""

    def __init__(self, path=CLIENTS_FILE):
        self.path = Path(path)

    def issue(self, name, scope='core.read'):
        if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 64 or
                re.search(r'[\x00-\x1f\x7f]', name)):
            raise ValueError('Nombre de cliente inválido (1 a 64 caracteres).')
        if scope not in {'core.read', 'core.status'}:
            raise ValueError('Permiso de cliente inválido.')
        name = name.strip()
        token = secrets.token_urlsafe(32)
        client_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
                scope TEXT NOT NULL CHECK(scope='core.read'),
                created_at TEXT NOT NULL, revoked_at TEXT)''')
            # Existing registries have only the original core.read column.
            columns = {row[1] for row in db.execute('PRAGMA table_info(clients)')}
            if 'permission' not in columns:
                db.execute("ALTER TABLE clients ADD COLUMN permission TEXT NOT NULL DEFAULT 'core.read' "
                           "CHECK(permission IN ('core.read','core.status'))")
            db.execute('''INSERT INTO clients
                (id,name,token_hash,scope,created_at,revoked_at,permission)
                VALUES (?,?,?,?,?,NULL,?)''',
                       (client_id, name, hashlib.sha256(token.encode('ascii')).hexdigest(),
                        'core.read', now, scope))
        return {'id': client_id, 'name': name, 'token': token, 'scope': scope}

    def verify(self, token):
        if not self.path.is_file() or not isinstance(token, str) or len(token) < 32:
            return None
        digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        try:
            # A damaged registry must fail closed without holding the HTTP thread.
            with self.path.open('rb') as source:
                if source.read(16) != b'SQLite format 3\x00':
                    return None
            db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=0.5)
            with closing(db):
                columns = {row[1] for row in db.execute('PRAGMA table_info(clients)')}
                permission = 'permission' if 'permission' in columns else 'scope'
                row = db.execute(f"SELECT token_hash,{permission} FROM clients WHERE token_hash=? AND revoked_at IS NULL",
                                 (digest,)).fetchone()
            return row[1] if row and hmac.compare_digest(row[0], digest) and row[1] in {'core.read', 'core.status'} else None
        except (OSError, sqlite3.Error):
            return None

    def revoke(self, client_id):
        if not isinstance(client_id, str) or not CHAT_ID.fullmatch(client_id):
            raise ValueError('ID de cliente inválido.')
        if not self.path.is_file():
            return False
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            result = db.execute('UPDATE clients SET revoked_at=? WHERE id=? AND revoked_at IS NULL',
                                (datetime.now(timezone.utc).isoformat(), client_id))
            return result.rowcount == 1

    def list(self):
        if not self.path.is_file():
            return []
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            columns = {row[1] for row in db.execute('PRAGMA table_info(clients)')}
            permission = 'permission' if 'permission' in columns else 'scope'
            rows = db.execute(f'SELECT id,name,{permission},created_at,revoked_at FROM clients ORDER BY created_at DESC').fetchall()
        return [dict(zip(('id', 'name', 'scope', 'created_at', 'revoked_at'), row)) for row in rows]


def _open_readonly(db_path):
    path = Path(db_path).resolve(strict=True)
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    version = db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()
    if not version or version[0] != '1':
        db.close()
        raise ValueError('Versión de Karen Core no compatible.')
    return db


def read_contract(db_path, path, task_db_path=None,
                  alert_db_path=DEFAULT_ALERT_PATH):
    """Return a bounded public contract; never create or mutate the database."""
    if path == '/v1/plans' or re.fullmatch(r'/v1/plans/[0-9a-f]{32}', path):
        from karen_core2.api import read_plans
        return read_plans(task_database_path(task_db_path), path)
    if path == '/v1/activity' or path == '/v1/events' or path.startswith('/v1/events?'):
        from core_events import read_activity, read_events
        parsed = urlsplit(path)
        after = 0
        if parsed.path == '/v1/events':
            try:
                params = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
                if params:
                    if len(params) != 1 or params[0][0] != 'after' or not re.fullmatch(r'[0-9]{1,19}', params[0][1]):
                        raise ValueError('Cursor inválido.')
                    after = int(params[0][1])
                    if after > 2**63 - 1:
                        raise ValueError('Cursor inválido.')
            except ValueError as exc:
                raise InvalidRequest('Cursor inválido.') from exc
        with closing(_open_readonly(db_path)) as db:
            return read_activity(db) if parsed.path == '/v1/activity' else read_events(db, after)
    if path == '/v1/alerts':
        with closing(sqlite3.connect(Path(alert_db_path).resolve(strict=True).as_uri() + '?mode=ro',
                                     uri=True, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            version = db.execute("SELECT value FROM alert_meta WHERE key='schema_version'").fetchone()
            if not version or version[0] != '1':
                raise ValueError('Versión de alertas no compatible.')
            rows = db.execute('''SELECT id,priority,substr(label,1,120) AS label,value,
                observed_at,created_at,status,resolved_at FROM alerts
                ORDER BY created_at DESC,rowid DESC LIMIT 50''').fetchall()
            return {'contract': 1, 'alerts': [dict(row) for row in rows], 'limit': 50}
    if path.startswith('/v1/memories'):
        parsed = urlsplit(path)
        if parsed.path != '/v1/memories' or parsed.fragment:
            return None
        try:
            params = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise InvalidRequest('Consulta inválida.') from exc
        if len(params) != 1 or params[0][0] != 'project':
            raise InvalidRequest('Proyecto requerido.')
        from karen_memory import MemoryStore
        try:
            project = MemoryStore._project(params[0][1])
        except ValueError as exc:
            raise InvalidRequest('Proyecto inválido.') from exc
        with closing(_open_readonly(db_path)) as db:
            rows = db.execute('''SELECT id,project,substr(content,1,4000) AS content,
                status,updated_at,expires_at FROM core_memories
                WHERE project=? AND sensitive=0 AND (expires_at IS NULL OR expires_at>?)
                ORDER BY updated_at DESC,id DESC LIMIT 50''',
                (project, datetime.now(timezone.utc).isoformat())).fetchall()
            return {'contract': 1, 'project': project,
                    'memories': [dict(row) for row in rows], 'limit': 50}
    if path == '/v1/tasks' or re.fullmatch(r'/v1/tasks/[0-9a-f]{32}', path):
        task_db_path = task_database_path(task_db_path)
        with closing(sqlite3.connect(Path(task_db_path).resolve(strict=True).as_uri() + '?mode=ro',
                                     uri=True, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            if path == '/v1/tasks':
                rows = db.execute('''SELECT id,status,cursor,created_at,updated_at FROM task_jobs
                    ORDER BY updated_at DESC,id DESC LIMIT 50''').fetchall()
                return {'contract': 1, 'tasks': [dict(row) for row in rows], 'limit': 50}
            task_id = path.split('/')[-1]
            row = db.execute('''SELECT id,status,cursor,cancel_requested,created_at,updated_at
                FROM task_jobs WHERE id=?''', (task_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result['cancel_requested'] = bool(result['cancel_requested'])
            result['steps'] = [dict(step) for step in db.execute('''SELECT ordinal,tool,permission,status
                FROM task_steps WHERE task_id=? ORDER BY ordinal LIMIT 32''', (task_id,))]
            return {'contract': 1, 'task': result}
    if path not in ('/v1/status', '/v1/chats') and not re.fullmatch(r'/v1/chats/(?:openclaw-)?[0-9a-f]{32}/exchanges', path):
        return None
    with closing(_open_readonly(db_path)) as db:
        if path == '/v1/status':
            active = db.execute("SELECT value FROM preferences WHERE key='active'").fetchone()
            mode = db.execute("SELECT value FROM preferences WHERE key='core.mode'").fetchone()
            return {'contract': 1, 'active_chat_id': active[0] if active and CONVERSATION_ID.fullmatch(active[0]) else None,
                    'mode': mode[0] if mode and mode[0] in {'normal', 'gaming', 'do_not_disturb'} else 'normal'}
        if path == '/v1/chats':
            rows = db.execute('SELECT id,title,updated FROM chats ORDER BY updated DESC,rowid DESC LIMIT 50').fetchall()
            return {'contract': 1, 'chats': [dict(row) for row in rows], 'limit': 50}
        chat_id = path.split('/')[3]
        if not db.execute('SELECT 1 FROM chats WHERE id=?', (chat_id,)).fetchone():
            return None
        rows = db.execute('''SELECT id,substr(prompt,1,4000) AS prompt,
            substr(answer,1,4000) AS answer,ok FROM exchanges WHERE chat_id=?
            ORDER BY id DESC LIMIT 20''', (chat_id,)).fetchall()
        return {'contract': 1, 'chat_id': chat_id, 'exchanges': [dict(row) for row in reversed(rows)],
                'limit': 20, 'text_limit': 4000}


def make_handler(db_path, token, clients_path=CLIENTS_FILE,
                 task_db_path=None, alert_db_path=DEFAULT_ALERT_PATH):
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError('Token Core API inválido.')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_args):
            pass

        def reply(self, code, payload):
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Client disconnected; no request or token enters logs.

        def do_GET(self):
            supplied = self.headers.get('Authorization', '')
            client_token = supplied[7:] if supplied.startswith('Bearer ') else ''
            scope = ('core.read' if hmac.compare_digest(supplied, 'Bearer ' + token)
                     else ClientRegistry(clients_path).verify(client_token))
            if scope is None:
                return self.reply(401, {'error': 'Autenticación requerida.'})
            if scope == 'core.status' and self.path != '/v1/status':
                return self.reply(403, {'error': 'Permiso insuficiente.'})
            if ('?' in self.path and not self.path.startswith(('/v1/memories?', '/v1/events?'))) or '#' in self.path:
                return self.reply(400, {'error': 'Ruta inválida.'})
            try:
                result = read_contract(db_path, self.path, task_db_path, alert_db_path)
            except InvalidRequest:
                return self.reply(400, {'error': 'Solicitud inválida.'})
            except (OSError, sqlite3.Error, ValueError):
                return self.reply(503, {'error': 'Karen Core no está disponible.'})
            if result is None:
                return self.reply(404, {'error': 'Ruta o chat desconocido.'})
            self.reply(200, result)

        def do_POST(self):
            self.reply(405, {'error': 'API de solo lectura.'})

        do_PUT = do_PATCH = do_DELETE = do_POST

    return Handler


def serve(db_path=DEFAULT_PATH, token_file=TOKEN_FILE, port=18792,
          clients_path=CLIENTS_FILE, alert_db_path=DEFAULT_ALERT_PATH):
    if not Path(db_path).is_absolute():
        raise ValueError('KAREN_CORE_DB debe ser una ruta absoluta.')
    token = load_token(token_file)
    # Fixed loopback bind; no host override or public listener.
    server = ThreadingHTTPServer(('127.0.0.1', port),
                                 make_handler(db_path, token, clients_path,
                                              None, alert_db_path))
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description='Puente local de solo lectura de Karen Core')
    parser.add_argument('action', choices=('init', 'token', 'rotate', 'serve', 'issue', 'revoke', 'clients'))
    parser.add_argument('value', nargs='?')
    parser.add_argument('--scope', choices=('read', 'status'), default='read')
    parser.add_argument('--port', type=int, default=18792)
    args = parser.parse_args()
    if args.action == 'init':
        if TOKEN_FILE.exists():
            print('Token ya existe. Usa token para verlo o rotate para revocarlo.')
        else:
            save_token()
            print('Token Core API creado con DPAPI. Usa token para verlo.')
    elif args.action == 'token':
        print(load_token())
    elif args.action == 'rotate':
        save_token()
        print('Token rotado. Reinicia el servidor para revocar el anterior.')
    elif args.action == 'issue':
        if not args.value:
            parser.error('Indica un nombre de cliente.')
        client = ClientRegistry().issue(args.value, 'core.' + args.scope)
        print(f"Cliente: {client['id']} ({client['name']}, {client['scope']})")
        print(f"Token (se muestra una vez): {client['token']}")
    elif args.action == 'revoke':
        if not args.value:
            parser.error('Indica el ID completo del cliente.')
        print('Cliente revocado.' if ClientRegistry().revoke(args.value) else 'Cliente inexistente o ya revocado.')
    elif args.action == 'clients':
        for client in ClientRegistry().list():
            print(f"{client['id']} {client['name']} {client['scope']} "
                  f"{'revocado' if client['revoked_at'] else 'activo'}")
    else:
        from os import getenv
        db_path = getenv('KAREN_CORE_DB') or DEFAULT_PATH
        if not 1 <= args.port <= 65535:
            parser.error('Puerto inválido.')
        print(f'Karen Core API: http://127.0.0.1:{args.port}/v1/status')
        serve(db_path, port=args.port)


if __name__ == '__main__':
    main()
