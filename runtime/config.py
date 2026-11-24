"""Portable configuration for the KAREN voice client."""

from dataclasses import dataclass, asdict, fields, field
import json
from pathlib import Path
import os
import sqlite3
from urllib.parse import urlparse


@dataclass(frozen=True)
class KarenConfig:
    server: str = "http://127.0.0.1:11434"
    backend: str = "ollama"
    api_key: str = ""
    model: str = "qwen2:0.5b"
    voice: str = "es-MX-DaliaNeural"
    voice_rate: str = "-1%"
    voice_pitch: str = "+0Hz"
    memory_dir: str = r"C:\Obsidian\Data Base\Proyecto FRIDAY"
    memory_files: str = "IDENTITY.md,SOUL.md,USER.md,FRIDAY_Blueprint.md,FRIDAY_Protocolos_Seguridad.md,MEMORY.md,MEMORY_PROTOCOL.md"
    whisper_model: str = "base"
    sample_rate: int = 16000
    voice_threshold: float = 0.15
    rms_threshold: float = 0.02
    request_timeout: int = 90
    wake_word_enabled: bool = True
    command_seconds: int = 30
    end_silence_seconds: float = 0.8
    wake_word_threshold: float = 0.5
    input_device: int | str | None = None
    tts_enabled: bool = True
    wake_model: str = "karen.onnx"
    wake_confirmations: int = 2
    model_choices: dict = field(default_factory=dict)
    stt_engine: str = 'whisper'
    tts_engine: str = 'edge'
    local_voice: str = 'ef_dora'
    local_pitch_semitones: float = 0.0
    voice_style: str = 'serene'
    allow_suggestions: bool = True
    allow_sarcasm: bool = True
    wake_mode: str = 'transcript'
    wake_auto_start: bool = False

    def __post_init__(self) -> None:
        from karen_personality import validate_style
        validate_style(self.voice_style)
        if self.wake_mode not in {'transcript', 'onnx'}:
            raise ValueError('Modo de activacion desconocido')
        if any(not isinstance(value, bool) for value in (self.allow_suggestions, self.allow_sarcasm, self.wake_auto_start)):
            raise ValueError('Las preferencias de personalidad y activacion deben ser booleanas')
        if not -3 <= self.local_pitch_semitones <= 3:
            raise ValueError('El ajuste de tono local debe estar entre -3 y 3 semitonos')
        if not 0.2 <= self.end_silence_seconds <= 3:
            raise ValueError('El silencio final debe estar entre 0.2 y 3 segundos')
        if self.stt_engine not in {'whisper', 'faster-small', 'faster-turbo'} or self.tts_engine not in {'edge', 'kokoro', 'qwen3'}:
            raise ValueError('Motor de voz desconocido')
        if not isinstance(self.model_choices, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.model_choices.items()):
            raise ValueError("model_choices must map nodes to model names")
        if self.sample_rate != 16000:
            raise ValueError("La captura de voz y ONNX requieren 16000 Hz")
        if not 1 <= self.wake_confirmations <= 10:
            raise ValueError("wake_confirmations must be between 1 and 10")
        if self.backend not in {"ollama", "karen"}:
            raise ValueError("backend must be ollama or karen")
        parsed = urlparse(self.server)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("server must be an absolute http:// or https:// URL")
        if self.sample_rate <= 0 or self.request_timeout <= 0 or self.command_seconds <= 0:
            raise ValueError("sample_rate, request_timeout, and command_seconds must be greater than zero")
        if not 0 < self.voice_threshold <= 1 or not 0 < self.rms_threshold <= 1:
            raise ValueError("audio thresholds must be between 0 and 1")
        if not 0 < self.wake_word_threshold <= 1:
            raise ValueError("wake_word_threshold must be between 0 and 1")


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


CONFIG_PATH = Path(__file__).resolve().with_name("settings.json")
PROFILES = {
    "cloud": {"server": "http://127.0.0.1:11434", "backend": "ollama", "model": "gemma4:31b-cloud"},
    "pc": {"server": "http://127.0.0.1:11434", "backend": "ollama", "model": "qwen2:0.5b"},
    "homelab": {"server": "http://192.168.100.146:11434", "backend": "ollama", "model": "llama3.2:3b"},
    "karen": {"server": "http://192.168.100.146:5000", "backend": "karen", "model": "llama3.2:3b"},
}


