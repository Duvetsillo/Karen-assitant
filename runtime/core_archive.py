"""Typed, serialized classic-client adapter for Karen Core v1.

No Tk calls or provider requests occur here. Snapshot results are immutable,
read in one transaction, and identified by the UI session epoch that requested
them. A bounded command queue prevents polling from growing without limit.
"""

from dataclasses import dataclass
from pathlib import Path
import queue
import sqlite3
import threading
from typing import Literal

from conversations import Conversations

Action = Literal['snapshot', 'select', 'create', 'style']


@dataclass(frozen=True)
class ArchiveRequest:
    sequence: int
    epoch: int
    action: Action
    chat_id: str
    known_exchange_id: int = -1
    force: bool = False
    style: str | None = None


@dataclass(frozen=True)
class ArchiveSnapshot:
    chat_id: str
    chats: tuple[tuple[str, str, str], ...]
    exchanges: tuple[tuple[str, str, int], ...] | None
    latest_exchange_id: int
    voice_style: str | None
    revision: int
    contract: Literal[1] = 1


@dataclass(frozen=True)
class ArchiveResult:
    request: ArchiveRequest
    snapshot: ArchiveSnapshot | None = None
    error: Literal['busy', 'incompatible', 'missing_chat', 'unavailable'] | None = None
    contract: Literal[1] = 1


def read_snapshot(archive, request, stopped=None):
    """A consistent chat list, messages, and style, never three different reads."""
    with archive.connect() as db:
        if stopped is not None:
            db.set_progress_handler(lambda: int(stopped.is_set()), 1000)
        db.execute('BEGIN')
        metadata = dict(db.execute('SELECT key,value FROM core_meta'))
        if metadata.get('schema_version') != '1' or metadata.get('events_version') != '1':
            raise ValueError('Versión de Karen Core no compatible.')
        chats = tuple(db.execute('SELECT id,title,updated FROM chats ORDER BY updated DESC,rowid DESC'))
        if not any(row[0] == request.chat_id for row in chats):
            raise KeyError('Conversación desconocida.')
        latest = db.execute('SELECT COALESCE(MAX(id),0) FROM exchanges WHERE chat_id=?', (request.chat_id,)).fetchone()[0]
        messages = None
        if request.force or latest != request.known_exchange_id:
            messages = tuple(db.execute('SELECT prompt,answer,ok FROM exchanges WHERE chat_id=? ORDER BY id', (request.chat_id,)))
        style = db.execute("SELECT value FROM preferences WHERE key='core.voice_style'").fetchone()
        from karen_personality import validate_style
        try:
            voice_style = validate_style(style[0]) if style else None
        except ValueError:
            voice_style = None
        revision = db.execute('SELECT COALESCE(MAX(seq),0) FROM core_events').fetchone()[0]
        return ArchiveSnapshot(request.chat_id, chats, messages, latest, voice_style, revision)


class ArchiveWorker:
    def __init__(self, path, completed):
        self.path = Path(path)
        self.completed = completed
        self.commands = queue.Queue(maxsize=4)
        self.stopped = threading.Event()
        self.sequence = 0
        self.thread = threading.Thread(target=self._run, name='karen-core-archive', daemon=True)
        self.thread.start()

    def submit(self, epoch, action, chat_id, *, known_exchange_id=-1, force=False, style=None):
        if self.stopped.is_set():
            raise RuntimeError('El archivo de Core se está cerrando.')
        if action not in {'snapshot', 'select', 'create', 'style'}:
            raise ValueError('Operación de archivo desconocida.')
        self.sequence += 1
        request = ArchiveRequest(self.sequence, epoch, action, chat_id, known_exchange_id, force, style)
        self.commands.put_nowait(request)
        return request.sequence

    def _execute(self, archive, request):
        archive.check_version()
        if self.stopped.is_set():
            return None
        if request.action == 'style':
            archive.set_voice_style(request.style)
            return None
        chat_id = request.chat_id
        if request.action == 'create':
            chat_id = archive.create()
        elif request.action == 'select':
            archive.activate(chat_id)
        else:
            # Recover a deleted chat only in this background worker.
            with archive.connect() as db:
                exists = db.execute('SELECT 1 FROM chats WHERE id=?', (chat_id,)).fetchone()
            if not exists:
                chat_id = archive.current()
        request_for_read = ArchiveRequest(request.sequence, request.epoch, request.action, chat_id,
                                          request.known_exchange_id,
                                          request.force or chat_id != request.chat_id or request.action in {'create', 'select'})
        return read_snapshot(archive, request_for_read, self.stopped)

    def _run(self):
        archive = Conversations.open_existing(self.path)
        while not self.stopped.is_set():
            try:
                request = self.commands.get(timeout=0.1)
            except queue.Empty:
                continue
            if self.stopped.is_set():
                self.commands.task_done()
                break
            try:
                result = ArchiveResult(request, self._execute(archive, request))
            except sqlite3.OperationalError as exc:
                error = 'busy' if getattr(exc, 'sqlite_errorcode', 0) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} else 'unavailable'
                result = ArchiveResult(request, error=error)
            except ValueError:
                result = ArchiveResult(request, error='incompatible')
            except KeyError:
                result = ArchiveResult(request, error='missing_chat')
            except (OSError, sqlite3.Error):
                result = ArchiveResult(request, error='unavailable')
            # Main thread receives values only; never run a Tk callback here.
            if not self.stopped.is_set():
                self.completed(result)
            self.commands.task_done()

    def close(self):
        self.stopped.set()
        while True:
            try:
                self.commands.get_nowait()
                self.commands.task_done()
            except queue.Empty:
                break
