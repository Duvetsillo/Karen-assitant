"""OpenClaw CLI adapter: the same pinned Karen voice, encoded as Ogg/Opus."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import threading
import sys

from shared_voice_client import synthesize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--text', help='Omit to read UTF-8 from stdin')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    ffmpeg = root / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    executable = str(ffmpeg) if ffmpeg.is_file() else shutil.which('ffmpeg')
    if not executable:
        raise RuntimeError('Instala FFmpeg para convertir las notas de voz')
    text = args.text if args.text is not None else sys.stdin.buffer.read(65537).decode('utf-8')
    audio = synthesize(root, text, threading.Event())
    result = subprocess.run([executable, '-hide_banner', '-loglevel', 'error', '-y',
        '-i', 'pipe:0', '-ac', '1', '-ar', '48000', '-c:a', 'libopus', '-b:a', '64k', '-f', 'ogg', str(args.output)],
        input=audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError('No se pudo convertir la voz original a Opus')


if __name__ == '__main__':
    main()
