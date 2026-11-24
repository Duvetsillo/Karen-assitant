"""Private iPhone bridge: fixed app preset, expiring approval, no arbitrary commands."""
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / '.private'
CONFIG = PRIVATE / 'iphone-routines.json'
PROTECTED_CONFIG = PRIVATE / 'iphone-routines.dpapi'
DATABASE = PRIVATE / 'iphone-routines.sqlite3'
LABELS = ['ChatGPT', 'Obsidian', 'Spotify']
# Identifiers read from Get-StartApps on this Windows installation.
APP_IDS = ['OpenAI.Codex_2p2nqsd0c76g0!App', 'md.obsidian',
           'SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify']


def launch_apps():
    results = []
    for label, app_id in zip(LABELS, APP_IDS):
        try:
            subprocess.Popen(['explorer.exe', 'shell:AppsFolder\\' + app_id],
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            results.append({'app': label, 'status': 'solicitado'})
        except OSError:
            results.append({'app': label, 'status': 'fallido'})
    return results


class Routines:
    def __init__(self, database=DATABASE, launcher=launch_apps, now=time.time):
        self.database, self.launcher, self.now = database, launcher, now
        self.lock = threading.Lock()
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS plans '
                       '(ticket TEXT PRIMARY KEY, created REAL, expires REAL, '
                       'status TEXT, result TEXT)')

    def prepare(self):
        with self.lock, closing(sqlite3.connect(self.database)) as db, db:
            now = self.now()
            # Arrival retries reuse a still-pending plan, rather than adding prompts.
            row = db.execute("SELECT ticket,expires FROM plans WHERE status='pending' "
                             'AND expires>? ORDER BY created DESC LIMIT 1', (now,)).fetchone()
            if not row:
                row = (secrets.token_urlsafe(24), now + 300)
                db.execute('INSERT INTO plans VALUES (?,?,?,?,?)',
                           (row[0], now, row[1], 'pending', None))
        return {'ticket': row[0], 'expires_in': int(row[1] - now), 'apps': LABELS,
                'question': '¿Abrir ChatGPT, Obsidian y Spotify en la PC?'}

    def confirm(self, ticket, confirmed):
        if not isinstance(ticket, str) or not 1 <= len(ticket) <= 100 or type(confirmed) is not bool:
            raise ValueError('Se requiere ticket y confirmed de tipo booleano.')
        with self.lock, closing(sqlite3.connect(self.database)) as db, db:
            row = db.execute('SELECT expires,status,result FROM plans WHERE ticket=?',
                             (ticket,)).fetchone()
            if not row:
                raise ValueError('Solicitud desconocida.')
            expires, status, result = row
            if status != 'pending':
                return {'status': status, 'repeated': True,
                        'apps': json.loads(result) if result else []}
            if expires <= self.now():
                db.execute("UPDATE plans SET status='expired' WHERE ticket=?", (ticket,))
                return {'status': 'expired', 'message': 'Vuelve a solicitar confirmación.'}
            if not confirmed:
                db.execute("UPDATE plans SET status='cancelled' WHERE ticket=?", (ticket,))
                return {'status': 'cancelled', 'message': 'No se abrió ninguna aplicación.'}
            # Commit before dispatch: a timeout or restart must never replay launches.
            db.execute("UPDATE plans SET status='dispatching' WHERE ticket=?", (ticket,))
            db.commit()
        try:
            results = self.launcher()
        except Exception:
            # The launcher may have partially executed: do not retry automatically.
            return {'status': 'dispatching', 'message': 'Resultado incierto. Revisa la PC.'}
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE plans SET status='completed',result=? WHERE ticket=?",
                       (json.dumps(results), ticket))
        return {'status': 'completed', 'apps': results,
                'message': 'Windows recibió la solicitud. No se verificaron las ventanas.'}


def make_handler(routines, token):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_args):
            pass  # Neither credentials nor request bodies enter HTTP logs.

        def reply(self, code, payload):
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            supplied = self.headers.get('Authorization', '')
            return hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode())

        def do_GET(self):
            if self.path == '/health':
                return self.reply(200, {'status': 'ready', 'confirmation_required': True})
            self.reply(405, {'error': 'Las rutinas requieren POST autenticado.'})

        def do_POST(self):
            if not self.authorized():
                return self.reply(401, {'error': 'Autenticación requerida.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.reply(415, {'error': 'Se requiere application/json.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2048:
                    raise ValueError('Tamaño inválido.')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Se requiere un objeto JSON.')
                if self.path == '/prepare' and data == {'routine': 'arrival_apps'}:
                    return self.reply(200, routines.prepare())
                if self.path == '/confirm' and set(data) == {'ticket', 'confirmed'}:
                    return self.reply(200, routines.confirm(data['ticket'], data['confirmed']))
                raise ValueError('Ruta o parámetros no permitidos.')
            except (ValueError, UnicodeDecodeError):
                self.reply(400, {'error': 'Solicitud inválida. No se ejecutó una nueva acción.'})

    return Handler


def _validate_config(config):
    if (not isinstance(config, dict) or not isinstance(config.get('token'), str) or
            len(config['token']) < 32 or type(config.get('port')) is not int or
            not 1 <= config['port'] <= 65535):
        raise ValueError('Configuración del puente iPhone inválida.')
    return {'token': config['token'], 'port': config['port']}


def _protect(data, decrypt=False):
    from icloud_calendar import crypt
    return crypt(data, decrypt=decrypt)


def _write_protected(config, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = _protect(json.dumps(_validate_config(config)).encode('utf-8'))
    temporary = path.with_suffix('.tmp')
    try:
        temporary.write_bytes(blob)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def initialize(config_path=CONFIG, protected_path=PROTECTED_CONFIG):
    """Keep legacy iPhone tokens working; new installations use DPAPI."""
    config_path, protected_path = Path(config_path), Path(protected_path)
    if protected_path.is_file():
        return _validate_config(json.loads(_protect(protected_path.read_bytes(), decrypt=True)))
    if config_path.is_file():
        return _validate_config(json.loads(config_path.read_text(encoding='utf-8-sig')))
    config = {'token': secrets.token_urlsafe(32), 'port': 18791}
    _write_protected(config, protected_path)
    return config


def prepare_legacy_migration(config_path=CONFIG, protected_path=PROTECTED_CONFIG):
    """Explicitly encrypt the existing token without changing or deleting its source."""
    config_path, protected_path = Path(config_path), Path(protected_path)
    if protected_path.exists():
        raise FileExistsError('Ya existe una configuración cifrada.')
    if not config_path.is_file():
        raise FileNotFoundError('No existe configuración anterior.')
    config = _validate_config(json.loads(config_path.read_text(encoding='utf-8-sig')))
    _write_protected(config, protected_path)
    return config


if __name__ == '__main__':
    if sys.argv[1:] == ['--migrate-config']:
        prepare_legacy_migration()
        print('Credencial cifrada creada. Comprueba el iPhone antes de retirar el JSON anterior manualmente.')
        raise SystemExit(0)
    if len(sys.argv) > 1:
        raise SystemExit('Uso: python iphone_routines.py [--migrate-config]')
    cfg = initialize()
    server = ThreadingHTTPServer(('127.0.0.1', cfg['port']),
                                make_handler(Routines(), cfg['token']))
    try:
        server.serve_forever()
    finally:
        server.server_close()
