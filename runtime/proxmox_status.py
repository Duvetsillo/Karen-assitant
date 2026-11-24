"""Read-only Proxmox status through its HTTPS API."""

import os
import math
import re
import unicodedata
from urllib.parse import urlparse

import requests


def _finite_number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


class ProxmoxStatus:
    def __init__(self, url=None, token_id=None, token_secret=None, session=None):
        self.url = url if url is not None else os.getenv('KAREN_PVE_URL', '')
        self.token_id = token_id if token_id is not None else os.getenv('KAREN_PVE_TOKEN_ID', '')
        self.token_secret = token_secret if token_secret is not None else os.getenv('KAREN_PVE_TOKEN_SECRET', '')
        self.session = session or requests.Session()

    def _request_path(self, path):
        parsed = urlparse(self.url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or
                parsed.query or parsed.fragment or parsed.path not in {'', '/'}):
            raise ValueError('KAREN_PVE_URL debe ser una URL HTTPS sin credenciales ni ruta.')
        if not re.fullmatch(r'[A-Za-z0-9_.@-]+![A-Za-z0-9_.-]+', self.token_id) or not self.token_secret:
            raise ValueError('Configura KAREN_PVE_TOKEN_ID y KAREN_PVE_TOKEN_SECRET.')
        response = self.session.get(
            self.url.rstrip('/') + '/api2/json' + path,
            headers={'Authorization': 'PVEAPIToken=' + self.token_id + '=' + self.token_secret},
            timeout=(2.0, 8.0),
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get('data') if isinstance(payload, dict) else None
        return data

    def _request(self, node, suffix):
        if not isinstance(node, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,62}', node):
            raise ValueError('Nombre de nodo inválido.')
        return self._request_path('/nodes/' + node + suffix)

    def cluster(self):
        data = self._request_path('/cluster/status')
        if not isinstance(data, list):
            raise ValueError('Estado de clúster Proxmox incompatible.')
        row = next((item for item in data if isinstance(item, dict) and item.get('type') == 'cluster'), None)
        if row is None or type(row.get('quorate')) not in (int, bool) or row['quorate'] not in (0, 1):
            raise ValueError('Proxmox no devolvió estado de quorum verificable.')
        result = {'quorate': bool(row['quorate'])}
        name = row.get('name')
        if isinstance(name, str):
            name = ''.join(char if not unicodedata.category(char).startswith('C') else ' ' for char in name)
            result['cluster'] = ' '.join(name.split())[:100]
        if type(row.get('nodes')) is int and 0 <= row['nodes'] <= 1000:
            result['nodes'] = row['nodes']
        return result

    def node(self, node):
        data = self._request(node, '/status')
        if not isinstance(data, dict):
            raise ValueError('Respuesta Proxmox incompatible.')
        result = {'node': node}
        if _finite_number(data.get('uptime')) and data['uptime'] >= 0:
            result['uptime_seconds'] = int(data['uptime'])
        if _finite_number(data.get('cpu')) and 0 <= data['cpu'] <= 1:
            result['cpu_percent'] = round(data['cpu'] * 100, 1)
        for name in ('memory', 'rootfs'):
            value = data.get(name)
            if (isinstance(value, dict) and _finite_number(value.get('used')) and
                    _finite_number(value.get('total')) and value['total'] > 0 and value['used'] >= 0):
                result[name + '_used_bytes'] = int(value['used'])
                result[name + '_total_bytes'] = int(value['total'])
        if len(result) == 1:
            raise ValueError('Proxmox no devolvió métricas de nodo compatibles.')
        return result

    def guests(self, node, kind):
        if kind not in {'qemu', 'lxc'}:
            raise ValueError('Tipo de invitado inválido.')
        data = self._request(node, '/' + kind)
        if not isinstance(data, list):
            raise ValueError('Inventario Proxmox incompatible.')
        guests = []
        for item in data:
            if not isinstance(item, dict) or type(item.get('vmid')) is not int or not 1 <= item['vmid'] <= 999999999:
                continue
            status = item.get('status')
            if not isinstance(status, str) or status not in {'running', 'stopped', 'paused'}:
                status = 'unknown'
            name = item.get('name')
            name = ''.join(char if not unicodedata.category(char).startswith('C') else ' '
                           for char in name) if isinstance(name, str) else ''
            name = ' '.join(name.split())[:100]
            guests.append({'vmid': item['vmid'], 'name': name,
                           'status': status, 'type': kind})
            if len(guests) >= 100:
                break
        return guests

    def storage(self, node):
        data = self._request(node, '/storage')
        if not isinstance(data, list):
            raise ValueError('Inventario de almacenamiento Proxmox incompatible.')
        rows = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get('storage'), str):
                continue
            name = item['storage']
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,62}', name):
                continue
            row = {'storage': name}
            active = item.get('active')
            if type(active) in (int, bool) and active in (0, 1):
                row['active'] = bool(active)
            for field in ('used', 'avail', 'total'):
                value = item.get(field)
                if type(value) is int and value >= 0:
                    row[field + '_bytes'] = value
            if len(row) == 1:
                continue
            rows.append(row)
            if len(rows) >= 100:
                break
        return rows
