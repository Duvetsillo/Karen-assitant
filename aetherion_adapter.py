"""Thin adapter to the official local client; no scoring or license logic."""
import sys
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
PACKAGE = Path.home() / 'Desktop/Carpetas/Local_AI_Benchmark/src'


class AetherionAdapter:
    def __init__(self):
        for path in (ROOT / 'integration-deps', PACKAGE):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from local_ai_benchmark.integration import IntegrationClient
        self.client = IntegrationClient()

    def request(self, method, path, payload=None):
        try:
            return self.client.request(method, path, payload)
        except HTTPError as exc:
            try:
                code = json.loads(exc.read()).get('error', {}).get('code', '')
            except (ValueError, AttributeError):
                code = ''
            messages = {'license_required': 'Inicia sesión en Aetherion Studio para habilitar pruebas.', 'busy': 'Aetherion ya tiene una prueba activa.', 'unauthorized': 'La credencial local no coincide; reconecta Aetherion.', 'model_not_installed': 'El motor no encuentra este modelo en el nodo registrado.'}
            raise RuntimeError(messages.get(code, f'Aetherion rechazó la operación ({exc.code}).')) from None
        except URLError:
            raise RuntimeError('API Aetherion no disponible en 127.0.0.1:8766. Inicia integration-api en Aetherion.') from None

    def nodes(self):
        return self.request('GET', '/v1/nodes')

    def start(self, payload):
        return self.request('POST', '/v1/benchmarks', payload)

    def poll(self, job_id):
        return self.request('GET', '/v1/benchmarks/' + job_id)

    def results(self, job_id):
        return self.request('GET', '/v1/benchmarks/' + job_id + '/results')

    def cancel(self, job_id):
        return self.request('POST', '/v1/benchmarks/' + job_id + '/cancel', {})
