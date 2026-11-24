"""Real loopback TTS benchmark, synthetic Spanish text only; never plays audio.

Run with expressive-runtime\Scripts\python.exe qa\measure_tts.py. The service
must already be running. Reports HTTP delivery, not speaker playback latency.
"""
import io
import json
from pathlib import Path
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]


def main():
    token = (ROOT / 'voice-models/.expressive-token').read_text().strip()
    active = json.loads((ROOT / 'voice-models/active-voice.json').read_text())
    identity = {'profileId': active['id'], 'referenceSha256': active['reference_sha256']}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, data=None):
        req = urllib.request.Request('http://127.0.0.1:18790' + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        return opener.open(req, timeout=240)

    started = time.perf_counter()
    with request('/prepare', identity) as response:
        assert json.load(response)['ready']
    preparation = time.perf_counter() - started
    print(json.dumps({'prepare_seconds': preparation}), flush=True)
    results = []
    texts = ['Hola. Soy Karen y estoy lista para ayudarte.',
             'Podemos conversar con calma y revisar tus pendientes.',
             'La temperatura del procesador depende de sus sensores.']
    for index, text in enumerate(texts):
        started = time.perf_counter()
        with request('/speech', dict(identity, text=text, style='serene')) as response:
            assert response.headers['X-Karen-Voice-Sha256'] == identity['referenceSha256']
            assert response.headers['X-Karen-Voice-Style'] == 'serene'
            audio = response.read(24_000_001)
        elapsed = time.perf_counter() - started
        assert len(audio) <= 24_000_000
        with wave.open(io.BytesIO(audio)) as wav:
            duration = wav.getnframes() / wav.getframerate()
        with request('/health') as response:
            health = json.load(response)
        output = ROOT / 'qa' / f'tts-accelerated-service-{index}.wav'
        output.write_bytes(audio)
        item = {'text': text, 'http_delivery_seconds': elapsed, 'audio_seconds': duration,
                'rtf': elapsed / duration, 'backend': health.get('backend', 'standard'),
                'engine_metrics': health.get('lastSynthesis'), 'sample': str(output)}
        results.append(item)
        print(json.dumps(item), flush=True)
    report = {'prepare_seconds': preparation, 'results': results}
    (ROOT / 'qa/tts-accelerated-service-20261031.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
