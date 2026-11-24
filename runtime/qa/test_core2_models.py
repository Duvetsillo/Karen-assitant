import tempfile
from pathlib import Path
import threading
import unittest

import requests

from karen_core2.models import LocalModels, GPU_RESERVE, task_kind


class Response:
    def __init__(self, data=None, lines=None, status=200):
        self.data, self.lines, self.status_code = data, lines or [], status
        self.closed = False
    def json(self): return self.data
    def iter_lines(self): yield from self.lines
    def raise_for_status(self):
        if self.status_code >= 400: raise requests.HTTPError('synthetic failure')
    def close(self): self.closed = True
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class Transport:
    def __init__(self): self.calls, self.chat_count = [], 0
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith('/api/tags'):
            return Response({'models': [{'name': 'good:1b', 'size': 500000000}, {'name': 'proxy:cloud', 'size': 0}]})
        return Response({'models': []})
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith('/api/show'): return Response({'capabilities': ['completion', 'vision', 'tools']})
        self.chat_count += 1
        return Response({'message': {'content': 'Respuesta local'}})


class ModelRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.transport = Transport()
        self.models = LocalModels(transport=self.transport, probe=lambda: {
            'ram_available_bytes': 8 * 1024**3, 'vram_available_bytes': 4 * 1024**3},
            lease_path=Path(self.temp.name) / 'inference.lock')
    def tearDown(self): self.temp.cleanup()

    def test_discovery_checks_capabilities_and_never_resolves_cloud_alias(self):
        result = self.models.discover()
        self.assertEqual([m['name'] for m in result], ['good:1b'])
        self.assertTrue(all(call[1].get('allow_redirects') is False for call in self.transport.calls))
        self.assertFalse(any(call[1].get('json', {}).get('model') == 'proxy:cloud' for call in self.transport.calls))

    def test_generation_caps_context_and_records_latency_without_prompt(self):
        self.assertEqual(self.models.chat([{'role': 'user', 'content': 'private synthetic prompt'}])['content'], 'Respuesta local')
        payload = next(kwargs['json'] for url, kwargs in self.transport.calls if url.endswith('/api/chat'))
        self.assertEqual(payload['options']['num_ctx'], 2048)
        self.assertEqual(payload['options']['num_predict'], 256)
        self.assertEqual(payload['options']['num_gpu'], 0)
        self.assertEqual(payload['keep_alive'], 0)
        self.assertEqual(self.models.metrics[-1]['device'], 'cpu')
        self.assertNotIn('private', str(self.models.metrics))

    def test_long_history_keeps_existing_context_budget_on_cpu(self):
        self.models.chat([{'role': 'user', 'content': 'Historia previa ' * 400}])
        payload = next(kwargs['json'] for url, kwargs in self.transport.calls if url.endswith('/api/chat'))
        self.assertEqual(payload['options']['num_ctx'], 4096)
        self.assertEqual(payload['options']['num_gpu'], 0)

    def test_complex_gpu_allocation_leaves_headroom_and_low_vram_uses_cpu(self):
        model = {'name': 'synthetic-tools', 'size': 3 * 1024**3, 'layers': 32, 'capabilities': ['completion', 'tools']}
        high = {'ram_available_bytes': 8 * 1024**3, 'vram_available_bytes': 4 * 1024**3}
        choice = self.models.allocation(model, 'tools', high)
        self.assertGreater(choice['gpu_layers'], 0)
        self.assertLess(choice['gpu_layers'], 32)
        self.assertLessEqual(choice['estimated_vram_bytes'] + GPU_RESERVE, high['vram_available_bytes'])
        low = {**high, 'vram_available_bytes': 512 * 1024**2}
        self.assertEqual(self.models.allocation(model, 'tools', low)['device'], 'cpu')
        self.assertIsNone(self.models.allocation(model, 'tools', {**low, 'ram_available_bytes': 1024**3}))

    def test_budget_is_rechecked_after_a_model_was_ranked(self):
        samples = iter([{'ram_available_bytes': 8 * 1024**3}, {'ram_available_bytes': 64 * 1024**2}])
        self.models.probe = lambda: next(samples)
        with self.assertRaises(RuntimeError): self.models.chat([])
        self.assertEqual(self.transport.chat_count, 0)

    def test_request_classification_uses_task_signals_without_inference(self):
        self.assertEqual(task_kind('Hola, Karen'), 'conversation')
        self.assertEqual(task_kind('Resume este texto'), 'memory')
        self.assertEqual(task_kind('Compara estas dos opciones paso a paso'), 'reasoning')
        self.assertEqual(task_kind('Depura este código Python'), 'coding')

    def test_partial_stream_never_retries_or_uses_thinking(self):
        original = self.transport.post
        def stream(url, **kwargs):
            if url.endswith('/api/chat'):
                self.transport.chat_count += 1
                return Response(lines=[b'{"message":{"content":"Texto","thinking":"oculto"}}', b'{"error":"failed"}'])
            return original(url, **kwargs)
        self.transport.post = stream
        parts = []
        with self.assertRaises(ValueError):
            self.models.chat([{'role': 'user', 'content': 'Hola'}], on_token=parts.append)
        self.assertEqual(parts, ['Texto'])
        self.assertEqual(self.transport.chat_count, 1)

    def test_redirects_rejected_and_cancellation_prevents_generation(self):
        self.transport.get = lambda *args, **kwargs: Response(status=302)
        with self.assertRaises(ValueError): self.models.discover()
        self.models.discover = lambda: [{'name': 'good:1b', 'size': 500000000, 'capabilities': ['completion']}]
        stop = threading.Event(); stop.set()
        with self.assertRaises(InterruptedError): self.models.chat([], stop=stop)
        self.assertEqual(self.transport.chat_count, 0)

    def test_one_model_lease_and_cancellable_wait(self):
        another = LocalModels(transport=self.transport, probe=self.models.probe, lease_path=self.models.lease_path)
        stopped = threading.Event()
        result = []
        def wait():
            try:
                with another.lease(stopped): result.append('unexpected concurrent access')
            except InterruptedError: result.append('canceled')
        with self.models.lease(threading.Event()):
            worker = threading.Thread(target=wait)
            worker.start(); stopped.set(); worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(result, ['canceled'])


if __name__ == '__main__': unittest.main()