def save_config(config: KarenConfig, *, sync_core=True) -> bool:
    data = asdict(config)
    data.pop("api_key")  # Credentials stay in the environment/session.
    temporary = CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CONFIG_PATH)
    if sync_core and os.getenv('KAREN_CORE_DB'):
        try:
            from conversations import Conversations
            Conversations().set_voice_style(config.voice_style)
        except (OSError, sqlite3.Error, ValueError):
            return False
    return True


def load_config(overrides: dict[str, object] | None = None) -> KarenConfig:
    raw_input_device = os.getenv("KAREN_INPUT_DEVICE")
    input_device: int | str | None = None
    if raw_input_device:
        input_device = int(raw_input_device) if raw_input_device.isdigit() else raw_input_device
    values: dict[str, object] = {
        "server": os.getenv("KAREN_SERVER", KarenConfig.server),
        "api_key": os.getenv("KAREN_API_KEY", KarenConfig.api_key),
        "model": os.getenv("KAREN_MODEL", KarenConfig.model),
        "voice": os.getenv("KAREN_VOICE", KarenConfig.voice),
        "voice_rate": os.getenv("KAREN_VOICE_RATE", KarenConfig.voice_rate),
        "voice_pitch": os.getenv("KAREN_VOICE_PITCH", KarenConfig.voice_pitch),
        "voice_style": os.getenv("KAREN_VOICE_STYLE", KarenConfig.voice_style),
        "memory_dir": os.getenv("KAREN_MEMORY_DIR", KarenConfig.memory_dir),
        "memory_files": os.getenv("KAREN_MEMORY_FILES", KarenConfig.memory_files),
        "whisper_model": os.getenv("KAREN_WHISPER_MODEL", KarenConfig.whisper_model),
        "sample_rate": int(os.getenv("KAREN_SAMPLE_RATE", str(KarenConfig.sample_rate))),
        "voice_threshold": float(os.getenv("KAREN_VOICE_THRESHOLD", str(KarenConfig.voice_threshold))),
        "rms_threshold": float(os.getenv("KAREN_RMS_THRESHOLD", str(KarenConfig.rms_threshold))),
        "request_timeout": int(os.getenv("KAREN_REQUEST_TIMEOUT", str(KarenConfig.request_timeout))),
        "wake_word_enabled": _as_bool(os.getenv("KAREN_WAKE_WORD", str(KarenConfig.wake_word_enabled))),
        "command_seconds": int(os.getenv("KAREN_COMMAND_SECONDS", str(KarenConfig.command_seconds))),
        "wake_word_threshold": float(os.getenv("KAREN_WAKE_WORD_THRESHOLD", str(KarenConfig.wake_word_threshold))),
        "input_device": input_device,
        "tts_enabled": _as_bool(os.getenv("KAREN_TTS_ENABLED", "true")),
        "wake_model": os.getenv("KAREN_WAKE_MODEL", "karen.onnx"),
        "wake_confirmations": int(os.getenv("KAREN_WAKE_CONFIRMATIONS", "2")),
    }
    if CONFIG_PATH.exists():
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        allowed = {field.name for field in fields(KarenConfig)} - {"api_key"}
        for key in allowed:
            env_name = "KAREN_WAKE_WORD" if key == "wake_word_enabled" else "KAREN_" + key.upper()
            if key in saved and env_name not in os.environ:
                values[key] = saved[key]
    values["backend"] = os.getenv("KAREN_BACKEND", values.get("backend", "ollama"))
    if os.getenv('KAREN_CORE_DB') and 'KAREN_VOICE_STYLE' not in os.environ:
        try:
            from conversations import Conversations
            shared_style = Conversations().get_voice_style()
            if shared_style:
                values['voice_style'] = shared_style
        except (OSError, sqlite3.Error, ValueError):
            pass  # The UI reports the Core failure and opens its local archive.
    if overrides:
        overrides = dict(overrides)
        profile = overrides.pop("profile", None)
        if profile:
            values.update(PROFILES[str(profile)])
        values.update({key: value for key, value in overrides.items() if value is not None})
    if isinstance(values["input_device"], str) and values["input_device"].isdigit():
        values["input_device"] = int(values["input_device"])
    return KarenConfig(**values)
