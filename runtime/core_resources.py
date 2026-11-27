"""Load the resource arbiter shared with the independently packaged Pet client."""

from pathlib import Path
import sys

_root = Path(__file__).resolve().parent
for _candidate in (_root.parent / 'pet' / 'python',
                   _root.parent / 'app.asar.unpacked' / 'python',
                   _root / 'desktop-pet' / 'python'):
    if (_candidate / 'core_resource.py').is_file():
        sys.path.insert(0, str(_candidate))
        break
from core_resource import ResourceBusy, microphone_guard, microphone_path

__all__ = ['ResourceBusy', 'microphone_guard', 'microphone_path']
