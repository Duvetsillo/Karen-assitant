"""Optional offline Kokoro voice. Its fixed timbre differs from the Qwen reference."""
import base64
import io
import json
from pathlib import Path
import sys
from voice_style import style_audio, validate_style

root = Path(sys.argv[1])
model = None
for line in sys.stdin:
    try:
        request = json.loads(line)
        text = request['text']
        if not isinstance(text, str) or not text.strip() or len(text) > 4096:
            raise ValueError()
        style = validate_style(request.get('style', 'serene'))
        import soundfile as sf
        from kokoro_onnx import Kokoro
        if model is None:
            model = Kokoro(str(root / 'voice-models/kokoro-v1.0.onnx'), str(root / 'voice-models/voices-v1.0.bin'))
        speaker = .85 * model.get_voice_style('ef_dora') + .15 * model.get_voice_style('af_bella')
        wave, rate = model.create(text, voice=speaker, speed=1., lang='es-419', sentence_pause=.2, clause_pause=.08)
        output = io.BytesIO()
        sf.write(output, wave, rate, format='WAV', subtype='PCM_16')
        audio = style_audio(output.getvalue(), root, style)
        result = {'audio': base64.b64encode(audio).decode('ascii')}
    except Exception:
        result = {'error': 'No se pudo generar la voz rápida. Revisa Kokoro, sus voces y FFmpeg.'}
    print(json.dumps(result), flush=True)
