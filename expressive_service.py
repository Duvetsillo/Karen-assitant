"""Compatibility entry point for Karen's shared original-voice service."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'desktop-pet/python'))
from shared_voice_service import serve
if __name__ == '__main__':
    serve(ROOT)
