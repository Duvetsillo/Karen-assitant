"""Authenticated loopback TTS. Utterances, keys and audio stay out of logs."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import gc
import io
import json
from pathlib import Path
import re
import secrets
import select
import socket
import threading
import time
import traceback

from voice_profile import load_profile
from voice_style import STYLES, style_audio, validate_style
from voice_acceleration import backend, accelerate, generate, check_cancelled, SpeechCancelled


def watch_disconnect(connection, cancelled, finished):
    """Observe only this HTTP connection; never cancels another client's audio."""
    while not finished.wait(.05):
        try:
            if select.select([connection], [], [], 0)[0] and not connection.recv(1, socket.MSG_PEEK):
                cancelled.set()
                return
        except OSError:
            cancelled.set()
            return


def speech_chunks(text, limit=200):
    result, current = [], ''
    for word in text.split():
        if len(current) + len(word) + 1 > limit and current:
            result.append(current)
            current = ''
        current = (current + ' ' + word).strip()
        if len(current) >= limit // 2 and re.search(r'[.!?]$', word):
            result.append(current)
            current = ''
    if current:
        result.append(current)
    return result


class VoiceEngine:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.model = self.prompt = self.signature = None
        self.last_used = time.monotonic()
        self.cache = OrderedDict()
        self.phase = 'cold'
        self.keep_warm_until = 0.0
        self.backend = backend(self.root)
        self.metrics = None
        self.last_error = None

    def execute(self, operation, *args):
        """Publish completion/failure on the inference thread before its next job."""
        try:
            return operation(*args)
        except SpeechCancelled:
            self.phase = 'ready' if self.model is not None else 'cold'
            raise
        except Exception as error:
            self.phase = 'error'
            # Locations only; exception messages can include request secrets.
            self.last_error = {'type': type(error).__name__, 'frames': [
                {'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                for frame in traceback.extract_tb(error.__traceback__)[-5:]]}
            raise

    def _load(self, profile):
        import torch
        from qwen_tts import Qwen3TTSModel
        signature = (profile.id, profile.reference_sha256, str(profile.model))
        if signature != self.signature:
            self.model = self.prompt = None
            self.cache.clear()
            gc.collect()
            torch.cuda.empty_cache()
        if self.model is None:
            self.phase = 'loading'
            if not torch.cuda.is_available():
                raise RuntimeError('Esta configuración de voz necesita CUDA')
            torch.set_num_threads(4)
            model = Qwen3TTSModel.from_pretrained(
                str(profile.model), device_map='cpu', dtype=torch.float32,
                attn_implementation='sdpa' if self.backend == 'cuda-graphs-fp32' else 'eager', local_files_only=True,
            )
            # Keep the validated FP32 Turing path and pinned speaker embedding.
            model.model.talker.to('cuda:0')
            model.model.speaker_encoder.to('cuda:0')
            model.device = torch.device('cuda:0')
            codec = model.model.speech_tokenizer
            codec.model.to(device='cpu', dtype=torch.float32)
            codec.device = torch.device('cpu')
            prompt = model.create_voice_clone_prompt(
                ref_audio=str(profile.reference), ref_text=profile.reference_text,
                x_vector_only_mode=True,
            )
            if self.backend == 'cuda-graphs-fp32':
                model.model.speaker_encoder.to('cpu')
                torch.cuda.empty_cache()
                model = accelerate(model, self.root, profile.generation)
                # Also warm decoder convolutions with synthetic text, never user data.
                with torch.inference_mode():
                    torch.manual_seed(int(profile.generation.get('seed', 42)))
                    generate(model, prompt, profile, 'Hola.', True)
            self.model, self.prompt = model, prompt
            self.signature = signature

    def prepare(self, expected_id, expected_hash):
        """Load the fixed voice while the assistant is still preparing its reply."""
        with self.lock:
            profile = load_profile(self.root)
            if (expected_id, expected_hash) != (profile.id, profile.reference_sha256):
                raise ValueError('El cliente no seleccionó la misma identidad de voz')
            self._load(profile)
            self.last_used = time.monotonic()
            self.keep_warm_until = self.last_used + 600
            self.phase = 'ready'
            self.last_error = None
            return profile

    def release(self):
        """Release idle weights while preserving the audio cache and voice identity."""
        if not self.lock.acquire(blocking=False):
            return False
        try:
            loaded = self.model is not None or self.prompt is not None
            self.model = self.prompt = None
            self.keep_warm_until = 0.0
            self.phase = 'cold'
            gc.collect()
            if loaded:
                import torch
                torch.cuda.empty_cache()
            return True
        finally:
            self.lock.release()

    def synthesize(self, text, expected_id, expected_hash, style='neutral', cancelled=None):
        check_cancelled(cancelled)
        validate_style(style)
        import numpy as np
        import soundfile as sf
        import torch
        with self.lock:
            check_cancelled(cancelled)
            started = time.monotonic()
            profile = load_profile(self.root)
            if (expected_id, expected_hash) != (profile.id, profile.reference_sha256):
                raise ValueError('El cliente no seleccionó la misma identidad de voz')
            signature = (profile.id, profile.reference_sha256, str(profile.model))
            key = (signature, text)
            self.last_used = time.monotonic()
            if key in self.cache:
                self.cache.move_to_end(key)
                self.metrics = {'cacheHit': True, 'generationSeconds': 0.0}
                self.keep_warm_until = self.last_used + 600
                self.phase = 'ready' if self.model is not None else 'cold'
                self.last_error = None
                return style_audio(self.cache[key], self.root, style), profile
            self._load(profile)
            check_cancelled(cancelled)
            self.phase = 'generating'
            chunks = []
            with torch.inference_mode():
                for chunk in speech_chunks(text):
                    torch.manual_seed(int(profile.generation.get('seed', 42)))
                    waves, rate = generate(self.model, self.prompt, profile, chunk,
                                           self.backend == 'cuda-graphs-fp32', cancelled)
                    wave = np.asarray(waves[0], dtype=np.float32)
                    if not np.isfinite(wave).all() or not wave.size or np.sqrt(np.mean(wave ** 2)) < .003:
                        raise RuntimeError('El motor devolvió audio inválido')
                    chunks.append(wave)
            check_cancelled(cancelled)
            output = io.BytesIO()
            sf.write(output, np.concatenate(chunks), rate, format='WAV', subtype='PCM_16')
            audio = output.getvalue()
            self.cache[key] = audio
            while len(self.cache) > 8 or sum(map(len, self.cache.values())) > 12_000_000:
                self.cache.popitem(last=False)
            self.last_used = time.monotonic()
            self.keep_warm_until = self.last_used + 600
            self.metrics = {'cacheHit': False, 'generationSeconds': self.last_used - started,
                            'audioSeconds': sum(len(wave) for wave in chunks) / rate,
                            'lastChunk': getattr(self.model, 'last_timings', None)}
            self.last_error = None
            self.phase = 'ready'
            return style_audio(audio, self.root, style), profile

    def cleanup(self):
        while True:
            time.sleep(15)
            if time.monotonic() > max(self.last_used + 120, self.keep_warm_until) and self.lock.acquire(blocking=False):
                try:
                    if self.model is not None and time.monotonic() > max(self.last_used + 120, self.keep_warm_until):
                        self.model = self.prompt = None
                        self.phase = 'cold'
                        gc.collect()
                        import torch
                        torch.cuda.empty_cache()
                finally:
                    self.lock.release()


def serve(root):
    root = Path(root).resolve()
    token = (root / 'voice-models/.expressive-token').read_text(encoding='ascii').strip()
    if len(token) < 32:
        raise RuntimeError('Credencial de voz local inválida')
    engine = VoiceEngine(root)
    # CUDA graphs and CPU decoder warmup belong to one long-lived inference
    # thread. HTTP requests/health remain concurrent and never run the model.
    inference = ThreadPoolExecutor(max_workers=1, thread_name_prefix='karen-tts')
    slots = threading.BoundedSemaphore(4)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def authorized(self):
            return not self.headers.get('Origin') and secrets.compare_digest(
                self.headers.get('Authorization', '').encode('utf-8'), ('Bearer ' + token).encode('ascii'))

        def reply(self, status, data):
            content = json.dumps(data).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if not self.authorized():
                self.reply(403, {'error': 'Autenticación de voz requerida'})
                return
            if self.path != '/health':
                self.reply(404, {'error': 'Ruta desconocida'})
                return
            try:
                profile = load_profile(root)
                self.reply(200, {'engine': 'qwen3-stable-spanish', 'protocol': 2,
                                'modelLoaded': engine.model is not None, 'phase': engine.phase,
                                'backend': engine.backend, 'lastSynthesis': engine.metrics,
                                'lastError': engine.last_error,
                                'capabilities': ['prepare'],
                                'styles': list(STYLES), 'styleRevision': 1, **profile.public()})
            except Exception:
                self.reply(503, {'error': 'Configura y verifica el perfil fijo de voz'})

        def do_POST(self):
            if not self.authorized():
                self.reply(403, {'error': 'Autenticación de voz requerida'})
                return
            if self.path not in {'/speech', '/prepare', '/release'}:
                self.reply(404, {'error': 'Ruta desconocida'})
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 65536:
                    raise ValueError()
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError()
                text = request.get('text', '')
                style = validate_style(request.get('style', 'neutral'))
                if self.path == '/speech' and (not isinstance(text, str) or not text.strip() or len(text) > 4096):
                    raise ValueError()
                profile = load_profile(root)
                if (request.get('profileId'), request.get('referenceSha256')) != (profile.id, profile.reference_sha256):
                    self.reply(409, {'error': 'La identidad de voz del cliente no coincide'})
                    return
            except (ValueError, KeyError, TypeError, OSError):
                self.reply(400, {'error': 'Petición o perfil de voz inválido'})
                return
            if self.path == '/release':
                released = engine.release()
                self.reply(200 if released else 409, {'released': released})
                return
            if not slots.acquire(blocking=False):
                self.reply(429, {'error': 'El motor de voz está ocupado; espera o cancela la petición actual'})
                return
            cancelled, finished = threading.Event(), threading.Event()
            try:
                if self.path == '/prepare':
                    inference.submit(engine.execute, engine.prepare, profile.id, profile.reference_sha256).result()
                    self.reply(200, {'ready': True, **profile.public()})
                    return
                threading.Thread(target=watch_disconnect, args=(self.connection, cancelled, finished), daemon=True).start()
                audio, profile = inference.submit(engine.execute, engine.synthesize, text.strip(), profile.id,
                                                   profile.reference_sha256, style, cancelled).result()
                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.send_header('Content-Length', str(len(audio)))
                self.send_header('X-Karen-Voice-Id', profile.id)
                self.send_header('X-Karen-Voice-Sha256', profile.reference_sha256)
                self.send_header('X-Karen-Voice-Style', style)
                self.end_headers()
                self.wfile.write(audio)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except SpeechCancelled:
                pass
            except Exception:
                self.reply(503, {'error': 'La voz fija no pudo generar audio; no se cambió de voz'})
            finally:
                finished.set()
                slots.release()

    server = ThreadingHTTPServer(('127.0.0.1', 18790), Handler)
    server.daemon_threads = True
    threading.Thread(target=engine.cleanup, daemon=True).start()
    server.serve_forever()


if __name__ == '__main__':
    import sys
    serve(sys.argv[1])
