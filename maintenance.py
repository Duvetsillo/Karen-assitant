"""Reproducible local backup and integrity check; never restores over live data.

SQLite files use the online backup API. WAL/SHM and live lock files must not be
restored from a second point in time. Windows backups receive a user-only ACL.
"""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent


def _digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def _private_directory(destination):
    destination.mkdir(parents=True, exist_ok=False)
    if os.name == 'nt':
        account = subprocess.check_output(['whoami'], text=True).strip()
        subprocess.run(['icacls', str(destination), '/inheritance:r', '/grant:r',
                        f'{account}:(OI)(CI)F'], check=True, capture_output=True)
    else:
        destination.chmod(0o700)


def backup(destination, root=ROOT):
    destination, root = Path(destination).resolve(), Path(root).resolve()
    if destination == root or destination.is_relative_to(root / '.private'):
        raise ValueError('No guardes un respaldo dentro de los datos de origen.')
    _private_directory(destination)
    manifest = {'format': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
                'repositories': {}, 'files': {}}
    with zipfile.ZipFile(destination / 'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for label, repository in [('classic', root), ('desktop-pet', root / 'desktop-pet')]:
            if not (repository / '.git').exists():
                continue
            manifest['repositories'][label] = {
                'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip(),
                'status': subprocess.check_output(['git', 'status', '--short'], cwd=repository, text=True),
            }
            names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=repository).decode().split('\0')
            for name in filter(None, names):
                path = repository / name
                if path.is_file() and not path.is_symlink():
                    archive.write(path, f'{label}/{name}')
    # Explicit allowlist. Do not copy models, environments, arbitrary home files,
    # or decrypt credentials. Electron userData requires its own stopped backup.
    sources = [root / '.private', root / 'settings.json', root / 'admin_policy.json']
    for source in sources:
        paths = source.rglob('*') if source.is_dir() else [source]
        for path in paths:
            if not path.is_file() or path.is_symlink() or path.name.endswith(('-wal', '-shm', '.lock')):
                continue
            relative = path.relative_to(root)
            target = destination / 'user-data' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with path.open('rb') as stream:
                is_sqlite = stream.read(16) == b'SQLite format 3\x00'
            if is_sqlite:
                with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as src, \
                     closing(sqlite3.connect(target)) as dst:
                    src.backup(dst)
                    if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('El respaldo SQLite no pasó integrity_check.')
            else:
                shutil.copyfile(path, target)
            manifest['files'][str(Path('user-data') / relative)] = {
                'bytes': target.stat().st_size, 'sha256': _digest(target), 'sqlite': is_sqlite,
            }
    manifest['files']['source.zip'] = {'bytes': (destination / 'source.zip').stat().st_size,
                                      'sha256': _digest(destination / 'source.zip'), 'sqlite': False}
    # A failed backup never receives a complete manifest.
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return len(manifest['files'])


def verify(destination):
    destination = Path(destination).resolve()
    manifest = json.loads((destination / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 1:
        raise ValueError('Formato de respaldo incompatible.')
    for relative, expected in manifest['files'].items():
        path = (destination / relative).resolve()
        if not path.is_relative_to(destination) or path.is_symlink():
            raise ValueError('Ruta de respaldo inválida.')
        if path.stat().st_size != expected['bytes'] or _digest(path) != expected['sha256']:
            raise ValueError('El respaldo contiene un archivo alterado o incompleto.')
        if expected['sqlite']:
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('SQLite no pasó integrity_check.')
    return len(manifest['files'])


def main():
    parser = argparse.ArgumentParser(description='Respaldo local verificable de Karen; contiene datos privados')
    parser.add_argument('action', choices=('backup', 'verify'))
    parser.add_argument('directory', type=Path, help='Directorio nuevo para backup, existente para verify')
    args = parser.parse_args()
    try:
        count = backup(args.directory) if args.action == 'backup' else verify(args.directory)
    except (OSError, ValueError, sqlite3.Error, subprocess.CalledProcessError):
        parser.exit(1, 'Respaldo incompleto o inválido. No uses esos archivos para recuperación.\n')
    print(f'{args.action}: OK; {count} archivos verificados localmente.')


if __name__ == '__main__':
    main()
