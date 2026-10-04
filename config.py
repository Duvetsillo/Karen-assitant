"""Portable configuration for the KAREN voice client."""

from dataclasses import dataclass
import os
from urllib.parse import urlparse


@dataclass(frozen=True)
class KarenConfig:
    server: str = "http://127.0.0.1:5000"
    voice: str = "es-ES-ElviraNeural"
    whisper_model: str = "base"
    sample_rate: int = 16000
    voice_threshold: float = 0.15
    rms_threshold: float = 0.02
    request_timeout: int = 90

    def __post_init__(self) -> None:
        parsed = urlparse(self.server)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("server must be an absolute http:// or https:// URL")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be greater than zero")
        if not 0 < self.voice_threshold <= 1:
            raise ValueError("voice_threshold must be between 0 and 1")
        if not 0 < self.rms_threshold <= 1:
            raise ValueError("rms_threshold must be between 0 and 1")


def load_config(overrides: dict[str, object] | None = None) -> KarenConfig:
    """Load settings from KAREN_* environment variables and explicit overrides."""
    values: dict[str, object] = {
        "server": os.getenv("KAREN_SERVER", KarenConfig.server),
        "voice": os.getenv("KAREN_VOICE", KarenConfig.voice),
        "whisper_model": os.getenv("KAREN_WHISPER_MODEL", KarenConfig.whisper_model),
        "sample_rate": int(os.getenv("KAREN_SAMPLE_RATE", str(KarenConfig.sample_rate))),
        "voice_threshold": float(os.getenv("KAREN_VOICE_THRESHOLD", str(KarenConfig.voice_threshold))),
        "rms_threshold": float(os.getenv("KAREN_RMS_THRESHOLD", str(KarenConfig.rms_threshold))),
        "request_timeout": int(os.getenv("KAREN_REQUEST_TIMEOUT", str(KarenConfig.request_timeout))),
    }
    if overrides:
        values.update({key: value for key, value in overrides.items() if value is not None})
    return KarenConfig(**values)
