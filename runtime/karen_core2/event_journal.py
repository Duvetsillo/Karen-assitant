"""Bounded JSON event journal. Only EventBus metadata reaches this file."""
import json
import logging
from logging.handlers import RotatingFileHandler

from .events import TOPICS


class EventJournal:
    def __init__(self, bus, path, *, max_bytes=262144, backups=3):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.Logger('karen.events', level=logging.INFO)
        self.handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backups,
                                           encoding='utf-8', delay=True)
        self.handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(self.handler)
        self._unsubscribe = [bus.subscribe(topic, self.write) for topic in TOPICS]

    def write(self, event):
        self.handler.acquire()
        try:
            self.logger.info(json.dumps(event, ensure_ascii=True, separators=(',', ':')))
        finally:
            # No persistent Windows handle: old callers need not adopt close() to release files.
            self.handler.close()
            self.handler.release()

    def close(self):
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe.clear()
        self.logger.removeHandler(self.handler)
        self.handler.close()
