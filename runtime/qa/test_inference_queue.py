import tempfile
from pathlib import Path
import threading
import time
import unittest

from karen_core2.inference_queue import InferenceQueue
from karen_core2.models import LocalModels
from qa.test_core2_models import Transport, Response


class InferenceQueueTests(unittest.TestCase):
    def wait_until(self, condition):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(.005)
        self.fail('La condición de sincronización no se cumplió.')

    def test_priorities_and_cancellation_preserve_one_active_task(self):
        queue = InferenceQueue(3)
        stop = threading.Event()
        order = []
        canceled = threading.Event()
        def run(label, priority, signal):
            try:
                with queue.acquire(signal, priority=priority):
                    order.append(label)
            except InterruptedError:
                order.append('canceled')
        workers = []
        with queue.acquire(stop):
            for index, (label, priority, signal) in enumerate((('background', 20, stop), ('chat', 0, stop), ('skip', 5, canceled)), 1):
                worker = threading.Thread(target=run, args=(label, priority, signal))
                workers.append(worker)
                worker.start()
                self.wait_until(lambda: queue.status()['waiting'] == index)
            with self.assertRaises(RuntimeError):
                with queue.acquire(stop):
                    self.fail('No puede entrar a una cola llena.')
            canceled.set()
            self.wait_until(lambda: queue.status()['waiting'] == 2)
        for worker in workers:
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(order, ['canceled', 'chat', 'background'])
        self.assertEqual(queue.status()['waiting'], 0)
        self.assertFalse(queue.status()['active'])

    def test_wait_timeout_does_not_leak_queue_entries(self):
        queue = InferenceQueue()
        with queue.acquire(threading.Event()):
            with self.assertRaises(TimeoutError):
                with queue.acquire(threading.Event(), timeout=.01):
                    self.fail('No debe ejecutar.')
            self.assertEqual(queue.status()['waiting'], 0)

    def test_gpu_stream_is_canceled_when_shared_gaming_mode_changes_without_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            mode = {'value': 'normal'}
            model = {'name': 'good:1b', 'size': 500000000, 'layers': 24, 'capabilities': ['completion']}
            transport = Transport()
            models = LocalModels(transport=transport, mode_probe=lambda: mode['value'],
                                 probe=lambda: {'ram_available_bytes': 8 * 1024**3, 'vram_available_bytes': 4 * 1024**3},
                                 lease_path=Path(directory) / 'inference.lock')
            models.discover = lambda: [model]
            original = transport.post
            def post(url, **kwargs):
                if url.endswith('/api/chat'):
                    transport.chat_count += 1
                    return Response(lines=[b'{"message":{"content":"first"}}', b'{"message":{"content":"second"}}', b'{"done":true}'])
                return original(url, **kwargs)
            transport.post = post
            fragments = []
            def interrupt(fragment):
                fragments.append(fragment)
                mode['value'] = 'gaming'
            with self.assertRaises(InterruptedError):
                models.chat([], kind='reasoning', on_token=interrupt)
            self.assertEqual(fragments, ['first'])
            self.assertEqual(transport.chat_count, 1)
            self.assertFalse(models.queue.status()['active'])

    def test_unknown_or_invalid_ram_budget_blocks_loading(self):
        models = LocalModels(transport=Transport())
        candidate = {'size': 500000000, 'layers': 24}
        for available in (None, float('nan'), float('inf'), True, -1, 'unknown'):
            with self.subTest(available=available):
                self.assertIsNone(models.allocation(candidate, 'reasoning', {'ram_available_bytes': available}))


if __name__ == '__main__':
    unittest.main()
