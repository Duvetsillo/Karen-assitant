"""Real local TTS cancellation from the classic Python client. No playback/mic."""
import io
import json
from pathlib import Path
import sys
import threading
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop-pet/python'))
from shared_voice_client import session, request, ensure_service, synthesize
from voice_profile import load_profile


def main():
    profile = load_profile(ROOT)
    opener, token = session(ROOT)
    ensure_service(ROOT,opener,token,profile)

    def health():
        with request(opener,token,'/health') as response:
            return json.load(response)

    assert health()['phase'] in {'cold','ready'}, 'Voice is busy; do not interrupt another client'
    with request(opener,token,'/prepare',profile.public(),timeout=240) as response:
        assert json.load(response)['ready']
    stop = threading.Event()
    result = {}

    def worker():
        try:
            result['audio'] = synthesize(ROOT,'Esta prueba sintética verifica la cancelación de Karen clásica. '*8,stop)
        except Exception as error:
            result['error'] = type(error).__name__

    thread = threading.Thread(target=worker,daemon=True)
    thread.start()
    deadline = time.monotonic()+30
    while health()['phase'] != 'generating':
        assert thread.is_alive() and time.monotonic()<deadline
        time.sleep(.05)
    started = time.perf_counter()
    stop.set()
    thread.join(2)
    client_elapsed = time.perf_counter()-started
    assert not thread.is_alive() and result.get('audio') == b'' and 'error' not in result
    while health()['phase'] != 'ready':
        assert time.perf_counter()-started<10
        time.sleep(.05)
    recovered = time.perf_counter()-started
    audio = synthesize(ROOT,'La conexión ya está libre y podemos continuar.',threading.Event(),style='serene')
    with wave.open(io.BytesIO(audio)) as wav:
        duration = wav.getnframes()/wav.getframerate()
    assert duration>1
    report = {'real_local_model':True,'client_cancel_seconds':client_elapsed,
              'service_recovery_seconds':recovered,'next_audio_seconds':duration,
              'profile_id':profile.id,'reference_sha256':profile.reference_sha256,
              'playback':False,'microphone':False}
    (ROOT/'qa/classic-voice-cancel-20261101.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
