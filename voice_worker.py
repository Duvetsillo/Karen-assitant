"""One isolated voice operation; private audio stays in pipes and memory."""
import base64
import io
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
stt_model = tts_model = None

def process(request):
    global stt_model, tts_model
    if request['operation'] == 'stt':
        return recognize(request)
    return speak(request)

def recognize(request):
    from transcription_local import recognize as decode
    audio = np.frombuffer(base64.b64decode(request['audio']), dtype=np.int16).astype(np.float32) / 32768
    return {'text': decode(audio, request.get('engine', 'faster-small'))}

def speak(request):
    global tts_model
    from kokoro_onnx import Kokoro
    import soundfile as sf
    if tts_model is None:
        tts_model = Kokoro(str(ROOT / 'voice-models/kokoro-v1.0.onnx'), str(ROOT / 'voice-models/voices-v1.0.bin'))
    voice = request.get('voice', 'ef_dora')
    if voice == 'ef_karen':
        # One constant speaker embedding. Spanish phonemization is unchanged.
        voice = (0.85 * tts_model.get_voice_style('ef_dora')
                 + 0.15 * tts_model.get_voice_style('af_bella'))
    audio, rate = tts_model.create(request['text'], voice=voice,
                                 speed=request.get('speed', 1.0), lang='es-419',
                                 sentence_pause=0.20, clause_pause=0.08)
    output = io.BytesIO()
    sf.write(output, audio, rate, format='WAV', subtype='PCM_16')
    encoded = output.getvalue()
    pitch = float(request.get('pitch_semitones', 0.0))
    if not -3 <= pitch <= 3:
        raise ValueError('Ajuste de tono fuera del rango permitido')
    if pitch:
        import subprocess
        shifted = subprocess.run(
            [str(ROOT / 'ffmpeg.exe'), '-hide_banner', '-loglevel', 'error',
             '-i', 'pipe:0', '-af', f'rubberband=pitch={2 ** (pitch / 12):.8f}:formant=preserved' + (',equalizer=f=3200:t=q:w=0.8:g=-2,volume=0.95' if request.get('voice') == 'ef_karen' else ''),
             '-ar', str(rate), '-c:a', 'pcm_s16le', '-f', 'wav', 'pipe:1'],
            input=encoded, capture_output=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if shifted.returncode:
            raise RuntimeError('No se pudo ajustar el tono local')
        encoded = shifted.stdout
    result = {'audio': base64.b64encode(encoded).decode('ascii'), 'sample_rate': rate}
    return result

if __name__ == '__main__':
    for line in sys.stdin:
        try:
            result = process(json.loads(line))
        except Exception:
            result = {'error': 'FallÃ³ el motor de voz local.'}
        print(json.dumps(result, ensure_ascii=True), flush=True)
