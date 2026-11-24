"""Reviewed, bounded local document search in the existing Core SQLite file."""
from datetime import datetime, timezone
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import uuid

from .memory import words
from .privacy import ASSIGNMENT, SECRET

MAX_BYTES = 1024 * 1024
MAX_CHUNKS = 256
TEXT_TYPES = {'.txt', '.md', '.json', '.csv', '.html', '.htm'}


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript'}:
            self.hidden += 1
        elif tag in {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3'} and not self.hidden:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript'}:
            self.hidden = max(0, self.hidden - 1)
        elif tag in {'p', 'div', 'li', 'h1', 'h2', 'h3'} and not self.hidden:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def extract(raw, suffix):
    text = raw.decode('utf-8-sig')
    if suffix == '.json':
        text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    elif suffix == '.csv':
        text = '\n'.join(' | '.join(row) for row in csv.reader(io.StringIO(text)))
    elif suffix in {'.html', '.htm'}:
        parser = PlainHTML()
        parser.feed(text)
        parser.close()
        text = ''.join(parser.parts)
    text = text.replace('\x00', '').strip()
    if not text or len(text) > MAX_BYTES:
        raise ValueError('Documento vacío o demasiado extenso después de extraerlo.')
    if ASSIGNMENT.search(text) or SECRET.search(text) or 'PRIVATE KEY' in text:
        raise ValueError('No se importan documentos que contengan posibles credenciales.')
    return text


def chunks(text, limit=1200):
    parts, current = [], ''
    for paragraph in re.split(r'\n\s*\n', text):
        for start in range(0, len(paragraph), limit):
            piece = paragraph[start:start + limit]
            if len(current) + len(piece) + 2 > limit:
                if current:
                    parts.append(current)
                current = ''
            current = (current + '\n\n' + piece).strip()
    if current:
        parts.append(current)
    if len(parts) > MAX_CHUNKS:
        raise ValueError('Documento excede el límite de fragmentos; importa secciones más pequeñas.')
    return parts


