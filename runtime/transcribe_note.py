"""OpenClaw audio CLI: local Spanish transcription; stdout is transcript only."""
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    args = parser.parse_args()
    if not args.audio.is_file() or args.audio.stat().st_size > 20 * 1024 * 1024:
        parser.error("Audio inexistente o mayor de 20 MB")
    from transcription_local import recognize
    from config import load_config
    transcript = recognize(str(args.audio), load_config().stt_engine)
    sys.stdout.reconfigure(encoding="utf-8")
    print(transcript)


if __name__ == "__main__":
    main()
