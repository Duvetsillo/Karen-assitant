"""Optional local HA transport. Discovery never grants control permissions."""
import asyncio
from collections import deque
from getpass import getpass
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

import requests

from .privacy import seal, unseal

CONFIG = Path(__file__).resolve().parent.parent / '.private' / 'ha-api.dpapi'
ENTITY = re.compile(r'[a-z_]{2,32}\.[a-z0-9_]{1,128}')
SERVICES = {
    'light': {'turn_on', 'turn_off'}, 'switch': {'turn_on', 'turn_off'},
    'fan': {'turn_on', 'turn_off'}, 'input_boolean': {'turn_on', 'turn_off'},
    'media_player': {'turn_on', 'turn_off', 'volume_set'},
}


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError('Configuración HA inválida.')
    url, token = config.get('url', ''), config.get('token', '')
    if not isinstance(url, str) or not isinstance(token, str) or not token or re.search(r'\s', token):
        raise ValueError('URL o credencial HA inválida.')
    parsed = urlsplit(url)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in {'', '/'}):
        raise ValueError('URL HA inválida.')
    if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('HA fuera de loopback requiere HTTPS.')
    timeout = config.get('timeout', 8)
    allowed, blocked = config.get('allowed', {}), config.get('blocked', [])
    if type(timeout) not in (float, int) or not 1 <= timeout <= 30:
        raise ValueError('Timeout HA inválido.')
    if not isinstance(allowed, dict) or not isinstance(blocked, list):
        raise ValueError('Permisos HA inválidos.')
    for entity, actions in allowed.items():
        if not isinstance(entity, str) or not ENTITY.fullmatch(entity) or not isinstance(actions, list):
            raise ValueError('Entidad HA inválida.')
        domain = entity.split('.')[0]
        if not actions or any(not isinstance(a, str) or a not in SERVICES.get(domain, set()) for a in actions):
            raise ValueError('Servicio HA no autorizado por código.')
    if any(not isinstance(e, str) or not ENTITY.fullmatch(e) for e in blocked):
        raise ValueError('Lista de bloqueo inválida.')
    return {**config, 'url': url.rstrip('/'), 'timeout': timeout, 'allowed': allowed, 'blocked': blocked}


