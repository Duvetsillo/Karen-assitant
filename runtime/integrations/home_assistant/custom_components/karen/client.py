"""Authenticated conversation-only connection to the existing Karen Core."""
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class KarenClient:
    def __init__(self, session, url, key, owns_session=False):
        self.session, self.url, self._key = session, url.rstrip('/'), key
        self.owns_session = owns_session

    async def close(self):
        if self.owns_session:
            await self.session.close()

    async def request(self, route, data=None, *, raw=None, audio=False):
        try:
            payload = {'data': raw} if raw is not None else {'json': data}
            headers = {'Authorization': 'Bearer ' + self._key}
            if raw is not None:
                headers['Content-Type'] = 'application/octet-stream'
            async with self.session.request('GET' if data is None and raw is None else 'POST', self.url + '/api/ha/' + route,
                **payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=120, sock_connect=5), allow_redirects=False) as response:
                if response.status != 200:
                    raise HomeAssistantError('Karen no confirmó la solicitud. Comprueba el PC y su conexión.')
                if audio:
                    result = await response.read()
                    if not result.startswith(b'RIFF'):
                        raise HomeAssistantError('Karen no devolvió audio WAV válido.')
                    return result
                result = await response.json()
                if not isinstance(result, dict):
                    raise HomeAssistantError('Karen devolvió una respuesta incompatible.')
                return result
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            raise HomeAssistantError('No se pudo conectar con Karen local.') from None


async def async_client(hass):
    # Provisioned through SSH only after explicit approval. Never put a token in YAML or a card.
    path = Path(hass.config.path('.storage', 'karen-connection.json'))
    try:
        raw = await hass.async_add_executor_job(path.read_text)
        config = json.loads(raw)
        url, key = config['url'], config['key']
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost'})) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError()
        if not isinstance(key, str) or len(key) < 32:
            raise ValueError()
    except (OSError, KeyError, TypeError, ValueError):
        raise HomeAssistantError('Falta la conexión privada de Karen o su configuración no es válida.') from None
    if config.get('transport') == 'ssh-unix':
        connector = aiohttp.UnixConnector(path=hass.config.path('.storage', 'karen-core.sock'))
        return KarenClient(aiohttp.ClientSession(connector=connector), url, key, owns_session=True)
    return KarenClient(async_get_clientsession(hass), url, key)
