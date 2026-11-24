"""Load the resource arbiter shared with the independently packaged Pet client."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'desktop-pet' / 'python'))
from core_resource import ResourceBusy, microphone_guard, microphone_path

__all__ = ['ResourceBusy', 'microphone_guard', 'microphone_path']
