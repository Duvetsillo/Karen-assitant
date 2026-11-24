"""Reuse Karen's existing offline STT worker and pinned local voice for HA."""
import base64
import io
import threading
import uuid
import wave


def transcribe(audio):
    if not isinstance(audio, bytes) or not 2 <= len(audio) <= 1_920_044:
        raise ValueError('Audio fuera del límite de 60 segundos.')
    if audio.startswith(b'RIFF'):
        with wave.open(io.BytesIO(audio), 'rb') as source:
            if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (16000, 1, 2):
                raise ValueError('Se requiere PCM mono de 16 bits y 16 kHz.')
            audio = source.readframes(source.getnframes())
    if len(audio) % 2:
        raise ValueError('PCM incompleto.')
    from voice_local import operation
    from karen_core2.models import LocalModels
    stop = threading.Event()
    models = LocalModels()
    with models.http, models.lease(stop):
        result = operation({'operation': 'stt', 'engine': 'faster-small',
                            'audio': base64.b64encode(audio).decode('ascii')}, stop, timeout=120)
    text = result.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValueError('No se reconoció una frase válida.')
    return {'text': text.strip()}


def synthesize(app, owner, data):
    if not isinstance(data, dict) or set(data) != {'text'}:
        raise ValueError('Solicitud de voz inválida.')
    return app.speech.render('home-assistant-' + owner, uuid.uuid4().hex, data['text'])
