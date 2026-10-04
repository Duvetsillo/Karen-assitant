"""
Karen - Cliente de voz (Windows)
Reconstruido tras cambio de PC. Referencia: KAREN_Bitacora / KAREN_Errores / KAREN_Roadmap.

Requiere:
    pip install -r requirements.txt

ffmpeg.exe y ffprobe.exe deben estar copiados directo en la carpeta del proyecto
(C:\\karen\\), NO depender del PATH del sistema (ver Error 2 en KAREN_Errores.md).
"""

from __future__ import annotations

import os
import sys
import asyncio
import tempfile
import argparse

from config import KarenConfig, load_config

# ---------------------------------------------------------------------------
# Rutas y configuración
# ---------------------------------------------------------------------------

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))

# ffmpeg copiado directo en la carpeta del proyecto (lección del Error 2)
os.environ["PATH"] = CARPETA_PROYECTO + os.pathsep + os.environ["PATH"]

CONFIG = load_config()
SERVIDOR = CONFIG.server
SAMPLE_RATE = CONFIG.sample_rate
VOZ = CONFIG.voice

# VAD: np.max supera a np.mean para detección de picos cuando el piso de
# ruido y la voz están cerca en amplitud (lección de KAREN_Roadmap 3.2)
UMBRAL_VOZ = CONFIG.voice_threshold

# Filtro RMS pre-transcripción: evita que Whisper alucine frases fantasma
# sobre silencio o ruido ambiente
UMBRAL_RMS = CONFIG.rms_threshold

WAKE_WORD_ACTIVO = False  # cambiar a True cuando exista C:\karen\karen.onnx
RUTA_KAREN_ONNX = os.path.join(CARPETA_PROYECTO, "karen.onnx")


# ---------------------------------------------------------------------------
# Utilidades de audio
# ---------------------------------------------------------------------------

def hay_voz(audio_np: np.ndarray) -> bool:
    """Detección de picos de voz usando np.max (no np.mean)."""
    import numpy as np

    return float(np.max(np.abs(audio_np))) > UMBRAL_VOZ


def pasa_filtro_rms(audio_np: np.ndarray) -> bool:
    """Filtro de energía RMS para descartar silencio/ruido antes de Whisper."""
    import numpy as np

    rms = float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
    return rms > UMBRAL_RMS


def grabar_voz(segundos: int = 5) -> np.ndarray:
    import sounddevice as sd

    print(f"Grabando {segundos} segundos... habla ahora")
    audio = sd.rec(int(segundos * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribir(modelo_whisper, audio_np: np.ndarray) -> str:
    import soundfile as sf

    if not pasa_filtro_rms(audio_np):
        return ""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        ruta = f.name
    sf.write(ruta, audio_np, SAMPLE_RATE)
    resultado = modelo_whisper.transcribe(ruta, language="es", fp16=False)
    os.unlink(ruta)
    return resultado["text"].strip()


# ---------------------------------------------------------------------------
# Comunicación con el servidor (Flask + Ollama en la LXC)
# ---------------------------------------------------------------------------

def preguntar_karen(texto: str, servidor: str = SERVIDOR, timeout: int = CONFIG.request_timeout) -> str:
    import requests

    try:
        r = requests.post(f"{servidor}/chat", json={"mensaje": texto}, timeout=timeout)
        r.raise_for_status()
        return r.json()["respuesta"]
    except (requests.RequestException, KeyError, ValueError) as e:
        return f"Error: {e}"


def verificar_servidor(servidor: str = SERVIDOR) -> bool:
    import requests

    try:
        r = requests.get(f"{servidor}/salud", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# Voz (Edge-TTS)
# ---------------------------------------------------------------------------

async def hablar_async(texto: str):
    import edge_tts
    import sounddevice as sd
    import soundfile as sf

    communicate = edge_tts.Communicate(texto, VOZ)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        ruta = f.name
    await communicate.save(ruta)
    data, fs = sf.read(ruta)
    sd.play(data, fs)
    sd.wait()
    os.unlink(ruta)


def hablar(texto: str):
    asyncio.run(hablar_async(texto))


# ---------------------------------------------------------------------------
# Wake word (gancho para cuando exista karen.onnx - Fase 3)
# ---------------------------------------------------------------------------

def cargar_wake_word():
    """
    Placeholder para activar detección de "Karen" sin ENTER.
    Descomentar y usar cuando karen.onnx esté entrenado y copiado aquí.
    """
    if not os.path.exists(RUTA_KAREN_ONNX):
        return None
    from openwakeword.model import Model
    return Model(wakeword_models=[RUTA_KAREN_ONNX], inference_framework="onnx")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Cliente de voz local de KAREN")
    parser.add_argument("--server", help="URL del servidor KAREN (o KAREN_SERVER)")
    parser.add_argument("--whisper-model", help="Modelo Whisper local (o KAREN_WHISPER_MODEL)")
    parser.add_argument("--voice", help="Voz Edge-TTS (o KAREN_VOICE)")
    args = parser.parse_args(argv)
    config = load_config({"server": args.server, "whisper_model": args.whisper_model, "voice": args.voice})

    print("Verificando servidor...")
    if not verificar_servidor(config.server):
        print(f"No se pudo contactar al servidor en {config.server}")
        print("Verifica que el servidor KAREN esté activo y que KAREN_SERVER sea correcto.")
        sys.exit(1)
    print("Servidor OK.\n")

    import requests
    import whisper

    print("Cargando Whisper...")
    modelo_whisper = whisper.load_model(config.whisper_model)
    print("Whisper listo.\n")

    if WAKE_WORD_ACTIVO:
        print("Cargando modelo de wake word...")
        oww_model = cargar_wake_word()
        if oww_model is None:
            print("No se encontró karen.onnx, cayendo a activación por ENTER.\n")
    else:
        oww_model = None

    print("Karen lista, Jefe. Di 'salir' para terminar.\n")

    while True:
        try:
            entrada = input("ENTER para hablar (o escribe los segundos): ").strip()
            segundos = int(entrada) if entrada.isdigit() else 5

            audio = grabar_voz(segundos)

            if not hay_voz(audio):
                print("No detecté voz, intenta de nuevo.\n")
                continue

            texto = transcribir(modelo_whisper, audio)
            if not texto:
                print("No entendí, intenta de nuevo.\n")
                continue

            print(f"Tú: {texto}\n")

            if "salir" in texto.lower():
                hablar("Hasta luego, Jefe.")
                break

            if "reset" in texto.lower() or "limpiar" in texto.lower():
                requests.post(f"{config.server}/chat", json={"reset": True}, timeout=config.request_timeout)
                print("Memoria limpiada.\n")
                continue

            print("Karen pensando...")
            respuesta = preguntar_karen(texto, config.server, config.request_timeout)
            print(f"Karen: {respuesta}\n")
            hablar(respuesta)

        except KeyboardInterrupt:
            sys.exit()


if __name__ == "__main__":
    main()
