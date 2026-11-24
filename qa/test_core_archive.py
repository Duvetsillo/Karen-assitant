"""Real SQLite and Tk checks for the asynchronous Core client.

Gates below simulate slow work explicitly. SQLite lock and GUI responsiveness
tests use real connections/windows. No provider, audio, or external host is used.
"""

from contextlib import closing
from dataclasses import replace
import gc
from pathlib import Path
import queue
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from config import KarenConfig
from conversations import Conversations
from core_archive import ArchiveRequest, ArchiveResult, ArchiveWorker, read_snapshot
from karen_app import KarenApp
from qa.ui_helpers import close_app, pump_until, wait_archive


class ArchiveWorkerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'core.sqlite3'
        self.archive = Conversations(self.path)
        self.chat_id = self.archive.create()
        self.results = queue.Queue()
        self.worker = ArchiveWorker(self.path, self.results.put)

    def tearDown(self):
        self.worker.close()
        self.worker.thread.join(2)
        self.assertFalse(self.worker.thread.is_alive())
        self.directory.cleanup()

    def test_snapshot_and_selection_are_serialized_and_do_not_migrate(self):
        self.archive.append(self.chat_id, 'Primera', 'Respuesta', True)
        # A worker does not call the constructor/migration on every poll.
        with patch.object(Conversations, '__init__', side_effect=AssertionError('No migrations')):
            self.worker.submit(1, 'snapshot', self.chat_id)
            result = self.results.get(timeout=2)
            self.assertIsNone(result.error)
            self.assertEqual(result.snapshot.exchanges, (('Primera', 'Respuesta', 1),))
            self.worker.submit(2, 'create', self.chat_id)
            created = self.results.get(timeout=2)
            self.assertNotEqual(created.snapshot.chat_id, self.chat_id)
            self.assertEqual(self.archive.current(), created.snapshot.chat_id)
            self.worker.submit(3, 'select', self.chat_id)
            selected = self.results.get(timeout=2)
            self.assertEqual(selected.snapshot.chat_id, self.chat_id)
            self.assertEqual(selected.request.epoch, 3)

    def test_unchanged_snapshot_omits_messages_but_keeps_style_and_choices(self):
        self.archive.append(self.chat_id, 'Pregunta', 'Respuesta', True)
        latest = self.archive.latest_exchange_id(self.chat_id)
        self.archive.set_voice_style('warm')
        self.worker.submit(1, 'snapshot', self.chat_id, known_exchange_id=latest)
        result = self.results.get(timeout=2)
        self.assertIsNone(result.snapshot.exchanges)
        self.assertEqual(result.snapshot.voice_style, 'warm')
        self.assertEqual(result.snapshot.chats[0][0], self.chat_id)

    def test_future_schema_denies_mutation_and_missing_file_is_not_created(self):
        with self.archive.connect() as db:
            db.execute("UPDATE core_meta SET value='99' WHERE key='events_version'")
        self.worker.submit(1, 'create', self.chat_id)
        self.assertEqual(self.results.get(timeout=2).error, 'incompatible')
        self.assertEqual(len(self.archive.list()), 1)
        self.worker.close()
        self.worker.thread.join(2)
        missing = Path(self.directory.name) / 'missing.sqlite3'
        self.worker = ArchiveWorker(missing, self.results.put)
        self.worker.submit(1, 'snapshot', self.chat_id)
        self.assertEqual(self.results.get(timeout=2).error, 'unavailable')
        self.assertFalse(missing.exists())

    def test_bounded_queue_and_shutdown_discard_unstarted_writes(self):
        entered, release = threading.Event(), threading.Event()
        original = read_snapshot
        def slow(*args):
            entered.set()
            release.wait(2)
            return original(*args)
        try:
            with patch('core_archive.read_snapshot', side_effect=slow):
                self.worker.submit(1, 'snapshot', self.chat_id)
                self.assertTrue(entered.wait(1))
                for _ in range(4): self.worker.submit(1, 'create', self.chat_id)
                with self.assertRaises(queue.Full): self.worker.submit(1, 'create', self.chat_id)
                self.worker.close()
                release.set()
                self.worker.thread.join(2)
            self.assertEqual(len(self.archive.list()), 1)
            self.assertTrue(self.results.empty())
        finally:
            release.set()

    def test_create_and_activation_are_atomic_when_locked(self):
        with closing(sqlite3.connect(self.path)) as locked:
            locked.execute('BEGIN EXCLUSIVE')
            self.worker.submit(1, 'create', self.chat_id)
            self.assertEqual(self.results.get(timeout=2).error, 'busy')
            locked.rollback()
        self.assertEqual(self.archive.current(), self.chat_id)
        self.assertEqual(len(self.archive.list()), 1)

    def test_two_clients_resolving_an_empty_archive_share_one_current_chat(self):
        self.archive.delete(self.chat_id)
        start = threading.Barrier(3)
        found = queue.Queue()
        def resolve():
            start.wait()
            try:
                found.put(Conversations.open_existing(self.path, timeout=1).current())
            except Exception as error:
                found.put(error)
        clients = [threading.Thread(target=resolve) for _ in range(2)]
        for client in clients: client.start()
        start.wait()
        for client in clients: client.join(2)
        first, second = found.get(timeout=1), found.get(timeout=1)
        self.assertIsInstance(first, str)
        self.assertEqual(first, second)
        self.assertEqual(len(self.archive.list()), 1)


class ArchiveGuiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'core.sqlite3'
        self.archive = Conversations(self.path)
        self.chat_id = self.archive.create()
        self.archive.append(self.chat_id, 'Sintético', 'Respuesta inicial', True)
        self.patches = [
            patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)),
            patch.object(KarenApp, 'load_catalog'),
            patch.object(KarenApp, 'connect_benchmark'),
            patch.dict('os.environ', {'KAREN_CORE_DB': str(self.path)}),
        ]
        for active in self.patches: active.start()
        self.app = KarenApp(KarenConfig(tts_enabled=False, wake_auto_start=False))
        wait_archive(self.app)

    def tearDown(self):
        close_app(self.app)
        for active in reversed(self.patches): active.stop()
        self.app = None
        # Tcl variables must be collected on their creating thread, including
        # cycles left by bound UI callbacks, before the next worker allocates.
        gc.collect()
        self.directory.cleanup()

    def test_tk_timers_continue_under_exclusive_sqlite_lock_and_recover(self):
        app = self.app
        ticks = []
        timer = None
        def tick():
            nonlocal timer
            ticks.append(time.perf_counter())
            timer = app.root.after(5, tick)
        try:
            with closing(sqlite3.connect(self.path)) as locked:
                locked.execute('BEGIN EXCLUSIVE')
                start = time.perf_counter()
                app.restore_conversation()
                submit_seconds = time.perf_counter() - start
                tick()
                pump_until(app, lambda: app.core_chat_sync_failed)
                self.assertLess(submit_seconds, 0.1)
                self.assertGreaterEqual(len(ticks), 5)
                self.assertIn('Respuesta inicial', app.chat.get('1.0', 'end'))
                locked.rollback()
            app.refresh_conversations()
            wait_archive(app)
            self.assertFalse(app.core_chat_sync_failed)
        finally:
            if timer: app.root.after_cancel(timer)

    def test_chat_crud_and_style_never_query_sqlite_from_tk(self):
        main = threading.get_ident()
        original = Conversations.connect
        def checked(archive):
            self.assertNotEqual(threading.get_ident(), main, 'SQL en el hilo Tk')
            return original(archive)
        app = self.app
        with patch.object(Conversations, 'connect', checked):
            app.change_conversation(new=True)
            wait_archive(app)
            self.assertNotEqual(app.chat_id, self.chat_id)
            old_index = next(i for i, row in enumerate(app.chat_choices) if row[0] == self.chat_id)
            app.conversation_selector.current(old_index)
            app.change_conversation()
            wait_archive(app)
            self.assertIn('Respuesta inicial', app.chat.get('1.0', 'end'))
            app.request_archive('style', style='warm')
            pump_until(app, lambda: app.archive_style_pending is None)
            app.restore_conversation()
            wait_archive(app)
            self.assertEqual(app.config.voice_style, 'warm')

    def test_deleted_active_chat_is_replaced_without_orphaning_the_ui(self):
        self.archive.delete(self.chat_id)
        self.app.refresh_conversations()
        wait_archive(self.app)
        self.assertNotEqual(self.app.chat_id, self.chat_id)
        self.assertEqual(self.app.client.chat_id, self.app.chat_id)
        self.assertNotIn('Respuesta inicial', self.app.chat.get('1.0', 'end'))

    def test_old_snapshot_cannot_replace_new_chat_or_new_turn(self):
        app = self.app
        request = ArchiveRequest(999, app.archive_epoch, 'snapshot', self.chat_id, force=True)
        old = read_snapshot(Conversations.open_existing(self.path), request)
        app.change_conversation(new=True)
        wait_archive(app)
        app.finish_archive(ArchiveResult(request, old))
        self.assertNotEqual(app.chat_id, self.chat_id)
        self.assertNotIn('Respuesta inicial', app.chat.get('1.0', 'end'))
        # Starting a model/tool turn invalidates earlier snapshots as well.
        current_request = replace(request, epoch=app.archive_epoch, chat_id=app.chat_id)
        app.request_pending = True
        app.finish_archive(ArchiveResult(current_request, old))
        self.assertNotIn('Respuesta inicial', app.chat.get('1.0', 'end'))
        app.request_pending = False

    def test_config_save_keeps_shared_write_off_tk_and_does_not_persist_api_key(self):
        app = self.app
        settings = Path(self.directory.name) / 'settings.json'
        original = Conversations.connect
        main = threading.get_ident()
        def checked(archive):
            self.assertNotEqual(threading.get_ident(), main)
            return original(archive)
        app.fields['voice_style'].set(app.voice_style_labels['bright'])
        app.fields['api_key'].delete(0, 'end')
        app.fields['api_key'].insert(0, 'SYNTHETIC-DO-NOT-PERSIST')
        with (patch.object(KarenApp, 'ensure_target', return_value=True),
              patch('config.CONFIG_PATH', settings),
              patch.object(Conversations, 'connect', checked)):
            self.assertTrue(app.save_config())
            pump_until(app, lambda: app.archive_style_pending is None)
        self.assertEqual(self.archive.get_voice_style(), 'bright')
        self.assertNotIn('SYNTHETIC-DO-NOT-PERSIST', settings.read_text(encoding='utf-8'))

    def test_slow_old_refresh_does_not_erase_a_new_local_reply(self):
        app = self.app
        old_request = ArchiveRequest(1, app.archive_epoch, 'snapshot', app.chat_id, force=True)
        old_snapshot = read_snapshot(Conversations.open_existing(self.path), old_request)
        entered, release = threading.Event(), threading.Event()
        original = read_snapshot
        def delayed(archive, request, stopped=None):
            if not entered.is_set():
                entered.set()
                release.wait(2)
                return old_snapshot
            return original(archive, request, stopped)
        try:
            with patch('core_archive.read_snapshot', side_effect=delayed):
                app.restore_conversation()
                self.assertTrue(entered.wait(1))
                app.send_prompt('/modo gaming')
                pump_until(app, lambda: not app.request_pending)
                self.assertIn('Modo compartido: gaming.', app.chat.get('1.0', 'end'))
                release.set()
                wait_archive(app)
                self.assertIn('Modo compartido: gaming.', app.chat.get('1.0', 'end'))
        finally:
            release.set()

    def test_archive_recovery_does_not_clear_a_newer_provider_error(self):
        app = self.app
        app.core_chat_sync_failed = True
        app.core_error_epoch = app.archive_epoch
        app.archive_epoch += 1  # A later generation belongs to a newer epoch.
        app.set_state('Error')
        app.refresh_conversations()
        wait_archive(app)
        self.assertFalse(app.core_chat_sync_failed)
        self.assertEqual(app.current_state, 'Error')


if __name__ == '__main__':
    unittest.main()
