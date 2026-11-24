import numpy as np
import sounddevice as sd

for device in (31, 33, 41):
    print(f"DEVICE {device}: {sd.query_devices(device)['name']}")
    try:
        with sd.RawInputStream(samplerate=16000, blocksize=1280,
                               channels=1, dtype='int16', device=device) as stream:
            peaks = []
            for _ in range(20):
                chunk, _ = stream.read(1280)
                peaks.append(int(np.max(np.abs(np.frombuffer(chunk, dtype=np.int16)))))
        print(f"peak={max(peaks)}")
    except Exception as error:
        print(f"ERROR={error}")
