"""Authenticated mobile bridge to Karen's existing, pinned local voice."""
import hashlib
import re
import threading
import time
from collections import OrderedDict

from speech_text import spoken_text


class SpeechBusy(RuntimeError):
    pass


class MobileSpeech:
    def __init__(self, synthesize=None, timeout=120):
        self.synthesize = synthesize or self._local
        self.timeout = timeout
        self.lock = threading.Lock()
        self.active = None
        self.recent = OrderedDict()

    @staticmethod
    def _local(text, stop):
        from expressive_voice import synthesize
        from karen_core2.models import LocalModels, local_model
        import requests
        # Same adult feminine identity as desktop/Pet; never choose a browser/cloud voice.
        models = LocalModels()
        with models.http, models.lease(stop):
            try:
                with models.request('/api/ps') as response:
                    loaded = response.json().get('models', [])
                for model in loaded:
                    if local_model(model.get('name', '')):
                        with models.request('/api/generate', {'model': model['name'], 'keep_alive': 0}):
                            pass
            except requests.RequestException:
                pass
            return synthesize(text, stop, style='serene')

    def prepare_chat(self, *, lightweight=False):
        if lightweight:
            from karen_core2.models import resources
            # A small CPU conversation can leave the pinned voice warm on the GPU.
            # Otherwise release voice weights so system RAM retains a real reserve.
            available = resources().get('ram_available_bytes')
            if available is not None and available >= 3584 * 1024**2:
                return
        from expressive_voice import release
        deadline = time.monotonic() + 4
        while not release():
            if time.monotonic() > deadline:
                raise SpeechBusy('La voz sigue generando audio; detén la lectura y vuelve a intentar.')
            time.sleep(.1)

    def release_idle(self):
        """Free idle voice weights after playback; never interrupt another synthesis."""
        from expressive_voice import release
        deadline = time.monotonic() + 2
        while True:
            with self.lock:
                active = self.active
            if active and not active[1].is_set():
                return False
            if active is None and release():
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(.05)

    @staticmethod
    def key(owner, identity):
        if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
            raise ValueError('Identificador de voz inválido.')
        return hashlib.sha256(owner.encode()).hexdigest(), identity

    def _remember(self, key):
        self.recent[key] = time.monotonic()
        while self.recent and (len(self.recent) > 64 or next(iter(self.recent.values())) < time.monotonic() - 180):
            self.recent.popitem(last=False)

    def cancel(self, owner, identity):
        key = self.key(owner, identity)
        with self.lock:
            self._remember(key)  # Handles cancellation arriving before the synthesis request.
            if self.active and self.active[0] == key:
                self.active[1].set()
        return {'canceled': True}

    def render(self, owner, identity, text):
        key = self.key(owner, identity)
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1200:
            raise ValueError('Texto de voz inválido.')
        text = spoken_text(text)
        if not text.strip():
            raise ValueError('No hay texto para leer.')
        stop = threading.Event()
        with self.lock:
            if key in self.recent:
                raise InterruptedError('Solicitud cancelada o ya atendida.')
            if self.active:
                raise SpeechBusy('La voz está ocupada.')
            self.active = (key, stop)
        timer = threading.Timer(self.timeout, stop.set)
        timer.daemon = True
        timer.start()
        try:
            audio = self.synthesize(text, stop)
            if stop.is_set():
                raise InterruptedError('Síntesis cancelada o agotada.')
            if not isinstance(audio, bytes) or not 44 <= len(audio) <= 24_000_000 or not audio.startswith(b'RIFF'):
                raise ValueError('El motor local no devolvió audio válido.')
            return audio
        finally:
            timer.cancel()
            with self.lock:
                self.active = None
                self._remember(key)
