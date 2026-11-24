"""Windows WASAPI loopback. No files, camera, screen frames or network calls."""
import base64
import json
import sys
import threading
import time

def emit(value):
    print(json.dumps(value), flush=True)

def main():
    import numpy as np
    import pyaudiowpatch as pa
    stop = threading.Event()
    threading.Thread(target=lambda: (sys.stdin.readline(), stop.set()), daemon=True).start()
    chunks = []
    last_meter = 0.0
    with pa.PyAudio() as audio:
        device = audio.get_default_wasapi_loopback()
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        def callback(data, count, info, flags):
            nonlocal last_meter
            if stop.is_set():
                return (None, pa.paComplete)
            values = np.frombuffer(data, dtype=np.float32).reshape(-1, channels).mean(axis=1)
            chunks.append(values)
            now = time.monotonic()
            if now - last_meter > 0.1:
                last_meter = now
                emit({"energy": float(min(1, np.sqrt(np.mean(values * values)) * 12))})
            return (None, pa.paContinue)
        with audio.open(format=pa.paFloat32, channels=channels, rate=rate, input=True,
                        input_device_index=device["index"], frames_per_buffer=1024,
                        stream_callback=callback):
            emit({"ready": True})
            stop.wait(60)
            stop.set()
    samples = np.concatenate(chunks) if chunks else np.zeros(1600, dtype=np.float32)
    positions = np.arange(min(960000, int(len(samples) * 16000 / rate))) * rate / 16000
    mono = np.interp(positions, np.arange(len(samples)), samples)
    pcm = (np.clip(mono, -1, 1) * 32767).astype(np.int16)
    emit({"audio": base64.b64encode(pcm.tobytes()).decode("ascii")})

if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit({"error": "No se pudo abrir WASAPI. Revisa el dispositivo de salida y PyAudioWPatch."})
        sys.exit(1)
