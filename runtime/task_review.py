"""Explicit local audit of uncertain tasks. Never executes task tools."""

import argparse
import json
from pathlib import Path
import sqlite3

from karen_tasks import TaskEngine


def main(argv=None, confirm=input):
    parser = argparse.ArgumentParser(description='Revisión manual de tareas con resultado incierto.')
    parser.add_argument('--db', type=Path, help='SQLite local; por defecto KAREN_TASKS_DB o .private/karen-tasks.sqlite3')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list', help='Mostrar tareas pendientes de revisión')
    review = commands.add_parser('review', help='Registrar un resultado comprobado fuera de Karen')
    review.add_argument('id')
    review.add_argument('outcome', choices=['applied', 'not_applied'])
    args = parser.parse_args(argv)
    try:
        engine = TaskEngine({}, args.db)
        if args.command == 'list':
            result = engine.uncertain_jobs()
        else:
            state = engine.inspect(args.id)
            if state['status'] != 'uncertain':
                raise ValueError('Solo se revisan tareas con estado uncertain.')
            print('Comprueba el efecto real fuera de Karen antes de registrar el resultado.')
            if confirm(f'Escribe el ID {args.id} para confirmar: ').strip() != args.id:
                raise ValueError('Revisión cancelada; ID no coincide.')
            result = engine.review_uncertain(args.id, args.outcome)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, sqlite3.Error, ValueError, KeyError, RuntimeError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
