"""Bounded priorities inside one router. The existing OS lease still spans processes."""
from contextlib import contextmanager
import heapq
import itertools
import threading
import time


class InferenceQueue:
    def __init__(self, limit=16):
        if type(limit) is not int or not 1 <= limit <= 128:
            raise ValueError('La cola admite de 1 a 128 solicitudes pendientes.')
        self.limit = limit
        self._condition = threading.Condition()
        self._pending = []
        self._sequence = itertools.count()
        self._active = False

    @contextmanager
    def acquire(self, stop, *, priority=10, timeout=30):
        if type(priority) is not int or not 0 <= priority <= 100 or not 0 < timeout <= 300:
            raise ValueError('Prioridad o timeout de inferencia inválido.')
        if stop.is_set():
            raise InterruptedError('Inferencia cancelada.')
        entry = (priority, next(self._sequence))
        deadline = time.monotonic() + timeout
        with self._condition:
            if len(self._pending) >= self.limit:
                raise RuntimeError('Cola de inferencia llena.')
            heapq.heappush(self._pending, entry)
            try:
                while True:
                    if stop.is_set():
                        raise InterruptedError('Espera de inferencia cancelada.')
                    if not self._active and self._pending[0] == entry:
                        heapq.heappop(self._pending)
                        self._active = True
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Espera de inferencia agotada.')
                    self._condition.wait(min(.05, remaining))
            except BaseException:
                self._pending.remove(entry)
                heapq.heapify(self._pending)
                self._condition.notify_all()
                raise
        try:
            yield
        finally:
            with self._condition:
                self._active = False
                self._condition.notify_all()

    def status(self):
        with self._condition:
            return {'waiting': len(self._pending), 'active': self._active, 'limit': self.limit,
                    'scope': 'router_process'}
