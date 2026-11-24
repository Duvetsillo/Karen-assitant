"""Local conversation archive. Each exchange is committed atomically."""
import sqlite3
import uuid
import os
import json
import re
from contextlib import contextmanager
from pathlib import Path


DEFAULT_PATH = Path(__file__).parent / '.private' / 'conversations.sqlite3'


class Conversations:
    def __init__(self, path=None):
        configured = os.getenv('KAREN_CORE_DB') if path is None else None
        if configured and not Path(configured).is_absolute():
            raise ValueError('KAREN_CORE_DB debe ser una ruta absoluta')
        self.path = Path(path or configured) if (path or configured) else DEFAULT_PATH
        self.timeout = 10
        self.must_exist = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_meta'").fetchone()
            if exists:
                row = db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()
                if not row or row[0] != '1':
                    raise ValueError(f"Versión de Karen Core no compatible: {row[0] if row else 'sin versión'}")
                events = db.execute("SELECT value FROM core_meta WHERE key='events_version'").fetchone()
                if events and events[0] != '1':
                    raise ValueError('Versión de eventos Core no compatible.')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS exchanges (
                    id INTEGER PRIMARY KEY, chat_id TEXT NOT NULL,
                    prompt TEXT NOT NULL, answer TEXT NOT NULL, ok INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS core_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT OR IGNORE INTO core_meta (key,value) VALUES ('schema_version','1');
            ''')
            version = db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()[0]
            if version != '1':
                raise ValueError(f'Versión de Karen Core no compatible: {version}')
            from core_events import install_events
            install_events(db)

    @contextmanager
    def connect(self):
        if getattr(self, 'must_exist', False):
            db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=self.timeout)
        else:
            db = sqlite3.connect(self.path, timeout=getattr(self, 'timeout', 10))
        try:
            with db:
                yield db
        finally:
            db.close()

    @classmethod
    def open_existing(cls, path, timeout=0.2):
        """Worker view: no schema initialization and never create a missing file."""
        archive = cls.__new__(cls)
        archive.path = Path(path)
        archive.timeout = timeout
        archive.must_exist = True
        return archive

    def check_version(self):
        with self.connect() as db:
            rows = dict(db.execute('SELECT key,value FROM core_meta'))
            if rows.get('schema_version') != '1' or rows.get('events_version') != '1':
                raise ValueError('Versión de Karen Core no compatible.')

    def activate(self, chat_id):
        with self.connect() as db:
            changed = db.execute("INSERT OR REPLACE INTO preferences (key,value) "
                                 "SELECT 'active',id FROM chats WHERE id=?", (chat_id,))
            if changed.rowcount != 1:
                raise KeyError('Conversación desconocida.')

    def get_voice_style(self):
        from karen_personality import validate_style
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE key='core.voice_style'").fetchone()
        if not row:
            return None
        try:
            return validate_style(row[0])
        except ValueError:
            return None

    def set_voice_style(self, style):
        from karen_personality import validate_style
        validate_style(style)
        with self.connect() as db:
            db.execute("INSERT INTO preferences (key,value) VALUES ('core.voice_style',?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (style,))

    def get_mode(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE key='core.mode'").fetchone()
        return row[0] if row and row[0] in {'normal', 'gaming', 'do_not_disturb'} else None

    def set_mode(self, mode):
        if not isinstance(mode, str) or mode not in {'normal', 'gaming', 'do_not_disturb'}:
            raise ValueError('Modo desconocido.')
        with self.connect() as db:
            db.execute("INSERT INTO preferences (key,value) VALUES ('core.mode',?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (mode,))

    def current(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT value FROM preferences WHERE key='active'").fetchone()
            if row and db.execute('SELECT 1 FROM chats WHERE id=?', row).fetchone():
                return row[0]
            return self._create(db)

    @staticmethod
    def _create(db):
        chat_id = uuid.uuid4().hex
        db.execute('INSERT INTO chats (id,title) VALUES (?,?)', (chat_id, 'Nueva conversación'))
        db.execute("INSERT OR REPLACE INTO preferences VALUES ('active', ?)", (chat_id,))
        return chat_id

    def create(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._create(db)

    def list(self):
        with self.connect() as db:
            return db.execute('SELECT id,title,updated FROM chats ORDER BY updated DESC, rowid DESC').fetchall()

    def exchanges(self, chat_id):
        with self.connect() as db:
            return db.execute('SELECT prompt,answer,ok FROM exchanges WHERE chat_id=? ORDER BY id', (chat_id,)).fetchall()

    def latest_exchange_id(self, chat_id):
        with self.connect() as db:
            return db.execute('SELECT COALESCE(MAX(id),0) FROM exchanges WHERE chat_id=?', (chat_id,)).fetchone()[0]

    def append(self, chat_id, prompt, answer, ok):
        with self.connect() as db:
            # Serialize with deletion and prevent orphan turns from late workers.
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM chats WHERE id=?', (chat_id,)).fetchone():
                raise KeyError('Conversación desconocida.')
            empty = not db.execute('SELECT 1 FROM exchanges WHERE chat_id=? LIMIT 1', (chat_id,)).fetchone()
            db.execute('INSERT INTO exchanges (chat_id,prompt,answer,ok) VALUES (?,?,?,?)', (chat_id,prompt,answer,int(ok)))
            if empty:
                db.execute("UPDATE chats SET title=? WHERE id=? AND title='Nueva conversación'",
                           (' '.join(prompt.split())[:65],chat_id))
            db.execute('UPDATE chats SET updated=CURRENT_TIMESTAMP WHERE id=?', (chat_id,))

    def search(self, query, limit=50):
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
            raise ValueError('Búsqueda inválida (1 a 200 caracteres).')
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Límite inválido.')
        needle = '%' + query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        with self.connect() as db:
            return db.execute('''SELECT id,title,updated FROM chats c
                WHERE title LIKE ? ESCAPE '\\' OR EXISTS
                  (SELECT 1 FROM exchanges e WHERE e.chat_id=c.id AND
                    (e.prompt LIKE ? ESCAPE '\\' OR e.answer LIKE ? ESCAPE '\\'))
                ORDER BY updated DESC,c.rowid DESC LIMIT ?''', (needle, needle, needle, limit)).fetchall()

    def rename(self, chat_id, title):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 65 or re.search(r'[\x00-\x1f\x7f]', title):
            raise ValueError('Título inválido (1 a 65 caracteres, sin controles).')
        with self.connect() as db:
            result = db.execute('UPDATE chats SET title=?,updated=CURRENT_TIMESTAMP WHERE id=?', (title.strip(), chat_id))
            if result.rowcount != 1:
                raise KeyError('Conversación desconocida.')

    def export_json(self, chat_id):
        with self.connect() as db:
            # A consistent read snapshot, even when the other client appends.
            db.execute('BEGIN')
            chat = db.execute('SELECT id,title,updated FROM chats WHERE id=?', (chat_id,)).fetchone()
            if not chat:
                raise KeyError('Conversación desconocida.')
            rows = db.execute('SELECT prompt,answer,ok FROM exchanges WHERE chat_id=? ORDER BY id', (chat_id,)).fetchall()
        return json.dumps({'contract': 1, 'chat': dict(zip(('id','title','updated'), chat)),
                           'exchanges': [dict(zip(('prompt','answer','ok'), row)) for row in rows]},
                          ensure_ascii=False, indent=2)

    def delete(self, chat_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM chats WHERE id=?', (chat_id,)).fetchone():
                return False
            db.execute('DELETE FROM exchanges WHERE chat_id=?', (chat_id,))
            db.execute("DELETE FROM preferences WHERE key='active' AND value=?", (chat_id,))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='core_external_turns'").fetchone():
                db.execute('DELETE FROM core_external_turns WHERE chat_id=?', (chat_id,))
            db.execute('DELETE FROM chats WHERE id=?', (chat_id,))
            return True

    def context(self, chat_id, max_chars=16000, max_turns=12):
        with self.connect() as db:
            rows = db.execute('SELECT prompt,answer FROM exchanges WHERE chat_id=? AND ok=1 ORDER BY id DESC LIMIT ?', (chat_id,max_turns)).fetchall()
        turns, size = [], 0
        for prompt, answer in rows:
            size += len(prompt) + len(answer)
            if size > max_chars:
                break
            turns.append([{'role':'user','content':prompt}, {'role':'assistant','content':answer}])
        return [message for turn in reversed(turns) for message in turn]


def open_archive():
    """Keep classic chat available when the optional shared Core is unusable."""
    try:
        archive = Conversations()
        return archive, archive.current(), None
    except (OSError, sqlite3.Error, ValueError):
        if not os.getenv('KAREN_CORE_DB'):
            raise
        archive = Conversations(DEFAULT_PATH)
        return (archive, archive.current(),
                'Karen Core no está disponible. Se abrió el historial local; revisa KAREN_CORE_DB.')