def save_config(config, path=CONFIG):
    """Explicit setup only; encrypted for the current Windows user, atomic replacement."""
    config = validate_config(config)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    try:
        with temporary.open('x', encoding='ascii') as out:
            out.write(seal(config))
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class HomeAssistant:
    def __init__(self, config=None, *, path=CONFIG, session=None):
        self._path = Path(path) if config is None else None
        self.config = validate_config(config) if config is not None else None
        if self.config is None and Path(path).exists():
            self.config = validate_config(unseal(Path(path).read_text(encoding='ascii')))
        self.http = session or requests.Session()
        if session is None:
            self.http.trust_env = False
        self.connected = False
        self.events_connected = False
        self.last_error = None
        self.errors = deque(maxlen=50)

    def status(self):
        return {'configured': self.config is not None, 'rest_connected': self.connected,
                'events_connected': self.events_connected, 'last_error': self.last_error,
                'errors': list(self.errors), 'administration': 'disabled'}

    def _error(self, code):
        self.last_error = code
        self.errors.append({'at': time.time(), 'code': code})

    def _request(self, method, path, payload=None):
        if self.config is None:
            raise ValueError('Home Assistant REST sin configurar.')
        try:
            response = self.http.request(method, self.config['url'] + path,
                headers={'Authorization': 'Bearer ' + self.config['token']}, json=payload,
                timeout=(2, self.config['timeout']), allow_redirects=False)
            try:
                if 300 <= response.status_code < 400:
                    raise ValueError('Redirección HA rechazada.')
                response.raise_for_status()
                result = response.json()
            finally:
                response.close()
            self.connected, self.last_error = True, None
            return result
        except (requests.RequestException, ValueError):
            self.connected = False
            self._error('rest_failed')
            raise ConnectionError('HA no respondió correctamente; operación no confirmada.') from None

    def states(self):
        rows = self._request('GET', '/api/states')
        if not isinstance(rows, list):
            self.connected = False
            self._error('invalid_states')
            raise ValueError('Estados HA incompatibles.')
        return [r for r in rows if isinstance(r, dict) and isinstance(r.get('entity_id'), str)
                and ENTITY.fullmatch(r['entity_id']) and isinstance(r.get('state'), str)]

    def control(self, entity, service, data=None, *, approve=None):
        if self._path is not None:
            self.config = validate_config(unseal(self._path.read_text(encoding='ascii')))
        if self.config is None:
            raise ValueError('Home Assistant sin configurar.')
        if (not isinstance(entity, str) or not ENTITY.fullmatch(entity) or
                entity in self.config['blocked'] or service not in self.config['allowed'].get(entity, [])):
            raise PermissionError('Entidad o servicio HA no autorizado.')
        domain = entity.split('.')[0]
        if service not in SERVICES.get(domain, set()):
            raise PermissionError('Servicio HA bloqueado por código.')
        data = {} if data is None else data
        if not isinstance(data, dict) or (service != 'volume_set' and data):
            raise ValueError('Parámetros HA no permitidos.')
        if service == 'volume_set' and (set(data) != {'volume_level'} or
                type(data['volume_level']) not in (int, float) or not 0 <= data['volume_level'] <= 1):
            raise ValueError('Volumen inválido.')
        request = {'entity_id': entity, 'service': service, 'data': dict(data)}
        if approve is None or approve(request) is not True:
            raise PermissionError('La acción HA requiere aprobación concreta.')
        if self._path is not None:
            latest = validate_config(unseal(self._path.read_text(encoding='ascii')))
            if latest != self.config:
                self.config = latest
                raise PermissionError('La configuración HA cambió; revisa y autoriza nuevamente.')
        # No retries of writes: timeout may mean an action already occurred.
        current = next((r for r in self.states() if r['entity_id'] == entity), None)
        if current is None or current['state'] in {'unknown', 'unavailable'}:
            raise ValueError('Entidad HA ausente o no disponible.')
        self._request('POST', '/api/services/' + domain + '/' + service, {**data, 'entity_id': entity})
        observed = next((r for r in self.states() if r['entity_id'] == entity), None)
        expected = {'turn_on': 'on', 'turn_off': 'off'}.get(service)
        verified = bool(observed and expected and observed['state'] == expected)
        if service == 'volume_set' and observed:
            actual = observed.get('attributes', {}).get('volume_level')
            verified = type(actual) in (int, float) and abs(actual - data['volume_level']) < .01
        return {'entity_id': entity, 'service': service, 'sent': True, 'verified': verified,
                'state': observed['state'] if observed else None}

    async def _authenticate(self, ws):
        message = await ws.receive_json()
        if message.get('type') != 'auth_required':
            raise ValueError('Inicio WebSocket HA inválido.')
        await ws.send_json({'type': 'auth', 'access_token': self.config['token']})
        if (await ws.receive_json()).get('type') != 'auth_ok':
            raise PermissionError('Autenticación WebSocket HA rechazada.')

    async def registries(self):
        """On demand only; entity area overrides device area. No automatic memory writes."""
        import aiohttp
        if self.config is None:
            raise ValueError('HA sin configurar.')
        try:
            async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=self.config['timeout'])) as session:
                async with session.ws_connect(self.config['url'] + '/api/websocket',
                                              timeout=aiohttp.ClientWSTimeout(ws_receive=self.config['timeout'], ws_close=2), max_msg_size=2**22) as ws:
                    await self._authenticate(ws)
                    result = {}
                    for i, name in enumerate(('area', 'device', 'entity'), 1):
                        await ws.send_json({'id': i, 'type': 'config/' + name + '_registry/list'})
                        message = await ws.receive_json()
                        if message.get('id') != i or message.get('success') is not True or not isinstance(message.get('result'), list):
                            raise ValueError('Registro HA no disponible.')
                        result['entities' if name == 'entity' else name + 's'] = message['result']
                    return result
        except Exception:
            self._error('registry_failed')
            raise ConnectionError('No se pudieron leer registros HA.') from None

    async def watch(self, stop, on_event, *, entities, attempts=5):
        """Explicit subscription; selected state changes only. No raw attributes retained."""
        import aiohttp
        if self.config is None or not isinstance(entities, (set, list, tuple)) or not entities or any(not isinstance(e, str) or not ENTITY.fullmatch(e) for e in entities):
            raise ValueError('Selecciona entidades HA para observar.')
        if type(attempts) is not int or not 1 <= attempts <= 20:
            raise ValueError('Reintentos HA inválidos.')
        failures = 0
        while not stop.is_set() and failures < attempts:
            try:
                async with aiohttp.ClientSession(trust_env=False, timeout=aiohttp.ClientTimeout(total=self.config['timeout'])) as session:
                    async with session.ws_connect(self.config['url'] + '/api/websocket',
                                                  timeout=aiohttp.ClientWSTimeout(ws_receive=self.config['timeout'], ws_close=2), heartbeat=20, max_msg_size=2**20) as ws:
                        await self._authenticate(ws)
                        await ws.send_json({'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'})
                        ack = await ws.receive_json()
                        if ack.get('id') != 1 or ack.get('success') is not True:
                            raise ValueError('Suscripción HA rechazada.')
                        self.events_connected = True
                        while not stop.is_set():
                            try:
                                message = await asyncio.wait_for(ws.receive_json(), timeout=.5)
                            except asyncio.TimeoutError:
                                if ws.closed:
                                    raise ConnectionError()
                                continue
                            if message.get('type') != 'event' or message.get('id') != 1:
                                continue
                            event = message.get('event', {})
                            data = event.get('data', {})
                            entity = data.get('entity_id')
                            old, new = data.get('old_state') or {}, data.get('new_state') or {}
                            if entity in entities and old.get('state') != new.get('state'):
                                on_event({'entity_id': entity, 'old_state': old.get('state'),
                                          'state': new.get('state'), 'at': event.get('time_fired')})
            except PermissionError:
                self._error('auth_failed')
                return
            except Exception:
                self._error('events_disconnected')
                failures += 1
            finally:
                self.events_connected = False
            # Cooperative, bounded backoff; cancellation never waits through the whole delay.
            for _ in range(min(2 ** failures, 30) * 10):
                if stop.is_set():
                    return
                await asyncio.sleep(.1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('configure')
    setup.add_argument('url')
    sub.add_parser('status')
    sub.add_parser('states')
    sub.add_parser('registries')
    watch = sub.add_parser('events')
    watch.add_argument('entities', nargs='+', help='IDs exactos; observa únicamente estas entidades.')
    allow = sub.add_parser('allow')
    allow.add_argument('entity')
    allow.add_argument('services', nargs='+', choices=('turn_on', 'turn_off', 'volume_set'))
    block = sub.add_parser('block')
    block.add_argument('entity')
    args = parser.parse_args()
    if args.command == 'configure':
        save_config({'url': args.url, 'token': getpass('Token HA (oculto): ')})
        print('Conexión guardada con DPAPI. Control desactivado; no se cambiaron permisos existentes.')
        return
    client = HomeAssistant()
    if args.command in {'allow', 'block'}:
        if client.config is None or not ENTITY.fullmatch(args.entity):
            raise ValueError('Configura HA y usa un ID de entidad válido.')
        config = json.loads(json.dumps(client.config))
        if args.command == 'allow':
            config['allowed'][args.entity] = args.services
            config['blocked'] = [e for e in config['blocked'] if e != args.entity]
            validate_config(config)
            print(json.dumps({'entity_id': args.entity, 'services': args.services}, ensure_ascii=False))
            if input('Para autorizar estos servicios escribe AUTORIZAR ' + args.entity + ': ') != 'AUTORIZAR ' + args.entity:
                print('Permisos sin cambios.')
                return
        else:
            config['allowed'].pop(args.entity, None)
            config['blocked'] = list(dict.fromkeys([*config['blocked'], args.entity]))
        save_config(config)
        print('Permisos guardados. Cada control vuelve a comprobarlos antes de enviar la orden.')
        return
    if args.command == 'states':
        rows = client.states()
        result = [{'entity_id': r['entity_id'], 'state': r['state']} for r in rows]
    elif args.command == 'events':
        import threading
        try:
            asyncio.run(client.watch(threading.Event(), lambda event: print(json.dumps(event, ensure_ascii=False)), entities=args.entities))
        except KeyboardInterrupt:
            pass
        return
    elif args.command == 'registries':
        result = asyncio.run(client.registries())
    else:
        result = client.status()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
