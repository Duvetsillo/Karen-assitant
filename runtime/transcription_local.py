"""Shared offline Spanish recognizer for desktop and WhatsApp."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
_models = {}
_dll_handles = []

def recognize(audio, engine="faster-turbo"):
    import ctranslate2
    from faster_whisper import WhisperModel
    if engine not in _models:
        library = ROOT / "expressive-runtime/Lib/site-packages/torch/lib"
        if os.name == "nt" and library.is_dir():
            os.environ["PATH"] = str(library) + os.pathsep + os.environ.get("PATH", "")
            _dll_handles.append(os.add_dll_directory(str(library)))
        device = "cuda" if engine == "faster-turbo" and ctranslate2.get_cuda_device_count() else "cpu"
        folder = "faster-whisper-turbo" if engine == "faster-turbo" else "faster-whisper-small"
        _models[engine] = WhisperModel(str(ROOT / "voice-models" / folder), device=device,
            compute_type="int8_float16" if device == "cuda" else "int8", cpu_threads=4, local_files_only=True)
    segments, _ = _models[engine].transcribe(audio, language="es", beam_size=5,
        vad_filter=True, vad_parameters={"min_silence_duration_ms":500,"speech_pad_ms":200},
        initial_prompt="Conversación en español latinoamericano con Karen y Friday.",
        condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segments).strip()
