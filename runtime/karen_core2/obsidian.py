"""Scoped Markdown operations and a rebuildable FTS5 index, with no Obsidian plugins.

Configuration is explicit. The index and backups must remain outside the vault.
This module never follows reparse points, imports instructions, or grants tools.
"""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import tempfile
import threading
import time
import uuid
from urllib.parse import urlencode

from core_resources import microphone_guard, ResourceBusy
from .knowledge import MAX_BYTES, extract
from .markdown_edits import frontmatter, properties_json, set_properties, tag_list, yaml_tags, set_task


class NoteConflict(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ObsidianManager:
    READ = {'list', 'search', 'read', 'backlinks', 'tasks', 'tags', 'properties', 'status'}
    WRITE = {'create', 'update', 'append', 'daily', 'link', 'move', 'rename', 'delete',
             'properties_set', 'tags_set', 'tasks_set'}
    SCHEMAS = {
        'list': ({}, {}),
        'status': ({}, {}),
        'search': ({'query': str}, {}),
        'read': ({'path': str}, {}),
        'backlinks': ({'path': str}, {}),
        'tasks': ({'path': str}, {}),
        'tags': ({'path': str}, {}),
        'properties': ({'path': str}, {}),
        'create': ({'path': str, 'content': str}, {}),
        'daily': ({'path': str, 'content': str}, {}),
        'update': ({'path': str, 'content': str, 'expected_hash': str}, {'section': str}),
        'append': ({'path': str, 'content': str, 'expected_hash': str}, {}),
        'link': ({'path': str, 'target': str, 'expected_hash': str}, {}),
        'reindex': ({}, {}),
        'move': ({'path': str, 'target': str, 'expected_hash': str}, {}),
        'rename': ({'path': str, 'name': str, 'expected_hash': str}, {}),
        'delete': ({'path': str, 'expected_hash': str}, {}),
        'open': ({'path': str, 'expected_hash': str}, {}),
        'properties_set': ({'path': str, 'values_json': str, 'expected_hash': str}, {}),
        'tags_set': ({'path': str, 'tags_json': str, 'expected_hash': str}, {}),
        'tasks_set': ({'path': str, 'line': int, 'done': bool, 'expected_hash': str}, {}),
    }

    def __init__(self, vault, scopes, database, *, events=None, poll_seconds=2, debounce=.25):
        selected = Path(vault).absolute()
        self._no_links(selected)
        if not selected.is_dir() or str(selected).startswith(('\\\\', '//')):
            raise ValueError('La bóveda debe ser una carpeta local existente.')
        self.vault = selected.resolve()
        if not scopes or isinstance(scopes, str):
            raise ValueError('Configura carpetas autorizadas de la bóveda.')
        self.scopes = tuple(self._relative(s) for s in scopes)
        for scope in self.scopes:
            path = self.vault.joinpath(*PurePosixPath(scope).parts)
            self._no_links(path)
            if not path.is_dir():
                raise ValueError('La carpeta autorizada no existe.')
        self.database = Path(database).absolute()
        self._no_links(self.database)
        if self.database.resolve().is_relative_to(self.vault):
            raise ValueError('Índice y copias deben quedar fuera de la bóveda.')
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.backups = self.database.with_suffix('.backups')
        self.backups.mkdir(exist_ok=True)
        self._no_links(self.backups)
        self.events = events
        self.poll_seconds = max(.05, float(poll_seconds))
        self.debounce = max(.02, float(debounce))
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        self.last_error = None
        self._vault_id = digest(str(self.vault).casefold().encode())
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS obsidian_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            version = db.execute("SELECT value FROM obsidian_meta WHERE key='version'").fetchone()
            if version and version[0] != '1':
                raise ValueError('Versión de índice Obsidian incompatible.')
            config = json.dumps([str(self.vault), self.scopes], ensure_ascii=False)
            old = db.execute("SELECT value FROM obsidian_meta WHERE key='config'").fetchone()
            if old and old[0] != config:
                raise ValueError('El índice pertenece a otra bóveda o permisos; selecciona otro archivo.')
            db.execute("INSERT OR IGNORE INTO obsidian_meta VALUES('version','1')")
            db.execute("INSERT OR IGNORE INTO obsidian_meta VALUES('config',?)", (config,))
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS obsidian_notes USING fts5(path UNINDEXED,hash UNINDEXED,body)')
            db.execute('CREATE TABLE IF NOT EXISTS obsidian_history(id TEXT PRIMARY KEY,path_hash TEXT,previous_hash TEXT,next_hash TEXT,at TEXT)')

    @staticmethod
    def _no_links(path):
        for part in (path, *path.parents):
            try:
                info = part.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('No se permiten symlinks, junctions ni otros reparse points.')

    @staticmethod
    def _relative(value):
        if (not isinstance(value, str) or not value or len(value) > 800 or '\\' in value
                or any(c in value for c in ':\x00<>"|?*') or value.startswith('/')):
            raise ValueError('Ruta relativa Markdown inválida; usa separadores /.')
        parts = value.split('/')
        if any(not p or p in {'.', '..'} or p.startswith('.') or p.endswith((' ', '.'))
               or re.match(r'(?i)^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)', p)
               or re.search(r'(?i)(credential|password|secrets?|tokens?|private)', p) for p in parts):
            raise ValueError('Ruta reservada, sensible o fuera del ámbito permitido.')
        return '/'.join(parts)

    def _path(self, name):
        name = self._relative(name)
        if not name.lower().endswith('.md') or not any(name.startswith(s + '/') for s in self.scopes):
            raise ValueError('Nota fuera de carpetas autorizadas o sin extensión Markdown.')
        path = self.vault.joinpath(*PurePosixPath(name).parts)
        self._no_links(path)
        if not path.resolve().is_relative_to(self.vault):
            raise ValueError('Ruta fuera de la bóveda.')
        if path.exists() and path.stat().st_nlink > 1:
            raise ValueError('No se permiten archivos con enlaces duros.')
        return path

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA journal_mode=WAL')
            with db:
                yield db

    def _read(self, name):
        path = self._path(name)
        with path.open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Nota supera 1 MiB.')
        extract(raw, '.md')  # Validate without normalizing the Markdown being edited.
        text = raw.decode('utf-8')
        return {'path': name, 'content': text, 'hash': digest(raw), 'trust': 'untrusted_data'}

    def _names(self):
        names = []
        for scope in self.scopes:
            root = self.vault.joinpath(*PurePosixPath(scope).parts)
            self._no_links(root)
            for folder, directories, files in os.walk(root, followlinks=False):
                safe = []
                for child in directories:
                    candidate = Path(folder) / child
                    try:
                        self._relative(candidate.relative_to(self.vault).as_posix())
                        self._no_links(candidate)
                        safe.append(child)
                    except ValueError:
                        continue
                directories[:] = safe
                for filename in files:
                    if not filename.lower().endswith('.md'):
                        continue
                    name = (Path(folder) / filename).relative_to(self.vault).as_posix()
                    try:
                        self._path(name)
                        names.append(name)
                    except ValueError:
                        continue
                    if len(names) > 10000:
                        raise ValueError('Ámbito supera 10000 notas; reduce carpetas autorizadas.')
        return sorted(set(names))

    def reindex(self, stop=None):
        with self._lock:
            names = self._names()
            changed, skipped = 0, 0
            with self._connect() as db:
                old = {row['path']: row['hash'] for row in db.execute('SELECT path,hash FROM obsidian_notes')}
                seen = set()
                for name in names:
                    if self._stop.is_set() or stop is not None and stop.is_set():
                        raise InterruptedError('Indexación cancelada.')
                    try:
                        note = self._read(name)
                    except (ValueError, OSError, UnicodeError):
                        skipped += 1
                        continue  # Drop stale snippets if a source becomes restricted or unreadable.
                    seen.add(name)
                    if old.get(name) == note['hash']:
                        continue
                    db.execute('DELETE FROM obsidian_notes WHERE path=?', (name,))
                    db.execute('INSERT INTO obsidian_notes VALUES(?,?,?)', (name, note['hash'], note['content']))
                    changed += 1
                for name in old.keys() - seen:
                    db.execute('DELETE FROM obsidian_notes WHERE path=?', (name,))
                    changed += 1
            if changed and self.events:
                self.events.emit('obsidian.index.updated', entity_id=self._vault_id)
            return {'indexed': len(seen), 'changed': changed, 'skipped': skipped}

    def _search(self, query):
        if not 1 <= len(query) <= 400:
            raise ValueError('Consulta debe tener entre 1 y 400 caracteres.')
        terms = re.findall(r'[^\W_]+', query, re.UNICODE)[:16]
        if not terms:
            return []
        expression = ' OR '.join('"' + term + '"' for term in terms)
        with self._connect() as db:
            rows = db.execute('SELECT path,hash,snippet(obsidian_notes,2,\'\',\'\',\' … \',40) AS snippet '
                              'FROM obsidian_notes WHERE obsidian_notes MATCH ? ORDER BY rank LIMIT 10', (expression,)).fetchall()
        result = []
        for row in rows:
            try:
                current = self._read(row['path'])
            except (ValueError, OSError, UnicodeError):
                continue
            if current['hash'] == row['hash']:
                result.append({**dict(row), 'trust': 'untrusted_data'})
        return result

    def _write(self, name, content, expected=None, *, create=False, stop=None):
        if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_BYTES:
            raise ValueError('Contenido inválido o mayor de 1 MiB.')
        extract(content.encode('utf-8'), '.md')  # Reject credentials before backups or index writes.
        path = self._path(name)
        if create and path.exists():
            raise NoteConflict('La nota ya existe; no se sobrescribe.')
        if not create and (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
            raise ValueError('La edición requiere expected_hash de la lectura revisada.')
        old = None if create else path.read_bytes()
        if old is not None and digest(old) != expected:
            raise NoteConflict('La nota cambió externamente; vuelve a leer antes de editar.')
        if stop is not None and stop.is_set():
            raise InterruptedError('Escritura cancelada.')
        self._no_links(self.backups)
        backup_id = uuid.uuid4().hex
        if old is not None:
            with (self.backups / (backup_id + '.md')).open('xb') as backup:
                backup.write(old)
                backup.flush()
                os.fsync(backup.fileno())
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path(name)
        raw = content.encode('utf-8')
        descriptor, temporary = tempfile.mkstemp(prefix='.karen-', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'wb') as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
            self._path(name)
            if stop is not None and stop.is_set():
                raise InterruptedError('Escritura cancelada.')
            if create:
                # Hard-link publication is atomic and fails if an external writer won creation.
                try:
                    os.link(temporary, path)
                except FileExistsError as exc:
                    raise NoteConflict('Otra aplicación creó la nota.') from exc
            else:
                if digest(path.read_bytes()) != expected:
                    raise NoteConflict('Cambio concurrente; no se reemplazó la nota.')
                os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        verified = self._read(name)
        if verified['hash'] != digest(raw):
            raise NoteConflict('El archivo cambió después de escribir; revisa el resultado.')
        with self._connect() as db:
            db.execute('INSERT INTO obsidian_history VALUES(?,?,?,?,?)',
                       (backup_id, digest(name.encode()), expected, verified['hash'], datetime.now(timezone.utc).isoformat()))
            db.execute('DELETE FROM obsidian_notes WHERE path=?', (name,))
            db.execute('INSERT INTO obsidian_notes VALUES(?,?,?)', (name, verified['hash'], verified['content']))
        if self.events:
            self.events.emit('obsidian.note.changed', entity_id=digest(name.encode()))
        return {'path': name, 'hash': verified['hash'], 'verified': True, 'backup_id': backup_id if old is not None else None}

    def validate(self, tool, args):
        """Side-effect-free validation, also used before persisting proposed plans."""
        if not isinstance(tool, str):
            raise ValueError('Herramienta Obsidian desconocida.')
        if tool.startswith('obsidian.'):
            tool = tool[9:]
        if tool not in self.SCHEMAS or not isinstance(args, dict):
            raise ValueError('Herramienta Obsidian desconocida.')
        required, optional = self.SCHEMAS[tool]
        if set(args) - (required.keys() | optional.keys()) or required.keys() - args.keys():
            raise ValueError('Parámetros Obsidian ausentes o desconocidos.')
        if any(type(value) is not (required | optional)[key] or isinstance(value, str) and '\0' in value for key, value in args.items()):
            raise ValueError('Tipos de parámetros Obsidian inválidos.')
        if 'path' in args:
            self._path(args['path'])
        if 'target' in args:
            self._path(args['target'])
        if 'content' in args:
            extract(args['content'].encode('utf-8'), '.md')
        if 'expected_hash' in args and not re.fullmatch('[0-9a-f]{64}', args['expected_hash']):
            raise ValueError('expected_hash inválido.')
        if tool == 'rename':
            if '/' in args['name']:
                raise ValueError('rename requiere solo un nombre; usa move para cambiar carpeta.')
            self._path(str(PurePosixPath(args['path']).parent / args['name']))
        if 'values_json' in args:
            properties_json(args['values_json'])
            extract(args['values_json'].encode('utf-8'), '.md')
        if 'tags_json' in args:
            tag_list(args['tags_json'])
            extract(args['tags_json'].encode('utf-8'), '.md')
        if 'line' in args and not 1 <= args['line'] <= 1000000:
            raise ValueError('Línea de tarea inválida.')
        return tool

    def permission(self, tool):
        if tool == 'delete':
            return 'destructive'
        if tool == 'open':
            return 'sensitive'
        return 'reversible' if tool in self.WRITE else 'read'

    def _delete(self, name, expected, stop=None):
        note = self._read(name)
        if note['hash'] != expected:
            raise NoteConflict('La nota cambió; vuelve a leer antes de eliminar o mover.')
        identity = uuid.uuid4().hex
        self._no_links(self.backups)
        with (self.backups / (identity + '.md')).open('xb') as backup:
            backup.write(note['content'].encode('utf-8'))
            backup.flush()
            os.fsync(backup.fileno())
        if stop is not None and stop.is_set():
            raise InterruptedError('Eliminación cancelada.')
        path = self._path(name)
        if digest(path.read_bytes()) != expected:
            raise NoteConflict('Cambio concurrente; no se eliminó la nota.')
        path.unlink()
        with self._connect() as db:
            db.execute('DELETE FROM obsidian_notes WHERE path=?', (name,))
            db.execute('INSERT INTO obsidian_history VALUES(?,?,?,?,?)',
                       (identity, digest(name.encode()), expected, None, datetime.now(timezone.utc).isoformat()))
        if self.events:
            self.events.emit('obsidian.note.changed', entity_id=digest(name.encode()), code='deleted')
        return {'path': name, 'verified': not path.exists(), 'backup_id': identity, 'deleted': True}

    def _move(self, name, target, expected, stop=None):
        if name.casefold() == target.casefold():
            raise ValueError('Origen y destino deben ser diferentes.')
        note = self._read(name)
        if note['hash'] != expected:
            raise NoteConflict('La nota cambió; vuelve a leer antes de mover.')
        self._path(target)
        # Publish without overwrite before removing the source. A failure may leave two
        # safe copies; Plans marks writes uncertain and never silently replays them.
        created = self._write(target, note['content'], create=True, stop=stop)
        removed = self._delete(name, expected, stop)
        return {**created, 'previous_path': name, 'backup_id': removed['backup_id'],
                'verified': removed['verified'] and self._read(target)['hash'] == expected,
                'backlinks_updated': False}

    def execute(self, tool, args, *, approve=None, stop=None):
        tool = self.validate(tool, args)
        if stop is not None and stop.is_set():
            raise InterruptedError('Operación cancelada.')
        permission = self.permission(tool)
        if permission != 'read' and (approve is None or approve({'tool': 'obsidian.' + tool, 'args': dict(args), 'permission': permission}) is not True):
            if self.events:
                self.events.emit('security.denied', code='obsidian_write')
            raise PermissionError('La escritura requiere aprobación de esta operación concreta.')
        with self._lock:
            if tool == 'status':
                with self._connect() as db:
                    count = db.execute('SELECT count(*) FROM obsidian_notes').fetchone()[0]
                return {'configured': True, 'indexed': count, 'watching': bool(self._thread and self._thread.is_alive()),
                        'last_error': self.last_error, 'scopes': list(self.scopes), 'schema': 1}
            if tool == 'reindex':
                return self.reindex(stop)
            if tool == 'list':
                names = self._names()
                return {'notes': names[:200], 'total': len(names), 'limit': 200}
            if tool == 'search':
                return self._search(args['query'])
            name = args['path']
            self._path(name)
            if tool == 'open':
                if self._read(name)['hash'] != args['expected_hash']:
                    raise NoteConflict('La nota cambió antes de abrirla; vuelve a leer.')
                if not hasattr(os, 'startfile'):
                    raise OSError('Apertura mediante URI disponible solo en Windows.')
                os.startfile('obsidian://open?' + urlencode({'path': str(self._path(name))}))
                return {'path': name, 'launch_requested': True, 'ui_verified': False}
            if tool == 'backlinks':
                stem = PurePosixPath(name).with_suffix('').as_posix()
                result = []
                for candidate in self._names():
                    try:
                        note = self._read(candidate)
                    except (ValueError, OSError, UnicodeError):
                        continue
                    links = re.findall(r'\[\[([^\]|#]+)', note['content'])
                    if stem in links or PurePosixPath(stem).name in links:
                        result.append(candidate)
                return {'notes': result[:200], 'limit': 200}
            if tool in {'create', 'daily'}:
                if tool == 'daily' and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', PurePosixPath(name).stem):
                    raise ValueError('La nota diaria requiere nombre YYYY-MM-DD.md.')
                operation = lambda: self._write(name, args['content'], create=True, stop=stop)
            else:
                note = self._read(name)
                if tool == 'read':
                    return note
                if tool == 'tasks':
                    return {'path': name, 'hash': note['hash'], 'tasks': [
                        {'line': i, 'done': mark.lower() == 'x', 'text': text}
                        for i, line in enumerate(note['content'].splitlines(), 1)
                        if (match := re.match(r'^\s*[-*+] \[([ xX])\] (.*)$', line))
                        for mark, text in [match.groups()]][:200]}
                if tool == 'tags':
                    return {'path': name, 'tags': sorted(set(yaml_tags(note['content']) +
                            re.findall(r'(?<![\w#])#([\w/-]+)', note['content'])))[:200]}
                if tool == 'properties':
                    return {'path': name, 'yaml': frontmatter(note['content'])[1], 'hash': note['hash'], 'trust': 'untrusted_data'}
                content = args.get('content', '')
                if tool == 'properties_set':
                    content = set_properties(note['content'], properties_json(args['values_json']))
                elif tool == 'tags_set':
                    content = set_properties(note['content'], {'tags': tag_list(args['tags_json'])})
                elif tool == 'tasks_set':
                    content = set_task(note['content'], args['line'], args['done'])
                elif tool == 'append':
                    content = note['content'] + '\n' + content
                elif tool == 'link':
                    target = args['target']
                    self._read(target)
                    if any(c in target for c in '[]#|'):
                        raise ValueError('Destino no representable como enlace interno.')
                    content = note['content'] + '\n[[' + target[:-3] + ']]\n'
                elif tool == 'update' and 'section' in args:
                    section = args['section']
                    lines = note['content'].splitlines(keepends=True)
                    matches = [i for i, line in enumerate(lines) if line.rstrip('\r\n') == section]
                    if len(matches) != 1 or not re.match(r'^#{1,6} .+', section):
                        raise ValueError('La sección debe identificar un encabezado único exacto.')
                    start = matches[0]
                    level = len(section.split(' ')[0])
                    end = next((i for i in range(start + 1, len(lines)) if re.match(r'^#{1,' + str(level) + r'} ', lines[i])), len(lines))
                    content = ''.join(lines[:start + 1]) + content.rstrip() + '\n\n' + ''.join(lines[end:])
                operation = lambda: self._write(name, content, args['expected_hash'], stop=stop)
                if tool == 'delete':
                    operation = lambda: self._delete(name, args['expected_hash'], stop)
                elif tool in {'move', 'rename'}:
                    target = args.get('target') or str(PurePosixPath(name).parent / args['name'])
                    operation = lambda: self._move(name, target, args['expected_hash'], stop)
            # Serialize cooperating Karen instances; hash checks detect ordinary external edits.
            try:
                with microphone_guard(self.database.with_suffix('.write.lock')):
                    return operation()
            except ResourceBusy as exc:
                raise NoteConflict('Otra instancia de Karen está escribiendo; reintenta después de leer.') from exc

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._watch, name='karen-obsidian', daemon=True)
            self._thread.start()

    def _watch(self):
        pending, previous = None, None
        while not self._stop.wait(self.poll_seconds):
            try:
                signature = tuple((name, self._path(name).stat().st_mtime_ns, self._path(name).stat().st_size) for name in self._names())
                if signature != previous:
                    previous, pending = signature, time.monotonic()
                if pending is not None and time.monotonic() - pending >= self.debounce:
                    self.reindex()
                    pending = None
                self.last_error = None
            except InterruptedError:
                return
            except (OSError, ValueError, sqlite3.Error):
                self.last_error = 'index_unavailable'

    def close(self):
        self._stop.set()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5)
