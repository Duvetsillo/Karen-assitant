"""Every local client uses the same immutable voice profile."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'desktop-pet/python'))
from shared_voice_client import synthesize as shared_synthesize, release as shared_release

def synthesize(text, cancelled, style='serene'):
    return shared_synthesize(ROOT, text, cancelled, style=style)


def release():
    return shared_release(ROOT)
