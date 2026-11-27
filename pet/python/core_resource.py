"""Cross-client resource ownership using OS locks, never expiring leases.

The worker keeps the lock until its parent's stdin closes. A crash releases the
OS handle automatically. Lock files contain no audio, identifiers, or secrets.
"""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import sys
import tempfile


class ResourceBusy(OSError):
    pass


def microphone_path():
    configured = os.getenv('KAREN_RESOURCE_DIR')
    if configured and not Path(configured).is_absolute():
        raise ValueError('KAREN_RESOURCE_DIR debe ser una ruta absoluta.')
    base = Path(configured) if configured else Path(
        os.getenv('LOCALAPPDATA') or tempfile.gettempdir()) / 'KarenCore' / 'locks'
    return base / 'microphone.lock'


@contextmanager
def microphone_guard(path=None):
    """Acquire without waiting. Never unlink a lock file while clients use it."""
    path = Path(path) if path is not None else microphone_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        # Windows requires the locked byte to exist. Never truncate this file.
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN} or getattr(exc, 'winerror', None) in {32, 33}:
                raise ResourceBusy('Otra interfaz de Karen usa el micrófono.') from exc
            raise
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--resource', choices=('microphone', 'inference'), default='microphone')
    args = parser.parse_args()
    path = microphone_path()
    if args.resource == 'inference':
        path = path.with_name('ollama-inference.lock')
    try:
        with microphone_guard(path):
            print('ACQUIRED', flush=True)
            # No commands accepted; the pipe lifetime is the ownership lifetime.
            sys.stdin.buffer.read()
    except ResourceBusy:
        print('BUSY', flush=True)
        return 2
    except (OSError, ValueError):
        print('UNAVAILABLE', flush=True)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
