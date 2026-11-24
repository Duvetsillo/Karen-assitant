"""Opt-in, local disk alerts; run separately from the Karen windows."""

import argparse
import json
import math
from pathlib import Path
import sys
import threading

from karen_alerts import AlertEngine
from karen_task_tools import cpu_sample, disk_sample, memory_sample


def check_disk(engine, probe=disk_sample):
    reading = probe({}, threading.Event())
    total, free = reading['disk_total_bytes'], reading['disk_free_bytes']
    if type(total) is not int or type(free) is not int or total <= 0 or not 0 <= free <= total:
        raise ValueError('Lectura de disco inválida.')
    percent = 100 * free / total
    alerts = engine.observe('pc', 'disk_free_percent', percent)
    return {'drive': reading['drive'], 'disk_free_percent': round(percent, 2), 'alerts': alerts}


def check_cpu(engine, probe=cpu_sample):
    reading = probe({}, threading.Event())
    percent = reading['cpu_percent']
    if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError('Lectura de CPU inválida.')
    return {'cpu_percent': round(percent, 2),
            'alerts': engine.observe('pc', 'cpu_percent', percent)}


def check_memory(engine, probe=memory_sample):
    reading = probe({}, threading.Event())
    total, available = reading['ram_total_bytes'], reading['ram_available_bytes']
    if type(total) is not int or type(available) is not int or total <= 0 or not 0 <= available <= total:
        raise ValueError('Lectura de RAM inválida.')
    percent = 100 * available / total
    return {'ram_available_percent': round(percent, 2),
            'alerts': engine.observe('pc', 'ram_available_percent', percent)}


def check_pc(engine):
    """Keep valid observations when an unrelated probe fails."""
    result = {'measurements': {}, 'alerts': [], 'errors': {}}
    for name, check in (('disk', check_disk), ('cpu', check_cpu), ('memory', check_memory)):
        try:
            reading = check(engine)
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            result['errors'][name] = str(exc)
            continue
        result['alerts'].extend(reading.pop('alerts'))
        result['measurements'][name] = reading
    return result


def watch_disk(engine, interval, stop, emit, probe=disk_sample):
    if not 10 <= interval <= 3600:
        raise ValueError('Intervalo inválido (10 a 3600 segundos).')
    while not stop.is_set():
        try:
            for alert in check_disk(engine, probe)['alerts']:
                emit(alert)
        except (OSError, ValueError) as exc:
            print(f'Lectura de disco fallida: {exc}', file=sys.stderr)
        stop.wait(interval)