class KnowledgeStore:
    def __init__(self, memory):
        self.base = memory.base
        with self.base.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS core2_documents (
                  id TEXT PRIMARY KEY, project TEXT NOT NULL, source_name TEXT NOT NULL,
                  source_key TEXT NOT NULL, digest TEXT NOT NULL, created_at TEXT NOT NULL,
                  approved INTEGER NOT NULL DEFAULT 0, sensitive INTEGER NOT NULL DEFAULT 0,
                  active INTEGER NOT NULL DEFAULT 0, UNIQUE(project,digest));
                CREATE TABLE IF NOT EXISTS core2_document_chunks (
                  id INTEGER PRIMARY KEY, document_id TEXT NOT NULL, position INTEGER NOT NULL,
                  body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS core2_document_chunks_source ON core2_document_chunks(document_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS core2_document_search USING fts5(
                  body, content=core2_document_chunks, content_rowid=id, tokenize='unicode61 remove_diacritics 2');
                CREATE TRIGGER IF NOT EXISTS core2_document_insert AFTER INSERT ON core2_document_chunks BEGIN
                  INSERT INTO core2_document_search(rowid,body) VALUES(NEW.id,NEW.body);
                END;
                CREATE TRIGGER IF NOT EXISTS core2_document_remove AFTER DELETE ON core2_document_chunks BEGIN
                  INSERT INTO core2_document_search(core2_document_search,rowid,body) VALUES('delete',OLD.id,OLD.body);
                END;
            ''')

    def import_file(self, project, filename, *, sensitive=False, allow_sensitive=False):
        project = self.base._project(project)
        path = Path(filename)
        resolved = path.resolve()
        # Only an explicitly selected local file. No network shares, archives or directory walks.
        if (not path.is_absolute() or str(resolved).startswith(('\\\\', '//')) or path.is_symlink()
                or not path.is_file() or path.suffix.lower() not in TEXT_TYPES):
            raise ValueError('Selecciona un archivo local absoluto de texto, Markdown, JSON, CSV o HTML.')
        if type(sensitive) is not bool or type(allow_sensitive) is not bool or sensitive and not allow_sensitive:
            raise ValueError('Información sensible requiere autorización explícita para almacenarse.')
        with path.open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Archivo supera 1 MiB.')
        content = extract(raw, path.suffix.lower())
        pieces = chunks(content)
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        source_key = hashlib.sha256(str(path.resolve()).casefold().encode('utf-8')).hexdigest()
        identity = uuid.uuid4().hex
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM core2_documents WHERE project=? AND digest=?', (project, digest)).fetchone()
            if old:
                # A repeated import can restrict sensitivity, never silently make data public.
                if sensitive and not old['sensitive']:
                    db.execute('UPDATE core2_documents SET sensitive=1,active=0 WHERE id=?', (old['id'],))
                return {**dict(old), 'duplicate': True, 'sensitive': bool(old['sensitive'] or sensitive),
                        'active': bool(old['active'] and not sensitive)}
            db.execute('INSERT INTO core2_documents (id,project,source_name,source_key,digest,created_at,sensitive) VALUES(?,?,?,?,?,?,?)',
                       (identity, project, path.name[:200], source_key, digest,
                        datetime.now(timezone.utc).isoformat(), int(sensitive)))
            db.executemany('INSERT INTO core2_document_chunks(document_id,position,body) VALUES(?,?,?)',
                           [(identity, position, piece) for position, piece in enumerate(pieces)])
        return {'id': identity, 'source_name': path.name[:200], 'chunks': len(pieces), 'approved': False, 'duplicate': False}

    def list(self, project):
        project = self.base._project(project)
        with self.base.connect() as db:
            return [dict(row) for row in db.execute('''SELECT id,source_name,created_at,approved,sensitive,active
                FROM core2_documents WHERE project=? ORDER BY created_at DESC LIMIT 100''', (project,))]

    def review(self, identity, *, approve=False, allow_sensitive=False):
        if type(approve) is not bool or type(allow_sensitive) is not bool:
            raise ValueError('Confirmación inválida.')
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            document = db.execute('SELECT * FROM core2_documents WHERE id=?', (identity,)).fetchone()
            if not document or document['sensitive'] and not allow_sensitive:
                raise ValueError('Documento no disponible o sensible; usa el CLI con autorización explícita.')
            if approve:
                db.execute('UPDATE core2_documents SET active=0 WHERE project=? AND source_key=?',
                           (document['project'], document['source_key']))
                db.execute('UPDATE core2_documents SET approved=1,active=1 WHERE id=?', (identity,))
            rows = db.execute('SELECT position,body FROM core2_document_chunks WHERE document_id=? ORDER BY position LIMIT 4', (identity,))
            return {'id': identity, 'approved': bool(approve or document['approved']),
                    'preview': [dict(row) for row in rows], 'preview_limit': 4}

    def search(self, project, query, *, limit=3):
        project = self.base._project(project)
        if not isinstance(query, str) or len(query) > 1000 or type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError('Consulta de conocimiento inválida.')
        terms = sorted(words(query))[:16]
        if not terms:
            return []
        # FTS operators and punctuation from documents/user input never become SQL or FTS syntax.
        expression = ' OR '.join('"' + term.replace('"', '""') + '"' for term in terms)
        with self.base.connect() as db:
            rows = db.execute('''SELECT d.id AS document_id,d.source_name,c.position,c.body,bm25(core2_document_search) AS rank
                FROM core2_document_search JOIN core2_document_chunks c ON c.id=core2_document_search.rowid
                JOIN core2_documents d ON d.id=c.document_id
                WHERE core2_document_search MATCH ? AND d.project=? AND d.approved=1 AND d.active=1 AND d.sensitive=0
                ORDER BY rank,c.id LIMIT ?''', (expression, project, limit))
            return [dict(row) for row in rows]

    def delete(self, identity, *, allow_sensitive=False):
        with self.base.connect() as db:
            db.execute('PRAGMA secure_delete=ON')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT sensitive FROM core2_documents WHERE id=?', (identity,)).fetchone()
            if not row or row['sensitive'] and not allow_sensitive:
                raise ValueError('Documento no disponible o eliminación sensible sin autorización.')
            db.execute('DELETE FROM core2_document_chunks WHERE document_id=?', (identity,))
            db.execute('DELETE FROM core2_documents WHERE id=?', (identity,))
            db.execute("INSERT INTO core2_document_search(core2_document_search) VALUES('optimize')")
        return {'deleted': identity}
