"""OpenClaw local TTS CLI; writes a native Opus voice note."""
import argparse
import subprocess
import threading
import sys
from pathlib import Path

from speech_text import spoken_text
from voice_local import synthesize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', help='Omitir para recibir UTF-8 por stdin sin texto en argumentos')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--engine', choices=['kokoro', 'qwen3', 'edge'], default='qwen3')
    args = parser.parse_args()
    if (Path(__file__).resolve().parent / 'voice-models/active-voice.json').is_file() and args.engine != 'qwen3':
        parser.error('La identidad compartida está fijada en qwen3; no se sustituirá por otra voz')
    raw = args.text if args.text is not None else sys.stdin.buffer.read(65537).decode('utf-8')
    text = spoken_text(raw)
    if len(text) > 4096:
        parser.error('Respuesta mayor de 4096 caracteres')
    if args.engine == 'edge':
        from config import load_config
        from dataclasses import replace
        from voice import SpeechPlayer
        audio = SpeechPlayer().encode(text, replace(load_config(), tts_engine='edge'))
    elif args.engine == 'qwen3':
        from expressive_voice import synthesize as expressive_synthesize
        audio = expressive_synthesize(text, threading.Event())
    else:
        from config import load_config
        config = load_config()
        audio = synthesize(text, config.local_voice, config.voice_rate, threading.Event(), config.local_pitch_semitones)
    ffmpeg = Path(__file__).resolve().parent / 'ffmpeg.exe'
    # WAV stays in memory; output is the file requested by OpenClaw.
    result = subprocess.run(
        [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
         '-i', 'pipe:0', '-ac', '1', '-ar', '48000', '-c:a', 'libopus',
         '-b:a', '64k', '-f', 'ogg', str(args.output)],
        input=audio, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        timeout=30, creationflags=0x08000000,
    )
    if result.returncode:
        raise RuntimeError('No se pudo codificar la nota de voz')


if __name__ == '__main__':
    main()
