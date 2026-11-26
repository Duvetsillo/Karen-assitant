"""Validated in-process notifications. Payloads never contain document or chat text."""
from collections import deque
from datetime import datetime, timezone
import re
import threading
import uuid


TOPICS = frozenset('conversation.started conversation.completed conversation.interrupted '
    'memory.created memory.updated memory.conflict obsidian.note.changed obsidian.index.updated '
    'model.loaded model.unloaded resource.pressure gaming.started gaming.ended task.created '
    'task.completed task.failed agent.started agent.completed security.denied system.error'.split())


class EventBus:
    def __init__(self):
        self._lock = threading.RLock()
        self._local = threading.local()
        self._listeners = {}
        self._recent = deque(maxlen=100)
        self.listener_errors = 0

    def subscribe(self, topic, callback):
        if topic not in TOPICS or not callable(callback):
            raise ValueError('Suscripción de evento inválida.')
        with self._lock:
            callbacks = self._listeners.setdefault(topic, [])
            if callback not in callbacks:
                callbacks.append(callback)
        def unsubscribe():
            with self._lock:
                if callback in self._listeners.get(topic, []):
                    self._listeners[topic].remove(callback)
        return unsubscribe

    def emit(self, topic, *, entity_id=None, code='ok'):
        if topic not in TOPICS or not isinstance(code, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', code):
            raise ValueError('Evento inválido.')
        if entity_id is not None and (not isinstance(entity_id, str) or not re.fullmatch(r'[0-9a-f]{32,64}', entity_id)):
            raise ValueError('Identificador de evento inválido.')
        active = getattr(self._local, 'active', ())
        if topic in active or len(active) >= 8:
            return False  # Bound reentrant event chains; never recurse indefinitely.
        event = {'id': uuid.uuid4().hex, 'topic': topic, 'entity_id': entity_id, 'code': code,
                 'at': datetime.now(timezone.utc).isoformat()}
        with self._lock:
            self._recent.append(event)
            listeners = tuple(self._listeners.get(topic, ()))
        self._local.active = (*active, topic)
        try:
            for callback in listeners:
                try:
                    callback(dict(event))
                except Exception:
                    # Observers cannot fail the action or leak exception messages.
                    with self._lock:
                        self.listener_errors += 1
        finally:
            self._local.active = active
        return True

    def status(self):
        with self._lock:
            return {'recent': [dict(row) for row in self._recent], 'listener_errors': self.listener_errors,
                    'listeners': sum(map(len, self._listeners.values()))}
