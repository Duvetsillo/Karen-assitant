"""Karen's opt-in iPhone client. Loopback origin; use Tailscale Serve for HTTPS."""
import argparse
from collections import deque
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import ipaddress
import json
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

import requests

from answers import final_answer
from config import load_config
from conversations import Conversations
from core_local_api import InvalidRequest, load_token, read_contract, save_token
from karen_personality import personality
from mobile_speech import SpeechBusy

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = ROOT / '.private' / 'mobile-access.dpapi'
ASSETS = ROOT / 'mobile'
COOKIE = 'karen_mobile'
LIFETIME = 14 * 86400


def validate_tailnet_origin(value):
    parsed = urlsplit(value)
    try:
        address = ipaddress.ip_address(parsed.hostname or '')
        valid = (address.version == 4 and address in ipaddress.ip_network('100.64.0.0/10')
                 and parsed.scheme == 'http' and parsed.port is not None
                 and not any((parsed.path, parsed.query, parsed.fragment, parsed.username)))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Usa http://IP-TAILSCALE:PUERTO, con IP entre 100.64.0.0 y 100.127.255.255.')
    return value


class MobileApp:
    def __init__(self, archive, config, secret, origin=None, ask=None, tailnet_origin=None, core2=None, ha_key_path=None):
        self.core2 = core2
        from ha_conversation import KEY_PATH
        self.ha_key_path = ha_key_path or KEY_PATH
        self.archive, self.config, self.secret = archive, config, secret
        self.origin = origin
        self.origins = {origin} if origin else set()
        if tailnet_origin:
            self.origins.add(validate_tailnet_origin(tailnet_origin))
        self.ask = ask or self.generate
        self.generation = threading.BoundedSemaphore(1)
        from mobile_speech import MobileSpeech
        self.speech = MobileSpeech()
        self.login_lock = threading.Lock()
        self.attempts = deque(maxlen=30)

    def session(self):
        stamp = str(int(time.time()))
        signature = hmac.new(self.secret.encode(), stamp.encode(), hashlib.sha256).hexdigest()
        return stamp + '.' + signature

    def authenticated(self, raw_cookie):
        try:
            cookie = SimpleCookie(raw_cookie)
            stamp, signature = cookie[COOKIE].value.split('.')
            age = time.time() - int(stamp)
            expected = hmac.new(self.secret.encode(), stamp.encode(), hashlib.sha256).hexdigest()
            return 0 <= age <= LIFETIME and hmac.compare_digest(signature, expected)
        except (CookieError, KeyError, ValueError, AttributeError):
            return False

    def login(self, code):
        with self.login_lock:
            now = time.monotonic()
            while self.attempts and now - self.attempts[0] > 60:
                self.attempts.popleft()
            if len(self.attempts) >= 10:
                return 429
            self.attempts.append(now)
            if not isinstance(code, str) or not hmac.compare_digest(code.encode(), self.secret.encode()):
                return 401
            self.attempts.clear()
            return 200

    def generate(self, chat_id, message):
        if self.core2:
            from karen_core2.models import task_kind, LIGHT_KINDS
            self.speech.prepare_chat(lightweight=task_kind(message) in LIGHT_KINDS)
            answer = self.core2.chat(message, self.archive.context(chat_id), preferred=self.config.model)
            if not isinstance(answer, str):
                raise ValueError('Respuesta Core 2 incompatible.')
            return final_answer(answer)
        config = self.config
        headers = {'Authorization': 'Bearer ' + config.api_key} if config.api_key else {}
        if config.backend == 'karen':
            # Independent session per chat; never borrows a desktop tool session.
            payload = {'mensaje': message, 'session_id': 'mobile-' + chat_id}
            route = '/chat'
        else:
            system = personality(config.voice_style, config.allow_suggestions, config.allow_sarcasm)
            system += (' Estás en el cliente móvil. No dispones de herramientas de control del PC, '
                       'de la casa ni de servidores. Nunca afirmes haber ejecutado acciones.')
            payload = {'model': config.model.removeprefix('ollama/'), 'stream': False,
                       'think': config.model.removeprefix('ollama/').split(':')[0] == 'qwen3',
                       'messages': [{'role': 'system', 'content': system}] +
                       self.archive.context(chat_id) + [{'role': 'user', 'content': message}]}
            route = '/api/chat'
        with requests.post(config.server.rstrip('/') + route, json=payload, headers=headers,
                           timeout=(10, config.request_timeout)) as response:
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError('Respuesta incompatible del modelo.')
        if config.backend == 'karen':
            answer = data.get('respuesta')
        else:
            reply = data.get('message')
            answer = reply.get('content') if isinstance(reply, dict) else None
        if not isinstance(answer, str):
            raise ValueError('Respuesta incompatible del modelo.')
        return final_answer(answer)


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *_args):
            pass  # No transcripts, credentials, or cookies in logs.

        def reply(self, status, payload, mime='application/json; charset=utf-8', cookie=None):
            data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionError):
                pass

        def allowed_host(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            allowed.update(urlsplit(origin).netloc for origin in app.origins)
            return self.headers.get('Host', '') in allowed

        def do_GET(self):
            if self.path.startswith('/api/ha/'):
                return self.ha_request('GET')
            if not self.allowed_host():
                return self.reply(403, {'error': 'Dirección no autorizada.'})
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/jarvis': ('jarvis.html', 'text/html; charset=utf-8'),
                      '/jarvis.css': ('jarvis.css', 'text/css; charset=utf-8'),
                      '/jarvis.js': ('jarvis.js', 'text/javascript; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8'),
                      '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
                      '/sw.js': ('sw.js', 'text/javascript; charset=utf-8'),
                      '/icon.svg': ('icon.svg', 'image/svg+xml'),
                      '/icon-192.png': ('icon-192.png', 'image/png'),
                      '/apple-touch-icon.png': ('apple-touch-icon.png', 'image/png')}
            if self.path in static:
                name, mime = static[self.path]
                return self.reply(200, (ASSETS / name).read_bytes(), mime)
            if not app.authenticated(self.headers.get('Cookie', '')):
                return self.reply(401, {'error': 'Introduce tu código para conectar con Karen.'})
            try:
                if self.path == '/api/session':
                    return self.reply(200, {'model': app.config.model, 'backend': app.config.backend})
                if app.core2 and self.path.startswith('/api/core2/'):
                    parsed = urlsplit(self.path)
                    if parsed.path == '/api/core2/status':
                        return self.reply(200, app.core2.status())
                    if parsed.path == '/api/core2/models':
                        return self.reply(200, {'models': app.core2.models.discover(force=True)})
                    if parsed.path == '/api/core2/plans':
                        return self.reply(200, {'plans': app.core2.plans.list()})
                    if re.fullmatch(r'/api/core2/plans/[0-9a-f]{32}', parsed.path):
                        return self.reply(200, app.core2.plans.inspect(parsed.path.rsplit('/', 1)[-1]))
                    if parsed.path == '/api/core2/memory':
                        from urllib.parse import parse_qs
                        params = parse_qs(parsed.query)
                        return self.reply(200, {'memories': app.core2.memory.retrieve(params.get('project', ['Karen'])[0], params.get('q', [''])[0])})
                    if parsed.path in {'/api/core2/memory/graph', '/api/core2/memory/consolidate'}:
                        from urllib.parse import parse_qs
                        params = parse_qs(parsed.query)
                        method = app.core2.memory.graph if parsed.path.endswith('/graph') else app.core2.memory.consolidate
                        return self.reply(200, method(params.get('project', ['Karen'])[0]))
                    if re.fullmatch(r'/api/core2/memory/[0-9a-f]{32}/(history|procedure)', parsed.path):
                        _, _, _, _, identity, action = parsed.path.split('/')
                        return self.reply(200, getattr(app.core2.memory, action)(identity))
                    if parsed.path == '/api/core2/memory/timeline':
                        from urllib.parse import parse_qs
                        params = parse_qs(parsed.query)
                        return self.reply(200, {'events': app.core2.memory.timeline(params.get('project', ['Karen'])[0],
                            since=params.get('since', [None])[0], until=params.get('until', [None])[0], kind=params.get('kind', [None])[0])})
                    if parsed.path == '/api/core2/home/status':
                        return self.reply(200, app.core2.home_status())
                if self.path.startswith('/api/v1/'):
                    result = read_contract(app.archive.path, self.path[4:])
                    return self.reply(200, result) if result is not None else self.reply(404, {'error': 'No encontrado.'})
                self.reply(404, {'error': 'No encontrado.'})
            except InvalidRequest:
                self.reply(400, {'error': 'Consulta inválida.'})
            except KeyError:
                self.reply(404, {'error': 'Plan o dato desconocido.'})
            except (OSError, sqlite3.Error, ValueError):
                self.reply(503, {'error': 'Estos datos todavía no están disponibles en el PC.'})
            except requests.RequestException:
                self.reply(503, {'error': 'Ollama local no está disponible.'})

        def ha_request(self, method):
            from ha_conversation import credential, converse
            if not self.allowed_host() or self.headers.get('Origin'):
                return self.reply(403, {'error': 'Canal de integración no autorizado.'})
            identity = credential(self.headers.get('Authorization', ''), app.ha_key_path)
            if identity is None:
                return self.reply(401, {'error': 'Conexión de Karen no autorizada.'})
            if method == 'GET' and self.path == '/api/ha/status':
                return self.reply(200, {'name': 'Karen', 'contract': 1, 'scope': 'conversation', 'core': app.core2 is not None, 'voice': True})
            if method == 'POST' and self.path in {'/api/ha/stt', '/api/ha/tts'}:
                if not app.generation.acquire(blocking=False):
                    return self.reply(409, {'error': 'Karen está ocupada.'})
                try:
                    from ha_voice import transcribe, synthesize
                    length = int(self.headers.get('Content-Length', '0'))
                    if self.path.endswith('/stt'):
                        if not 2 <= length <= 1_920_044 or self.headers.get_content_type() not in {'application/octet-stream', 'audio/wav'}:
                            raise ValueError()
                        return self.reply(200, transcribe(self.rfile.read(length)))
                    if not 0 < length <= 10000 or self.headers.get_content_type() != 'application/json':
                        raise ValueError()
                    data = json.loads(self.rfile.read(length))
                    audio = synthesize(app, identity, data)
                    self.reply(200, audio, mime='audio/wav')
                    threading.Thread(target=app.speech.release_idle, daemon=True).start()
                    return
                except (ValueError, UnicodeError):
                    return self.reply(400, {'error': 'Audio o texto no válido.'})
                except (OSError, RuntimeError, TimeoutError, InterruptedError):
                    return self.reply(503, {'error': 'El motor de voz local no está disponible.'})
                finally:
                    app.generation.release()
            if method != 'POST' or self.path != '/api/ha/conversation':
                return self.reply(404, {'error': 'Función fuera del alcance de esta conexión.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20000 or self.headers.get_content_type() != 'application/json':
                    raise ValueError()
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, UnicodeError):
                return self.reply(400, {'error': 'Conversación inválida.'})
            if not app.generation.acquire(blocking=False):
                return self.reply(409, {'error': 'Karen está respondiendo; vuelve a intentar al terminar.'})
            try:
                return self.reply(200, converse(app, identity, data))
            except ValueError:
                return self.reply(400, {'error': 'Consulta o respuesta inválida; no se confirmó el turno.'})
            except (OSError, sqlite3.Error, RuntimeError, KeyError, requests.RequestException):
                return self.reply(503, {'error': 'Karen local no está disponible; revisa el PC y Ollama.'})
            finally:
                app.generation.release()

        def do_POST(self):
            if self.path.startswith('/api/ha/'):
                return self.ha_request('POST')
            local_origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
            local_origins.update(app.origins)
            if not self.allowed_host() or self.headers.get('Origin') not in local_origins:
                return self.reply(403, {'error': 'Origen no autorizado.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32768 or self.headers.get_content_type() != 'application/json':
                    raise ValueError()
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, UnicodeError):
                return self.reply(400, {'error': 'Solicitud inválida.'})
            secure = '; Secure' if self.headers.get('Origin', '').startswith('https://') else ''
            if self.path == '/api/login':
                status = app.login(data.get('code'))
                if status != 200:
                    return self.reply(status, {'error': 'Espera un minuto antes de volver a intentar.' if status == 429 else 'Código incorrecto.'})
                return self.reply(200, {'ok': True}, cookie=f'{COOKIE}={app.session()}; Path=/; HttpOnly; SameSite=Strict; Max-Age={LIFETIME}{secure}')
            if not app.authenticated(self.headers.get('Cookie', '')):
                return self.reply(401, {'error': 'Vuelve a conectar con tu código.'})
            if self.path == '/api/logout':
                return self.reply(200, {'ok': True}, cookie=f'{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0{secure}')
            if self.path in {'/api/speech', '/api/speech/cancel', '/api/speech/release'}:
                try:
                    owner = self.headers.get('Cookie', '')
                    if self.path.endswith('/release') and not data:
                        released = app.speech.release_idle()
                        return self.reply(200 if released else 409, {'released': released})
                    if self.path.endswith('/cancel') and set(data) == {'id'}:
                        return self.reply(200, app.speech.cancel(owner, data['id']))
                    if self.path == '/api/speech' and set(data) == {'id', 'text'}:
                        return self.reply(200, app.speech.render(owner, data['id'], data['text']), 'audio/wav')
                    raise ValueError()
                except SpeechBusy:
                    return self.reply(409, {'error': 'La voz local está ocupada. Espera o detén la lectura actual.'})
                except InterruptedError:
                    return self.reply(409, {'error': 'Lectura cancelada o tiempo de voz agotado.'})
                except ValueError:
                    return self.reply(400, {'error': 'Solicitud de voz inválida o audio no disponible.'})
                except Exception:
                    return self.reply(503, {'error': 'La voz local de Karen no pudo generar audio. Revisa el servicio de voz en el PC.'})
            if app.core2 and self.path.startswith('/api/core2/'):
                try:
                    if self.path == '/api/core2/plan' and set(data) == {'goal'}:
                        if not isinstance(data['goal'], str) or not 1 <= len(data['goal']) <= 2000:
                            raise ValueError()
                        return self.reply(201, app.core2.create_plan(data['goal']))
                    if self.path in {'/api/core2/run', '/api/core2/cancel', '/api/core2/resume', '/api/core2/remember'} and set(data) == {'id'}:
                        identity = data['id']
                        if self.path.endswith('/cancel'):
                            result = app.core2.plans.cancel(identity)
                        elif self.path.endswith('/remember'):
                            result = app.core2.memory.record_procedure(app.core2.plans.inspect(identity))
                        else:
                            # Remote clients never get an implicit write approval.
                            result = app.core2.plans.run(identity, resume=self.path.endswith('/resume'), actor='authenticated-mobile')
                        return self.reply(200, result)
                    if self.path == '/api/core2/vision' and set(data) == {'scope'} and data['scope'] in {'window', 'screen'}:
                        app.core2.vision.pause(False)
                        try:
                            return self.reply(200, app.core2.vision.analyze(scope=data['scope']))
                        finally:
                            app.core2.vision.pause()
                    if self.path == '/api/core2/vision/pause' and not data:
                        return self.reply(200, app.core2.vision.pause())
                    return self.reply(400, {'error': 'Operación Core 2 inválida.'})
                except (ValueError, KeyError, PermissionError):
                    return self.reply(400, {'error': 'Revisa el plan, los parámetros y los permisos.'})
                except Exception as exc:
                    return self.reply(503, {'error': 'Core 2 no pudo completar la operación (' + type(exc).__name__ + ').'})
            if self.path == '/api/chats':
                # Create without stealing the desktop's active-chat preference.
                chat_id = secrets.token_hex(16)
                with app.archive.connect() as db:
                    db.execute('INSERT INTO chats (id,title) VALUES (?,?)', (chat_id, 'Nueva conversación'))
                return self.reply(201, {'id': chat_id})
            if self.path != '/api/message':
                return self.reply(404, {'error': 'No encontrado.'})
            chat_id, message = data.get('chat_id'), data.get('message')
            if (not isinstance(chat_id, str) or not re.fullmatch(r'(?:openclaw-)?[0-9a-f]{32}', chat_id)
                    or not isinstance(message, str) or not 1 <= len(message.strip()) <= 8000):
                return self.reply(400, {'error': 'Escribe un mensaje de hasta 8.000 caracteres en un chat válido.'})
            if message.strip().startswith('/'):
                return self.reply(400, {'error': 'Los comandos del escritorio no están habilitados aquí. Usa Consultar para ver tareas, alertas y recuerdos.'})
            if not app.generation.acquire(blocking=False):
                return self.reply(409, {'error': 'Karen está respondiendo. Espera a que termine.'})
            try:
                with app.archive.connect() as db:
                    if not db.execute('SELECT 1 FROM chats WHERE id=?', (chat_id,)).fetchone():
                        return self.reply(404, {'error': 'La conversación ya no existe.'})
                answer = app.ask(chat_id, message.strip())
                app.archive.append(chat_id, message.strip(), answer, True)
                self.reply(200, {'answer': answer})
            except SpeechBusy:
                self.reply(409, {'error': 'La voz está terminando una lectura. Detén la voz y vuelve a intentar.'})
            except RuntimeError:
                self.reply(503, {'error': 'El núcleo local o la voz no están disponibles. Revisa sus servicios en el PC.'})
            except requests.RequestException:
                self.reply(502, {'error': 'El modelo no respondió. Revisa su conexión en el PC. No se guardó este turno; comprueba el historial antes de reenviarlo.'})
            except (OSError, sqlite3.Error, ValueError, KeyError):
                self.reply(503, {'error': 'No se pudo completar o guardar la respuesta. Comprueba el historial antes de reenviar.'})
            finally:
                app.generation.release()

    return Handler


def main():
    parser = argparse.ArgumentParser(description='Karen para iPhone')
    parser.add_argument('action', choices=('serve', 'code', 'rotate'), nargs='?', default='serve')
    parser.add_argument('--port', type=int, default=18793)
    parser.add_argument('--origin', help='Origen HTTPS exacto de Tailscale Serve')
    parser.add_argument('--tailnet-origin', type=validate_tailnet_origin,
                        help='Acceso por IP sin DNS; exclusivamente mediante Tailscale Serve TCP')
    args = parser.parse_args()
    if args.origin:
        parsed = urlsplit(args.origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
            parser.error('--origin debe ser https://nombre-equipo sin ruta')
    if args.action == 'rotate' or not TOKEN_FILE.exists():
        save_token(TOKEN_FILE)
    secret = load_token(TOKEN_FILE)
    if args.action in ('code', 'rotate'):
        print(secret)
        return
    from karen_core2.runtime import CoreRuntime, effective_local_config
    archive = Conversations()
    core2 = CoreRuntime(archive_path=archive.path)
    app = MobileApp(archive, effective_local_config(load_config()), secret, args.origin,
                    tailnet_origin=args.tailnet_origin, core2=core2)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    server.daemon_threads = True
    tunnel = None
    if Path(app.ha_key_path).exists() and args.port == 18793:
        from ha_tunnel import HATunnel
        tunnel = HATunnel()
        tunnel.start()
    print(f'Karen móvil: http://127.0.0.1:{args.port}', flush=True)
    print('Ver código: python mobile_server.py code', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if tunnel:
            tunnel.close()
        server.server_close()


if __name__ == '__main__':
    main()
