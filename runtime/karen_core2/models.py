"""Loopback-only Ollama routing with verified capabilities and one OS lease."""
from contextlib import contextmanager
import json
import math
import os
import re
import subprocess
import threading
import time
from urllib.parse import urlsplit

import requests

from answers import final_answer
from core_resources import ResourceBusy, microphone_guard, microphone_path
from .resource_policy import ResourcePolicy
from .inference_queue import InferenceQueue

KINDS = {'conversation', 'reasoning', 'coding', 'tools', 'vision', 'memory'}
LIGHT_KINDS = {'conversation', 'memory'}
GPU_RESERVE = 1536 * 1024**2


def task_kind(message):
    """Cheap local classification; never spends an inference to select an inference."""
    if re.search(r'(?i)\b(código|python|typescript|javascript|depura|debug|repositorio|programación)\b|escribe un programa', message):
        return 'coding'
    if re.search(r'(?i)\b(resume|resumen|sintetiza)\b', message):
        return 'memory'
    if len(message) > 700 or re.search(r'(?i)\b(analiza|compara|razona|planifica|diagnostica)\b|paso a paso', message):
        return 'reasoning'
    return 'conversation'


def local_endpoint(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('La inferencia de Core 2 solo admite Ollama en loopback HTTP.')
    return value.rstrip('/')


def local_model(name, metadata=None):
    metadata = metadata or {}
    return (isinstance(name, str) and bool(re.fullmatch(r'[\w./:-]{1,160}', name))
            and not re.search(r'(^|[-:/])cloud($|[-:/])', name, re.I)
            and not metadata.get('remote_host') and not metadata.get('remote_model'))


def resources():
    result = {'ram_available_bytes': None, 'vram_available_bytes': None, 'vram_total_bytes': None}
    try:
        from karen_task_tools import memory_sample
        result['ram_available_bytes'] = memory_sample({}, threading.Event())['ram_available_bytes']
    except (OSError, ValueError):
        pass
    try:
        response = subprocess.run(['nvidia-smi', '--query-gpu=memory.free,memory.total', '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=3,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        free, total = (int(value.strip()) for value in response.stdout.splitlines()[0].split(','))
        result.update(vram_available_bytes=free * 1048576, vram_total_bytes=total * 1048576)
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        pass
    return result


class LocalModels:
    def __init__(self, endpoint='http://127.0.0.1:11434', *, transport=None, probe=resources, lease_path=None, policy=None, mode_probe=None):
        self.endpoint = local_endpoint(endpoint)
        self.http = transport or requests.Session()
        if transport is None:
            self.http.trust_env = False
        self.probe = probe
        self.policy = policy or ResourcePolicy.from_environment()
        self.mode_probe = mode_probe
        self.queue = InferenceQueue(int(os.getenv('KAREN_MAX_PENDING_INFERENCES', '16')))
        self.lease_path = lease_path or microphone_path().with_name('ollama-inference.lock')
        self.catalog = []
        self.catalog_at = 0
        self.metrics = []
        self.active = None
        self.active_device = None
        self._guard = threading.Lock()

    def operating_mode(self):
        if self.mode_probe is None:
            return 'normal'
        try:
            value = self.mode_probe()
            return value if value in {'normal', 'gaming', 'do_not_disturb'} else 'normal'
        except Exception:
            return 'gaming'  # Unknown shared state must not permit new GPU work.

    def request(self, path, payload=None, *, stream=False):
        method = self.http.get if payload is None else self.http.post
        kwargs = {'timeout': (5, 120), 'allow_redirects': False}
        if payload is not None:
            kwargs.update(json=payload, stream=stream)
        response = method(self.endpoint + path, **kwargs)
        if 300 <= response.status_code < 400:
            response.close()
            raise ValueError('Ollama intentó redirigir fuera del endpoint local.')
        response.raise_for_status()
        return response

    def discover(self, force=False):
        with self._guard:
            if not force and time.monotonic() - self.catalog_at < 60:
                return list(self.catalog)
            with self.request('/api/tags') as response:
                tags = response.json().get('models', [])
            found = []
            for item in tags[:50]:
                name = item.get('name')
                if not local_model(name, item):
                    continue
                try:
                    with self.request('/api/show', {'model': name}) as response:
                        data = response.json()
                    if not local_model(name, data) or not isinstance(data.get('capabilities'), list):
                        continue
                    found.append({'name': name, 'size': item.get('size', 0),
                                  'capabilities': data['capabilities'],
                                  'layers': data.get('model_info', {}).get(
                                      str(data.get('model_info', {}).get('general.architecture', '')) + '.block_count'),
                                  'quantization': data.get('details', {}).get('quantization_level')})
                except (requests.RequestException, ValueError, TypeError):
                    continue
            self.catalog, self.catalog_at = found, time.monotonic()
            return list(found)

    def allocation(self, model, kind, budget):
        """Conservative estimates, not a promise about driver/KV memory usage."""
        size = model.get('size', 0)
        if not isinstance(size, (int, float)) or not math.isfinite(size) or size <= 0:
            return None
        free = budget.get('vram_available_bytes')
        if type(free) not in (int, float) or not math.isfinite(free) or free < 0:
            free = 0
        layers = model.get('layers')
        gpu_layers = 0
        if self.operating_mode() != 'gaming' and self.policy.profile != 'economy' and kind not in LIGHT_KINDS and type(layers) is int and 1 <= layers <= 256:
            room = max(0, free - self.policy.reserve_bytes - 512 * 1024**2)
            gpu_layers = min(layers, int(room / (size * 1.25 / layers)))
        host_needed = size * (1 - gpu_layers / layers) if gpu_layers else size
        host_needed += 384 * 1024**2
        available = budget.get('ram_available_bytes')
        if type(available) not in (int, float) or not math.isfinite(available) or available <= 0:
            return None
        reserve = max(1024**3, min(3 * 1024**3, (available or 0) // 4))
        if available is not None and host_needed + reserve > available:
            return None
        return {'device': 'gpu' if gpu_layers else 'cpu', 'gpu_layers': gpu_layers,
                'context': self.policy.context(kind),
                'vram_reserve_bytes': self.policy.reserve_bytes,
                'estimated_vram_bytes': int(size * 1.25 * gpu_layers / layers + 512 * 1024**2) if gpu_layers else 0}

    def rank(self, kind='conversation', preferred=None, *, budget=None):
        if kind not in KINDS:
            raise ValueError('Categoría de modelo desconocida.')
        budget = budget if budget is not None else self.probe()
        candidates = []
        for model in self.discover():
            caps = model['capabilities']
            if 'completion' not in caps or (kind in {'vision', 'tools'} and kind not in caps):
                continue
            if self.allocation(model, kind, budget) is None:
                continue
            name = model['name']
            score = 0
            if name == preferred:
                score += 35
            if kind == 'coding' and 'coder' in name:
                score += 70
            if kind in {'reasoning', 'tools', 'vision'} and 'qwen3.5' in name:
                score += 40
            if kind in {'conversation', 'memory'} and name == 'gemma3:1b':
                score += 65
            recent = [m['seconds'] for m in self.metrics if m['model'] == name and m['ok']]
            if recent:
                score -= min(20, sum(recent) / len(recent))
            # Smaller weights help latency only after capability and task suitability.
            score -= model['size'] / 1024**3
            candidates.append((score, model))
        return [model for _, model in sorted(candidates, key=lambda item: item[0], reverse=True)]

    @contextmanager
    def lease(self, stop):
        deadline = time.monotonic() + 30
        while True:
            if stop.is_set():
                raise InterruptedError('Inferencia cancelada.')
            try:
                with microphone_guard(self.lease_path):
                    yield
                return
            except ResourceBusy:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Otra interfaz está usando la inferencia local.')
                stop.wait(.1)

    @contextmanager
    def _gaming_watch(self, response, stop, allocation):
        finished = threading.Event()
        def monitor():
            while not finished.wait(.1):
                if self.operating_mode() == 'gaming':
                    stop.set()
                    response.close()
                    return
        thread = None
        if allocation['gpu_layers'] and self.mode_probe is not None:
            thread = threading.Thread(target=monitor, name='karen-gaming-cancel', daemon=True)
            thread.start()
        try:
            yield
        finally:
            finished.set()
            if thread:
                thread.join(timeout=.2)

    def chat(self, messages, *, kind='conversation', preferred=None, tools=None, on_token=None,
             stop=None, on_response=None, output_schema=None):
        stop = stop or threading.Event()
        priority = {'conversation': 0, 'tools': 5, 'memory': 10, 'vision': 10}.get(kind, 20)
        with self.queue.acquire(stop, priority=priority), self.lease(stop):
            candidates = self.rank(kind, preferred)
            if not candidates:
                raise ValueError('No hay modelo local instalado con capacidades y memoria suficientes; no se descargó ninguno.')
            last_error = None
            for selected in candidates[:2]:
                if stop.is_set():
                    raise InterruptedError('Inferencia cancelada.')
                started = time.monotonic()
                first_token_seconds = None
                delivered = False
                name = selected['name']
                allocation = None
                self.active = name
                try:
                    with self.request('/api/ps') as response:
                        loaded = response.json().get('models', [])
                    for previous in loaded:
                        previous_name = previous.get('name', '')
                        if previous_name != name and local_model(previous_name):
                            with self.request('/api/generate', {'model': previous_name, 'keep_alive': 0}):
                                pass
                    hardware = self.probe()
                    allocation = self.allocation(selected, kind, hardware)
                    if allocation is None:
                        raise ValueError('El presupuesto de memoria cambió; no se carga este modelo.')
                    self.active_device = allocation['device']
                    context = allocation['context']
                    if self.policy.profile != 'economy' and kind in LIGHT_KINDS and sum(len(str(m.get('content', ''))) for m in messages) > 4200:
                        context = 4096  # Preserve the existing bounded conversation history.
                    payload = {'model': name, 'messages': messages, 'stream': bool(on_token),
                               'keep_alive': 0,
                               'options': {'num_ctx': context, 'num_batch': 64 if kind in LIGHT_KINDS else 128,
                                           'num_gpu': allocation['gpu_layers'],
                                           'num_predict': self.policy.output_tokens(kind)}}
                    if 'thinking' in selected['capabilities']:
                        payload['think'] = False
                    if tools:
                        payload['tools'] = tools
                    if output_schema:
                        payload['format'] = output_schema
                    with self.request('/api/chat', payload, stream=bool(on_token)) as response, self._gaming_watch(response, stop, allocation):
                        if on_response:
                            on_response(response)
                        if stop.is_set():
                            raise InterruptedError('Inferencia cancelada.')
                        if on_token:
                            content, done = [], False
                            for line in response.iter_lines():
                                if allocation['gpu_layers'] and self.operating_mode() == 'gaming':
                                    stop.set()
                                if stop.is_set():
                                    raise InterruptedError('Inferencia cancelada.')
                                if not line:
                                    continue
                                event = json.loads(line)
                                if event.get('error'):
                                    raise ValueError('El modelo local rechazó la generación.')
                                fragment = event.get('message', {}).get('content', '')
                                if fragment:
                                    if first_token_seconds is None:
                                        first_token_seconds = round(time.monotonic() - started, 3)
                                    delivered = True
                                    content.append(fragment)
                                    on_token(fragment)
                                if event.get('done'):
                                    done = True
                                    break
                            if not done:
                                raise ValueError('Ollama cerró el stream sin respuesta final.')
                            result = {'content': final_answer(''.join(content))}
                        else:
                            data = response.json()
                            result = data.get('message') if isinstance(data, dict) else None
                            if not isinstance(result, dict) or (not result.get('tool_calls') and not isinstance(result.get('content'), str)):
                                raise ValueError('Respuesta local incompatible.')
                            result = {key: result[key] for key in ('content', 'tool_calls') if key in result}
                            if result.get('content'):
                                result['content'] = final_answer(result['content'])
                    if stop.is_set():
                        raise InterruptedError('Inferencia cancelada.')
                    self.metrics.append({'model': name, 'kind': kind, 'seconds': round(time.monotonic() - started, 3),
                                         'first_token_seconds': first_token_seconds,
                                         'device': allocation['device'], 'gpu_layers': allocation['gpu_layers'], 'ok': True})
                    self.metrics[:] = self.metrics[-100:]
                    return result
                except Exception as exc:
                    if stop.is_set():
                        self.metrics.append({'model': name, 'kind': kind, 'seconds': round(time.monotonic() - started, 3),
                                             'first_token_seconds': first_token_seconds, 'ok': False, 'canceled': True,
                                             'device': self.active_device, 'gpu_layers': (allocation or {}).get('gpu_layers')})
                        self.metrics[:] = self.metrics[-100:]
                        raise InterruptedError('Inferencia cancelada.') from None
                    if not isinstance(exc, (requests.RequestException, ValueError)):
                        raise
                    self.metrics.append({'model': name, 'kind': kind, 'seconds': round(time.monotonic() - started, 3), 'ok': False})
                    self.metrics[:] = self.metrics[-100:]
                    last_error = exc
                    if delivered:
                        raise
                finally:
                    self.active = None
                    self.active_device = None
            raise RuntimeError('Fallaron los modelos locales; no se usó cloud.') from last_error

    def status(self):
        return {'endpoint': self.endpoint, 'active_model': self.active, 'active_device': self.active_device,
                'queue': self.queue.status(),
                'policy': {'profile': self.policy.profile, 'light_tasks': 'cpu',
                           'gpu_reserve_bytes': self.policy.reserve_bytes, 'keep_alive': 0,
                           'operating_mode': self.operating_mode()}, 'hardware': self.probe(),
                'models': list(self.catalog), 'latency': self.metrics[-10:], 'local_only': True}
