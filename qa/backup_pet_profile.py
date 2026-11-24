"""Copy durable Desktop Pet preferences and encrypted vault after closing the app.

Chromium caches are excluded. Conversation/task SQLite files are backed up by
maintenance.py, using SQLite's online backup API rather than filesystem copies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from maintenance import _private_directory


def backup(destination):
    profile = Path(os.environ['APPDATA']) / 'karen-desktop-pet'
    if not (profile / 'settings.json').is_file():
        raise ValueError('No existe el perfil de Desktop Pet.')
    destination = Path(destination).resolve()
    if destination == profile.resolve() or destination.is_relative_to(profile.resolve()):
        raise ValueError('El destino debe quedar fuera del perfil.')
    _private_directory(destination)
    manifest = {'format': 1, 'files': {}}
    for name in ('settings.json', 'vault.dpapi', 'window.json', 'initiative.json'):
        source = profile / name
        if not source.exists():
            continue
        if source.is_symlink() or not source.is_file():
            raise ValueError('El perfil contiene una ruta inesperada.')
        target = destination / name
        shutil.copy2(source, target)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError('El respaldo no coincide con el original.')
        manifest['files'][name] = {'sha256': digest, 'bytes': target.stat().st_size}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return len(manifest['files'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(f'Perfil respaldado y verificado: {backup(args.destination)} archivos. Credenciales sin descifrar.')
