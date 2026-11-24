"""Explicit local document import and review. Imported text cannot call tools."""
import argparse
import json
from pathlib import Path

from karen_core2.knowledge import KnowledgeStore
from karen_core2.memory import ContextMemory


def main():
    parser = argparse.ArgumentParser(description='Conocimiento local: importa, revisa y aprueba antes de recuperar.')
    parser.add_argument('--database', type=Path)
    parser.add_argument('--project', default='Karen')
    sub = parser.add_subparsers(dest='action', required=True)
    command = sub.add_parser('import')
    command.add_argument('file', type=Path)
    command.add_argument('--sensitive', action='store_true')
    command.add_argument('--allow-sensitive', action='store_true')
    sub.add_parser('list')
    for action in ('review', 'approve', 'delete'):
        command = sub.add_parser(action)
        command.add_argument('id')
        command.add_argument('--allow-sensitive', action='store_true')
    command = sub.add_parser('search')
    command.add_argument('query')
    args = parser.parse_args()
    store = KnowledgeStore(ContextMemory(args.database))
    if args.action == 'import':
        result = store.import_file(args.project, args.file.absolute(), sensitive=args.sensitive, allow_sensitive=args.allow_sensitive)
    elif args.action == 'list':
        result = store.list(args.project)
    elif args.action == 'search':
        result = store.search(args.project, args.query)
    elif args.action == 'delete':
        result = store.delete(args.id, allow_sensitive=args.allow_sensitive)
    else:
        result = store.review(args.id, approve=args.action == 'approve', allow_sensitive=args.allow_sensitive)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
