"""Explicit local memory management for Karen Core v1."""
import argparse
import json
import os
import sys

from karen_memory import MemoryStore
from karen_core2.memory import KINDS


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', help='Ruta absoluta a la base SQLite compartida.')
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('project')
    add.add_argument('content', help='Texto del recuerdo; usa - para leer de stdin.')
    add.add_argument('--inferred', action='store_true')
    add.add_argument('--sensitive', action='store_true')
    add.add_argument('--retention-days', type=int)
    add.add_argument('--kind', choices=sorted(KINDS))
    add.add_argument('--state', choices=('VERIFICADO', 'INFERIDO', 'PENDIENTE', 'DESACTUALIZADO'))
    add.add_argument('--fact-key')
    add.add_argument('--tag', action='append', default=[])
    add.add_argument('--supersedes')
    listing = commands.add_parser('list')
    listing.add_argument('project')
    listing.add_argument('--query', default='')
    listing.add_argument('--limit', type=int, default=100)
    edit = commands.add_parser('edit')
    edit.add_argument('id')
    edit.add_argument('content', help='Usa - para leer de stdin.')
    certainty = edit.add_mutually_exclusive_group()
    certainty.add_argument('--confirmed', action='store_true')
    certainty.add_argument('--inferred', action='store_true')
    delete = commands.add_parser('delete')
    delete.add_argument('id')
    export = commands.add_parser('export')
    export.add_argument('project')
    export.add_argument('path', help='Archivo nuevo; no sobrescribe uno existente.')
    bundle = commands.add_parser('export-engine')
    bundle.add_argument('project')
    bundle.add_argument('path', help='Archivo nuevo; incluye versiones públicas y relaciones.')
    commands.add_parser('reindex', help='Reconstruye FTS5 sin modificar recuerdos.')
    incoming = commands.add_parser('import-engine', help='Revisa un paquete; aplicar requiere --apply y la huella revisada.')
    incoming.add_argument('project')
    incoming.add_argument('path')
    incoming.add_argument('--apply', action='store_true')
    incoming.add_argument('--expected-hash')
    imported = commands.add_parser('inspect-import', help='Muestra recuerdo y procedencia reportada para revisión explícita.')
    imported.add_argument('id')
    review = commands.add_parser('review-import', help='Promueve un recuerdo concreto tras revisión explícita.')
    review.add_argument('id')
    review.add_argument('--expected-hash', required=True)
    for name, argument in (('history', 'id'), ('procedure', 'id'), ('graph', 'project'), ('consolidate', 'project'), ('search', 'project'), ('timeline', 'project')):
        command = commands.add_parser(name)
        command.add_argument(argument)
        if name == 'search':
            command.add_argument('query', nargs='?', default='')
        if name == 'timeline':
            command.add_argument('--since')
            command.add_argument('--until')
            command.add_argument('--kind')
    for command in (add, listing, edit, delete, export):
        command.add_argument('--allow-sensitive', action='store_true')
    args = parser.parse_args(argv)
    store = MemoryStore(args.db)
    if args.command in {'import-engine', 'inspect-import', 'review-import'}:
        from karen_core2.memory import ContextMemory
        from karen_core2.memory_portability import load_bundle
        port = ContextMemory(store.path).portability
        if args.command == 'inspect-import':
            result = port.inspect(args.id)
        elif args.command == 'review-import':
            result = port.review(args.id, args.expected_hash)
        else:
            bundle = load_bundle(args.path)
            result = port.apply(bundle, args.project, args.expected_hash) if args.apply else port.preview(bundle, args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command in {'history', 'procedure', 'graph', 'consolidate', 'search', 'timeline', 'export-engine', 'reindex'}:
        from karen_core2.memory import ContextMemory
        engine = ContextMemory(store.path)
        if args.command == 'reindex': result = engine.reindex()
        elif args.command == 'search': result = engine.retrieve(args.project, args.query)
        elif args.command == 'timeline': result = engine.timeline(args.project, since=args.since, until=args.until, kind=args.kind)
        elif args.command == 'export-engine':
            result = engine.export_bundle(args.project)
            with os.fdopen(os.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as target:
                json.dump(result, target, ensure_ascii=False, indent=2)
            result = {'exported': args.path, 'count': len(result['memories'])}
        else: result = getattr(engine, args.command)(getattr(args, 'id', None) or args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == 'add':
        content = sys.stdin.read() if args.content == '-' else args.content
        if args.kind or args.state or args.fact_key or args.tag or args.supersedes:
            from karen_core2.memory import ContextMemory
            if args.sensitive or args.allow_sensitive:
                raise ValueError('Memoria contextual no admite datos sensibles.')
            result = ContextMemory(store.path).add(args.project, content, kind=args.kind or 'semantic',
                status='hypothesis' if args.inferred else 'confirmed', state=args.state,
                temporary_days=args.retention_days, fact_key=args.fact_key, tags=args.tag, supersedes=args.supersedes)
        else:
            result = store.add(args.project, content, confirmed=not args.inferred,
                               sensitive=args.sensitive, allow_sensitive=args.allow_sensitive,
                               retention_days=args.retention_days)
    elif args.command == 'list':
        result = store.list(args.project, args.query, include_sensitive=args.allow_sensitive,
                            limit=args.limit)
    elif args.command == 'edit':
        content = sys.stdin.read() if args.content == '-' else args.content
        confirmed = True if args.confirmed else False if args.inferred else None
        result = store.edit(args.id, content, confirmed=confirmed,
                            allow_sensitive=args.allow_sensitive)
    elif args.command == 'delete':
        result = {'deleted': store.delete(args.id, allow_sensitive=args.allow_sensitive)}
    else:
        data = store.export_json(args.project, include_sensitive=args.allow_sensitive)
        with os.fdopen(os.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                       'w', encoding='utf-8') as target:
            target.write(data)
        result = {'exported': args.path, 'count': len(json.loads(data)['memories'])}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