def watch_pc(engine, interval, stop, emit, trends=None):
    if not 10 <= interval <= 3600:
        raise ValueError('Intervalo inválido (10 a 3600 segundos).')
    while not stop.is_set():
        reading = check_pc(engine)
        if trends is not None:
            try:
                trends.sample(stop)
            except (OSError, ValueError, RuntimeError, InterruptedError):
                pass
        for alert in reading['alerts']:
            emit(alert)
        for source, error in reading['errors'].items():
            print(f'Lectura de {source} fallida: {error}', file=sys.stderr)
        stop.wait(interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Alertas locales de disco, independientes de la ventana Karen.')
    parser.add_argument('--db', type=Path, help='SQLite local; por defecto .private/karen-alerts.sqlite3')
    commands = parser.add_subparsers(dest='command', required=True)
    rule = commands.add_parser('add-disk-rule')
    rule.add_argument('operator', choices=['<', '<='])
    rule.add_argument('threshold', type=float, help='Porcentaje libre; 0 a 100')
    rule.add_argument('--priority', choices=['low', 'normal', 'high', 'critical'], default='high')
    rule.add_argument('--cooldown', type=int, default=300, help='Segundos entre episodios, 0 a 86400')
    cpu_rule = commands.add_parser('add-cpu-rule')
    cpu_rule.add_argument('operator', choices=['>', '>='])
    cpu_rule.add_argument('threshold', type=float, help='Uso de CPU; 0 a 100 %%')
    cpu_rule.add_argument('--priority', choices=['low', 'normal', 'high', 'critical'], default='normal')
    cpu_rule.add_argument('--cooldown', type=int, default=300)
    ram_rule = commands.add_parser('add-memory-rule')
    ram_rule.add_argument('operator', choices=['<', '<='])
    ram_rule.add_argument('threshold', type=float, help='RAM disponible; 0 a 100 %%')
    ram_rule.add_argument('--priority', choices=['low', 'normal', 'high', 'critical'], default='high')
    ram_rule.add_argument('--cooldown', type=int, default=300)
    commands.add_parser('check')
    commands.add_parser('check-pc')
    watcher = commands.add_parser('watch')
    watcher.add_argument('--interval', type=int, default=60, help='Segundos; 10 a 3600')
    pc_watcher = commands.add_parser('watch-pc')
    pc_watcher.add_argument('--interval', type=int, default=60, help='Segundos; 10 a 3600')
    pc_watcher.add_argument('--trends', action='store_true', help='Añade tendencias Core 2 en la base de tareas existente')
    history = commands.add_parser('history')
    history.add_argument('--status', choices=['active', 'acknowledged', 'resolved'])
    commands.add_parser('rules')
    rule_state = commands.add_parser('rule', help='Activar o desactivar una regla por ID')
    rule_state.add_argument('id')
    rule_state.add_argument('state', choices=['on', 'off'])
    source_state = commands.add_parser('source', help='Activar o desactivar una fuente')
    source_state.add_argument('name')
    source_state.add_argument('state', choices=['on', 'off'])
    ack = commands.add_parser('ack')
    ack.add_argument('id')
    quiet = commands.add_parser('quiet')
    quiet.add_argument('start', nargs='?', help='HH:MM local; omite ambos para desactivar')
    quiet.add_argument('end', nargs='?')
    gaming = commands.add_parser('gaming')
    gaming.add_argument('state', choices=['on', 'off'])
    args = parser.parse_args(argv)
    try:
        engine = AlertEngine(args.db)
        if args.command in {'add-disk-rule', 'add-cpu-rule', 'add-memory-rule'}:
            if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 100:
                raise ValueError('El porcentaje debe estar entre 0 y 100.')
            metric, label = {
                'add-disk-rule': ('disk_free_percent', 'Disco libre'),
                'add-cpu-rule': ('cpu_percent', 'Uso de CPU'),
                'add-memory-rule': ('ram_available_percent', 'RAM disponible'),
            }[args.command]
            result = {'rule_id': engine.add_rule('pc', metric, args.operator,
                                                args.threshold, priority=args.priority,
                                                cooldown_seconds=args.cooldown,
                                                label=f'{label} {args.operator} {args.threshold:g}%')}
        elif args.command == 'check':
            result = check_disk(engine)
        elif args.command == 'check-pc':
            result = check_pc(engine)
        elif args.command in {'watch', 'watch-pc'}:
            print(f'Monitor local iniciado; intervalo {args.interval} s. Detén con Ctrl+C.', flush=True)
            try:
                watcher_fn = watch_pc if args.command == 'watch-pc' else watch_disk
                options = {}
                if args.command == 'watch-pc' and args.trends:
                    from karen_core2.runtime import CoreRuntime
                    options['trends'] = CoreRuntime().diagnostics
                watcher_fn(engine, args.interval, threading.Event(),
                           lambda alert: print(json.dumps(alert, ensure_ascii=False), flush=True), **options)
            except KeyboardInterrupt:
                pass
            return 0
        elif args.command == 'history':
            result = engine.history(status=args.status)
        elif args.command == 'rules':
            result = engine.rules()
        elif args.command == 'rule':
            engine.set_rule_enabled(args.id, args.state == 'on')
            result = {'rule_id': args.id, 'enabled': args.state == 'on'}
        elif args.command == 'source':
            engine.set_source_enabled(args.name, args.state == 'on')
            result = {'source': args.name, 'enabled': args.state == 'on'}
        elif args.command == 'ack':
            result = {'acknowledged': engine.acknowledge(args.id)}
        elif args.command == 'quiet':
            engine.set_quiet_hours(args.start, args.end)
            result = {'quiet_hours': [args.start, args.end]}
        else:
            engine.set_gaming(args.state == 'on')
            result = {'gaming': args.state}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
