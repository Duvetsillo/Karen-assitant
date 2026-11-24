"""Explicit local chat management. Never contacts a model or remote service."""

import argparse
import sqlite3
from pathlib import Path

from conversations import Conversations


def main():
    parser = argparse.ArgumentParser(description='Gestiona el archivo local de chats de Karen')
    parser.add_argument('--db', type=Path, help='SQLite; predeterminado: KAREN_CORE_DB o archivo clásico')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    search = sub.add_parser('search')
    search.add_argument('query')
    rename = sub.add_parser('rename')
    rename.add_argument('id')
    rename.add_argument('title')
    export = sub.add_parser('export')
    export.add_argument('id')
    export.add_argument('output', type=Path)
    delete = sub.add_parser('delete')
    delete.add_argument('id')
    delete.add_argument('--confirm', required=True, help='Repite el ID exacto; borra turnos y metadatos del chat')
    args = parser.parse_args()
    if args.command == 'delete' and args.confirm != args.id:
        parser.error('Confirmación diferente del ID; no se borró nada.')
    try:
        archive = Conversations(args.db)
        if args.command in {'list', 'search'}:
            for chat_id, title, updated in (archive.list() if args.command == 'list' else archive.search(args.query)):
                print(f'{chat_id}  {updated}  {title}')
        elif args.command == 'rename':
            archive.rename(args.id, args.title)
            print('Conversación renombrada.')
        elif args.command == 'export':
            content = archive.export_json(args.id)
            with args.output.open('x', encoding='utf-8') as output:
                output.write(content)
            print('Conversación exportada. El archivo contiene texto privado; guárdalo localmente.')
        else:
            print('Conversación borrada.' if archive.delete(args.id) else 'Conversación inexistente.')
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
