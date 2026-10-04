import pytest

from config import KarenConfig, load_config


def test_default_config_is_localhost(monkeypatch):
    monkeypatch.delenv("KAREN_SERVER", raising=False)
    config = load_config()
    assert config.server == "http://127.0.0.1:5000"
    assert config.whisper_model == "base"


def test_environment_overrides_are_loaded(monkeypatch):
    monkeypatch.setenv("KAREN_SERVER", "http://192.168.1.20:5000")
    monkeypatch.setenv("KAREN_REQUEST_TIMEOUT", "30")
    config = load_config()
    assert config.server == "http://192.168.1.20:5000"
    assert config.request_timeout == 30


def test_explicit_overrides_win_over_environment(monkeypatch):
    monkeypatch.setenv("KAREN_SERVER", "http://192.168.1.20:5000")
    config = load_config({"server": "http://127.0.0.1:5000"})
    assert config.server == "http://127.0.0.1:5000"


def test_invalid_server_is_rejected():
    with pytest.raises(ValueError, match="absolute"):
        KarenConfig(server="192.168.1.20:5000")
