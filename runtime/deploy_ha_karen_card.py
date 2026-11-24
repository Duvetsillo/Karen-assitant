"""Deploy only Karen's static HA card, with remote backup and checksum verification.

By default this only deploys a static asset. --integration also installs the
native component. --connect explicitly provisions a conversation-only credential
and must only be used after the user's approval. Never restarts HA.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile
import uuid

SOURCE = Path(__file__).resolve().parent / 'integrations/home_assistant/karen-home-card.js'
DESTINATION = '/opt/stacks/homeassistant/config/www/karen-home-card.js'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deploy', action='store_true', required=True)
    parser.add_argument('--host', default='friday-datacenter')
    parser.add_argument('--integration', action='store_true')
    parser.add_argument('--connect', nargs='?', const='ssh-unix', metavar='HTTPS_KAREN_URL', help='Approved conversation channel; defaults to private SSH socket')
    args = parser.parse_args()
    def ssh(*command, check=True, input_text=None):
        return subprocess.run(['ssh', '-o', 'BatchMode=yes', args.host, shlex.join(command)],
                              check=check, capture_output=True, text=True, input=input_text, timeout=30)
    if args.integration:
        folder = SOURCE.parent / 'custom_components' / 'karen'
        remote_dir = '/opt/stacks/homeassistant/config/custom_components'
        package_stage = '/tmp/karen-component-' + uuid.uuid4().hex + '.tar'
        with tempfile.TemporaryDirectory(prefix='karen-component-') as directory:
            package = Path(directory) / 'karen.tar'
            with tarfile.open(package, 'w') as archive:
                for source in folder.rglob('*'):
                    if source.is_file() and source.suffix in {'.py', '.json'}:
                        info = archive.gettarinfo(str(source), 'karen/' + source.relative_to(folder).as_posix())
                        info.mode = 0o644
                        with source.open('rb') as stream:
                            archive.addfile(info, stream)
            subprocess.run(['scp', '-q', str(package), args.host + ':' + package_stage], check=True, timeout=30)
            try:
                ssh('pct', 'push', '101', package_stage, package_stage)
                ssh('pct', 'exec', '101', '--', 'mkdir', '-p', remote_dir)
                ssh('pct', 'exec', '101', '--', 'tar', '-xf', package_stage, '-C', remote_dir)
            finally:
                ssh('rm', '-f', package_stage, check=False)
                ssh('pct', 'exec', '101', '--', 'rm', '-f', package_stage, check=False)
        print('Native Karen component files installed; HA has not been restarted.')
    if args.connect:
        import json
        from urllib.parse import urlsplit
        from ha_conversation import provision, KEY_PATH
        if args.connect != 'ssh-unix':
            parsed = urlsplit(args.connect)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
                raise ValueError('Use the private HTTPS endpoint without credentials or path.')
        secret_path = '/opt/stacks/homeassistant/config/.storage/karen-connection.json'
        if ssh('pct', 'exec', '101', '--', 'test', '-e', secret_path, check=False).returncode == 0:
            raise ValueError('The HA connection already exists; no credential was replaced.')
        key = provision()
        writer = "import os,sys; p='/config/.storage/karen-connection.json'; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,'w'); f.write(sys.stdin.read()); f.close()"
        try:
            ssh('pct', 'exec', '101', '--', 'docker', 'exec', '-i', 'homeassistant', 'python', '-c', writer,
                input_text=json.dumps({'url': 'http://127.0.0.1:18793' if args.connect == 'ssh-unix' else args.connect.rstrip('/'),
                                       'transport': args.connect, 'key': key}))
        except Exception:
            KEY_PATH.unlink(missing_ok=True)  # Revoke only the just-created, unusable grant.
            raise
        print('Conversation-only private channel provisioned; no secret was printed.')
    stage = '/tmp/karen-home-card-' + uuid.uuid4().hex + '.js'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    subprocess.run(['scp', '-q', str(SOURCE), args.host + ':' + stage], check=True, timeout=30)
    try:
        if ssh('pct', 'exec', '101', '--', 'test', '-e', DESTINATION, check=False).returncode == 0:
            ssh('pct', 'exec', '101', '--', 'cp', '-a', DESTINATION, DESTINATION + '.before-' + stamp)
        pending = DESTINATION + '.pending-' + stamp
        ssh('pct', 'push', '101', stage, pending)
        remote = ssh('pct', 'exec', '101', '--', 'sha256sum', pending).stdout.split()[0]
        if remote != digest:
            raise ValueError('Remote checksum mismatch; current asset was not replaced.')
        ssh('pct', 'exec', '101', '--', 'mv', pending, DESTINATION)
        print('Static HA card deployed and verified:', digest)
    finally:
        # Exact unique temporary file created by this command; no recursive operation.
        ssh('rm', '-f', stage, check=False)
    pet = SOURCE.with_name('karen-pet.png')
    if pet.exists():
        stage = '/tmp/karen-pet-' + uuid.uuid4().hex + '.png'
        subprocess.run(['scp', '-q', str(pet), args.host + ':' + stage], check=True, timeout=30)
        try:
            ssh('pct', 'push', '101', stage, '/opt/stacks/homeassistant/config/www/karen-pet.png')
            remote = ssh('pct', 'exec', '101', '--', 'sha256sum', '/opt/stacks/homeassistant/config/www/karen-pet.png').stdout.split()[0]
            if remote != hashlib.sha256(pet.read_bytes()).hexdigest():
                raise ValueError('Pet checksum mismatch.')
        finally:
            ssh('rm', '-f', stage, check=False)


if __name__ == '__main__':
    main()
