"""Apply the reviewed HA layout offline, with backups and an unconditional restart.

Only dashboard storage, its resource URL and Karen's own theme are changed.
Requires the existing authorized SSH alias; never reads authentication files.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import uuid

from ha_dashboard import redesign


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    parser.add_argument('--host', default='friday-datacenter')
    args = parser.parse_args()
    base = '/opt/stacks/homeassistant/config/'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = Path('.private') / ('ha-minimal-' + stamp)
    folder.mkdir(parents=True)

    def ssh(*command):
        return subprocess.run(['ssh', '-o', 'BatchMode=yes', args.host, shlex.join(command)],
                              check=True, capture_output=True, timeout=60)

    def ct(*command):
        return ssh('pct', 'exec', '101', '--', *command)

    staged = []
    for name in ('lovelace.dashboard_casa', 'lovelace_resources'):
        target = base + '.storage/' + name
        before = ct('cat', target).stdout
        (folder / (name + '.before.json')).write_bytes(before)
        data = json.loads(before)
        if name == 'lovelace.dashboard_casa':
            data['data']['config'] = redesign(data['data']['config'])
        else:
            for resource in data['data']['items']:
                if resource['url'].startswith('/local/karen-home-card.js'):
                    resource['url'] = '/local/karen-home-card.js?v=minimal-' + stamp
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode()
        local = folder / (name + '.after.json')
        local.write_bytes(payload)
        stage = '/tmp/karen-minimal-' + uuid.uuid4().hex
        subprocess.run(['scp', '-q', str(local), args.host + ':' + stage], check=True, timeout=30)
        ssh('pct', 'push', '101', stage, stage)
        staged.append((target, stage, hashlib.sha256(before).hexdigest(), hashlib.sha256(payload).hexdigest()))
    theme = Path('integrations/home_assistant/karen-calm.yaml')
    stage_theme = '/tmp/karen-theme-' + uuid.uuid4().hex
    subprocess.run(['scp', '-q', str(theme), args.host + ':' + stage_theme], check=True, timeout=30)
    ssh('pct', 'push', '101', stage_theme, stage_theme)
    ct('docker', 'stop', '--time', '30', 'homeassistant')
    try:
        # Validate every current file before applying either change.
        for target, stage, expected, digest in staged:
            if ct('sha256sum', target).stdout.decode().split()[0] != expected:
                raise RuntimeError('HA configuration changed during staging; nothing was applied.')
        for target, stage, expected, digest in staged:
            ct('cp', '-p', target, target + '.before-' + stamp)
            ct('cp', stage, target + '.pending')
            ct('chmod', '--reference=' + target, target + '.pending')
            ct('chown', '--reference=' + target, target + '.pending')
            ct('mv', target + '.pending', target)
            if ct('sha256sum', target).stdout.decode().split()[0] != digest:
                raise RuntimeError('Published configuration checksum mismatch.')
        ct('cp', stage_theme, base + 'themes/karen-calm.yaml')
    finally:
        ct('docker', 'start', 'homeassistant')
        for stage in [s[1] for s in staged] + [stage_theme]:
            ct('rm', '-f', stage)
            ssh('rm', '-f', stage)
    print('Dashboard, resources and theme applied; HA restarted. Backups:', folder)


if __name__ == '__main__':
    main()
