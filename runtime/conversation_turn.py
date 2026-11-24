"""Per-request cancellation and conservative playback receipts, kept only in RAM."""
import threading
import time
import uuid


class ConversationTurn:
    def __init__(self, prompt, scope):
        self.id = uuid.uuid4().hex
        self.prompt, self.scope = prompt, scope
        self.cancelled = threading.Event()
        self.audio_cancelled = threading.Event()
        self.started = time.monotonic()
        self.private = False
        self._lock = threading.Lock()
        self._segments = []
        self.first_audio_seconds = None
        self.interrupted = False

    def generated(self, text):
        with self._lock:
            if self.cancelled.is_set():
                return False
            # The LLM output has its own token limit; also bound this working memory.
            if len(self._segments) >= 256 or sum(len(s['text']) for s in self._segments) + len(text) > 32000:
                raise ValueError('El turno excedió su límite de segmentos.')
            self._segments.append({'text': text, 'synthesized': False, 'played': False})
            return True

    def receipt(self, text, stage):
        if stage not in {'synthesized', 'played'}:
            raise ValueError('Etapa de audio desconocida.')
        with self._lock:
            if self.audio_cancelled.is_set():
                return False
            for segment in self._segments:
                if segment['text'] == text and not segment[stage]:
                    if stage == 'played' and not segment['synthesized']:
                        raise ValueError('Audio reproducido sin síntesis confirmada.')
                    segment[stage] = True
                    return True
            return False

    def audio_started(self):
        with self._lock:
            if not self.audio_cancelled.is_set() and self.first_audio_seconds is None:
                self.first_audio_seconds = time.monotonic() - self.started

    def interrupt(self, *, cancel_generation=True):
        with self._lock:
            self.interrupted = True
            self.audio_cancelled.set()
            if cancel_generation:
                self.cancelled.set()

    def snapshot(self):
        with self._lock:
            return {'id': self.id, 'interrupted': self.interrupted,
                    'first_audio_seconds': self.first_audio_seconds,
                    'segments': [dict(segment) for segment in self._segments]}

    def context(self, scope):
        """Do not mistake synthesized text for text delivered to the audio device."""
        with self._lock:
            if not self.interrupted or self.private or self.scope != scope:
                return None
            played = [s['text'] for s in self._segments if s['played']]
            pending = [s['text'] for s in self._segments if not s['played']]
            return {'question': self.prompt[:1000],
                    'delivered_sentences': ' '.join(played)[-1500:],
                    'unconfirmed_sentences': ' '.join(pending)[:1500]}
