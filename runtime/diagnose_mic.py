"""Bounded Windows microphone diagnostic; no audio is saved or transcribed."""

import argparse
import math
import time

import numpy as np
import sounddevice as sd

from config import load_config

SAMPLE_RATE = 16000
BLOCKSIZE = 1280


def probe(device, seconds):
    if not 0 < seconds <= 30 or not math.isfinite(seconds):
        raise ValueError("La duración debe estar entre 0 y 30 segundos.")
    info = sd.query_devices(device, 'input')
    print(f"Micrófono: {info['name']}")
    print(f"Duración: {seconds:g} segundos; audio no guardado.")
    blocks = max(1, math.ceil(seconds * SAMPLE_RATE / BLOCKSIZE))
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE,
                           channels=1, dtype="int16", device=device) as stream:
        started = time.monotonic()
        overflows = 0
        peak = 0
        energy = 0.0
        for _ in range(blocks):
            chunk, overflowed = stream.read(BLOCKSIZE)
            audio = np.frombuffer(chunk, dtype=np.int16)
            peak = max(peak, int(np.max(np.abs(audio.astype(np.int32)))) if audio.size else 0)
            energy += float(np.mean(audio.astype(np.float64) ** 2)) if audio.size else 0
            overflows += bool(overflowed)
    result = {'device': device, 'blocks': blocks, 'elapsed_seconds': round(time.monotonic() - started, 3),
              'rms': round(math.sqrt(energy / blocks), 1), 'peak': peak, 'overflows': overflows}
    print(result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default=None, help='Índice o nombre del dispositivo de entrada.')
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args()
    configured = load_config().input_device if args.device is None else args.device
    device = int(configured) if isinstance(configured, str) and configured.isdecimal() else configured
    probe(device, args.seconds)
