"""Create reliable one-shot reminders through OpenClaw's native scheduler."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import subprocess
import sys

from reminder_ready import CLI


def gateway(method, params):
    result = subprocess.run(CLI + ['gateway', 'call', method, '--params',
                                  json.dumps(params), '--json', '--timeout', '30000'],
                            capture_output=True, encoding='utf-8', timeout=40,
                            creationflags=0x08000000)
    if result.returncode:
        raise RuntimeError('No se pudo confirmar el recordatorio: ' + (result.stdout or result.stderr)[:1000])
    return json.loads(result.stdout)


def resolve_time(at=None, minutes=None, now=None):
    now = now or datetime.now(timezone.utc)
    if minutes is not None:
        if type(minutes) is not int or not 1 <= minutes <= 525600:
            raise ValueError('El plazo debe ser de 1 a 525600 minutos.')
        return now + timedelta(minutes=minutes)
    try:
        result = datetime.fromisoformat((at or '').replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Usa una fecha ISO-8601 con zona horaria o --in-minutes.') from exc
    if result.tzinfo is None or result <= now:
        raise ValueError('La fecha debe ser futura e incluir zona horaria.')
    return result


def create_reminder(at, message, dry_run=False):
    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        raise ValueError('El mensaje debe contener entre 1 y 4000 caracteres.')
    timestamp = at.astimezone(timezone.utc).isoformat()
    identity = hashlib.sha256((timestamp + '\n' + message).encode()).hexdigest()[:20]
    name = 'Recordatorio FRIDAY ' + identity
    if dry_run:
        return {'dry_run': True, 'scheduled': False, 'at': timestamp, 'message': message}
    existing = gateway('cron.list', {'includeDisabled': True}).get('jobs', [])
    matching = next((job for job in existing if job['name'] == name), None)
    if matching:
        return {'id': matching['id'], 'enabled': matching['enabled'],
                'schedule': matching['schedule'], 'existing': True}
    job = {
        'name': name, 'displayName': message[:80],
        'schedule': {'kind': 'at', 'at': timestamp}, 'sessionTarget': 'isolated',
        'payload': {'kind': 'command', 'argv': [sys.executable,
            'C:/karen/reminder_ready.py', '--message', message], 'timeoutSeconds': 300},
        'delivery': {'mode': 'announce', 'channel': 'whatsapp',
                     'accountId': 'default', 'to': '+18497511821'},
        'deleteAfterRun': True,
    }
    result = gateway('cron.add', job)
    if not isinstance(result, dict) or not result.get('id') or result.get('enabled') is not True:
        raise RuntimeError('El planificador no confirmó un ID habilitado. Consulta su estado antes de repetir.')
    return result


def main():
    parser = argparse.ArgumentParser()
    when = parser.add_mutually_exclusive_group()
    when.add_argument('--at', help='ISO-8601 with explicit timezone')
    when.add_argument('--in-minutes', type=int, help='Minutos a partir de ahora; no necesita calcular la hora')
    parser.add_argument('--message')
    parser.add_argument('--dry-run', action='store_true', help='Muestra la fecha sin programar ni enviar')
    parser.add_argument('--check', action='store_true', help='Consulta el programador; no crea ni envía nada')
    args = parser.parse_args()
    if args.check:
        status = gateway('cron.status', {})
        print(json.dumps({'scheduler_enabled': status.get('enabled') is True,
                          'now': datetime.now(timezone.utc).isoformat()}, ensure_ascii=True))
        return
    if args.at is None and args.in_minutes is None:
        parser.error('Indica --at o --in-minutes.')
    try:
        at = resolve_time(args.at, args.in_minutes)
        print(json.dumps(create_reminder(at, args.message, args.dry_run), ensure_ascii=True))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
