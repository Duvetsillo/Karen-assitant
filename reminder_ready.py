"""Wait for the WhatsApp listener before releasing scheduled reminder text."""
import argparse
import json
import subprocess
import sys
import time

CLI = [r'C:\Program Files\nodejs\node.exe',
       r'C:\Users\Dayve\AppData\Roaming\npm\node_modules\openclaw\dist\index.js']


def ready(status, account):
    return any(item.get('accountId') == account and item.get('connected')
               and item.get('running')
               for item in status.get('channelAccounts', {}).get('whatsapp', []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--message', required=True)
    parser.add_argument('--account', default='default')
    # The scheduled command's 300s budget expires before this deadline. This
    # records a transient timeout and enables native one-shot retry behavior.
    parser.add_argument('--wait-seconds', type=int, default=600)
    args = parser.parse_args()
    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(CLI + ['channels', 'status', '--json'],
                                    capture_output=True, encoding='utf-8', timeout=35,
                                    creationflags=0x08000000)
            if result.returncode == 0 and ready(json.loads(result.stdout), args.account):
                sys.stdout.reconfigure(encoding='utf-8')
                print(args.message, flush=True)
                return
        except (ValueError, subprocess.TimeoutExpired):
            pass
        time.sleep(5)
    # Timeout is an execution failure, rather than successful undelivered text.
    print('Network timeout: WhatsApp no se conectó; recordatorio pendiente.', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main()
