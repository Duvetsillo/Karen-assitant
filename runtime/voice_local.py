import atexit
import base64
import json
import queue
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_lock = threading.Lock()
_proc = None
_responses = None


def shutdown():
    global _proc
    proc, _proc = _proc, None
    if proc is not None:
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        for pipe in (proc.stdin, proc.stdout):
            pipe.close()


atexit.register(shutdown)


def _read_responses(proc, responses):
    try:
        for line in proc.stdout:
            responses.put(json.loads(line))
    except (ValueError, OSError):
        pass
    finally:
        responses.put({'error': 'El motor local se cerró.'})


def operation(payload, cancelled, timeout=120):
    global _proc, _responses
    started = time.monotonic()
    while not _lock.acquire(timeout=.05):
        if cancelled.is_set():
            return {}
        if time.monotonic() - started > timeout:
            raise TimeoutError('El motor de voz local agotó el tiempo de espera.')
    try:
        if cancelled.is_set():
            return {}
        if _proc is None or _proc.poll() is not None:
            shutdown()
            python = ROOT / 'voice-runtime/Scripts/python.exe'
            if not python.is_file():
                raise RuntimeError('Entorno de voz local no instalado. Selecciona el motor anterior en Audio.')
            _responses = queue.Queue()
            _proc = subprocess.Popen([str(python), '-u', str(ROOT / 'voice_worker.py')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=0x08000000, cwd=str(ROOT))
            threading.Thread(target=_read_responses, args=(_proc, _responses), daemon=True).start()
        try:
            _proc.stdin.write((json.dumps(payload) + '\n').encode('utf-8'))
            _proc.stdin.flush()
            while True:
                if cancelled.is_set():
                    shutdown()
                    return {}
                if time.monotonic() - started > timeout:
                    raise TimeoutError('El motor de voz local agotó el tiempo de espera.')
                try:
                    result = _responses.get(timeout=.05)
                    break
                except queue.Empty:
                    continue
            if 'error' in result:
                raise RuntimeError(result['error'])
            return result
        except Exception:
            shutdown()
            raise
    finally:
        _lock.release()


def synthesize(text, voice, rate, cancelled, pitch_semitones=0.0):
    result = operation({'operation': 'tts', 'text': text, 'voice': voice, 'pitch_semitones': pitch_semitones, 'speed': max(.5, min(2.0, 1 + int(rate.rstrip('%')) / 100))}, cancelled)
    return base64.b64decode(result['audio']) if result else b''


def transcribe(audio, cancelled, engine="faster-small"):
    result = operation({'operation': 'stt', 'engine': engine, 'audio': base64.b64encode(audio.tobytes()).decode('ascii')}, cancelled)
    return result.get('text', '')
