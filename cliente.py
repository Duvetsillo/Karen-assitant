"""
Karen - Cliente de voz (Windows)
Reconstruido tras cambio de PC. Referencia: KAREN_Bitacora / KAREN_Errores / KAREN_Roadmap.

Requiere:
    pip install -r requirements.txt

ffmpeg.exe y ffprobe.exe deben estar copiados directo en la carpeta del proyecto
(C:\\karen\\), NO depender del PATH del sistema (ver Error 2 en KAREN_Errores.md).
"""

import os
import sys
import asyncio
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf
import requests
import edge_tts
import whisper

# ---------------------------------------------------------------------------
# Rutas y configuración
# ---------------------------------------------------------------------------

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))

# ffmpeg copiado directo en la carpeta del proyecto (lección del Error 2)
os.environ["PATH"] = CARPETA_PROYECTO + os.pathsep + os.environ["PATH"]

SERVIDOR = "http://192.168.100.66:5000"
SAMPLE_RATE = 16000
VOZ = "es-ES-ElviraNeural"

# VAD: np.max supera a np.mean para detección de picos cuando el piso de
# ruido y la voz están cerca en amplitud (lección de KAREN_Roadmap 3.2)
UMBRAL_VOZ = 0.15

# Filtro RMS pre-transcripción: evita que Whisper alucine frases fantasma
# sobre silencio o ruido ambiente
UMBRAL_RMS = 0.02

WAKE_WORD_ACTIVO = False  # cambiar a True cuando exista C:\karen\karen.onnx
RUTA_KAREN_ONNX = os.path.join(CARPETA_PROYECTO, "karen.onnx")


# ---------------------------------------------------------------------------
# Utilidades de audio
# ---------------------------------------------------------------------------

def hay_voz(audio_np: np.ndarray) -> bool:
    """Detección de picos de voz usando np.max (no np.mean)."""
    return float(np.max(np.abs(audio_np))) > UMBRAL_VOZ


def pasa_filtro_rms(audio_np: np.ndarray) -> bool:
    """Filtro de energía RMS para descartar silencio/ruido antes de Whisper."""
    rms = float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
    return rms > UMBRAL_RMS


def grabar_voz(segundos: int = 5) -> np.ndarray:
    print(f"Grabando {segundos} segundos... habla ahora")
    audio = sd.rec(int(segundos * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribir(modelo_whisper, audio_np: np.ndarray) -> str:
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

def preguntar_karen(texto: str) -> str:
    try:
        r = requests.post(f"{SERVIDOR}/chat", json={"mensaje": texto}, timeout=90)
        return r.json()["respuesta"]
    except Exception as e:
        return f"Error: {e}"


def verificar_servidor() -> bool:
    try:
        r = requests.get(f"{SERVIDOR}/salud", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Voz (Edge-TTS)
# ---------------------------------------------------------------------------

async def hablar_async(texto: str):
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

def main():
    print("Verificando servidor...")
    if not verificar_servidor():
        print(f"No se pudo contactar al servidor en {SERVIDOR}")
        print("Verifica que el karen.service siga activo en la LXC (192.168.100.66).")
        sys.exit(1)
    print("Servidor OK.\n")

    print("Cargando Whisper...")
    modelo_whisper = whisper.load_model("base")
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
                requests.post(f"{SERVIDOR}/chat", json={"reset": True})
                print("Memoria limpiada.\n")
                continue

            print("Karen pensando...")
            respuesta = preguntar_karen(texto)
            print(f"Karen: {respuesta}\n")
            hablar(respuesta)

        except KeyboardInterrupt:
            sys.exit()


if __name__ == "__main__":
    main()
