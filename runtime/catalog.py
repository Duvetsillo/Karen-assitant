"""Read-only model discovery, independent of chat and benchmark execution."""
from dataclasses import dataclass
import logging
import threading
import time
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class CatalogSource:
    server: str
    backend: str = "ollama"
    api_key: str = ""

    @property
    def key(self):
        return self.server.rstrip("/"), self.backend, self.api_key

    @property
    def preference_key(self):
        return self.backend + ":" + self.server.rstrip("/")


@dataclass(frozen=True)
class CatalogResult:
    models: tuple
    status: str
    message: str
    selectable: bool = True

    def snapshot(self, source):
        # No credentials; node addresses are metadata, not authorized benchmark targets.
        return {"provider": source.backend, "node_url": source.server.rstrip("/"),
                "status": self.status, "selectable": self.selectable,
                "models": [dict(m) for m in self.models]}


def fetch_catalog(source):
    try:
        parsed = urlparse(source.server)
        valid_url = (parsed.scheme in {'http', 'https'} and parsed.hostname and
                     not parsed.username and not parsed.password and
                     not parsed.query and not parsed.fragment)
        parsed.port  # Validate malformed and out-of-range ports before HTTP.
    except ValueError:
        valid_url = False
    if not valid_url or source.backend not in {"ollama", "karen"}:
        return CatalogResult((), "error", "Servidor o API inválidos")
    headers = {"Authorization": "Bearer " + source.api_key} if source.api_key else {}
    route = "/salud" if source.backend == "karen" else "/api/tags"
    try:
        response = requests.get(source.server.rstrip("/") + route, headers=headers, timeout=(3, 10))
        response.raise_for_status()
        data = response.json()
        if source.backend == "karen":
            if not isinstance(data, dict) or data.get("estado") != "ok":
                raise ValueError("Salud Karen incompatible")
            model = data.get("modelo")
            models = ({"name": model, "installed": True},) if isinstance(model, str) and model else ()
            return CatalogResult(models, "ready", "Modelo definido por el servidor Karen", False)
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list) or any(not isinstance(m, dict) or not isinstance(m.get("name"), str) or not m["name"].strip() for m in models):
            raise ValueError("El endpoint no devuelve un catálogo Ollama válido")
        normalized = tuple({k: m[k] for k in ("name", "size", "digest", "modified_at", "details") if k in m} for m in models)
        # The local daemon can resolve signed-in cloud models absent from /tags.
        # Discover only the cloud model the user explicitly requested; no pull.
        cloud_name = 'gemma4:31b-cloud'
        if parsed.hostname in {'127.0.0.1', 'localhost'} and cloud_name not in [m['name'] for m in normalized]:
            try:
                cloud = requests.post(source.server.rstrip('/') + '/api/show', json={'model': cloud_name}, headers=headers, timeout=(3, 10))
                cloud_data = cloud.json() if cloud.status_code == 200 else None
                capabilities = cloud_data.get('capabilities') if isinstance(cloud_data, dict) else None
                if isinstance(capabilities, list) and 'completion' in capabilities:
                    normalized += ({'name': cloud_name, 'cloud': True, 'installed': False},)
            except (requests.RequestException, ValueError):
                pass
        # tags lists installed models, not proof that they are currently resident in RAM.
        cloud_count = sum(bool(m.get('cloud') or m['name'].endswith('-cloud')) for m in normalized)
        message = f'{len(normalized) - cloud_count} modelos locales' + (f' · {cloud_count} cloud' if cloud_count else '')
        return CatalogResult(normalized, "ready" if normalized else "empty", message if normalized else "Sin modelos instalados; no se descargó ninguno")
    except requests.Timeout:
        return CatalogResult((), "error", "El catálogo agotó el tiempo de espera; pulsa Refrescar")
    except requests.RequestException:
        return CatalogResult((), "error", "No se pudo consultar el nodo; revisa servidor/API y pulsa Refrescar")
    except ValueError as exc:
        return CatalogResult((), "error", str(exc))


class CatalogBroker:
    """Coalesce concurrent requests and reuse fresh catalogues per credential/node."""
    def __init__(self, fetcher=fetch_catalog, ttl=30):
        self.fetcher, self.ttl = fetcher, ttl
        self.cache = {}
        self.inflight = {}
        self.lock = threading.Lock()

    def request(self, source, callback, force=False):
        key = source.key
        cached = None
        with self.lock:
            if key in self.inflight:
                self.inflight[key].append(callback)
                return
            entry = self.cache.get(key)
            if not force and entry and time.monotonic() - entry[0] < self.ttl:
                cached = entry[1]
            else:
                self.inflight[key] = [callback]
        if cached is not None:
            callback(cached)
            return

        def worker():
            try:
                result = self.fetcher(source)
            except Exception:
                result = CatalogResult((), "error", "No se pudo cargar el catálogo; pulsa Refrescar")
            with self.lock:
                # Errors are retryable; cache only a valid API response.
                if result.status in {"ready", "empty"}:
                    self.cache[key] = time.monotonic(), result
                callbacks = self.inflight.pop(key)
            for listener in callbacks:
                try:
                    listener(result)
                except Exception:
                    logging.getLogger(__name__).exception('Error al notificar el catálogo')
        threading.Thread(target=worker, daemon=True).start()
