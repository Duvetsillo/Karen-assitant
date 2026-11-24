"""Versioned SQLite contract shared by Karen classic and Desktop Pet."""
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from conversations import Conversations, open_archive
from config import KarenConfig, load_config, save_config
from karen_app import KarenApp
from karen_personality import STYLE_LABELS


class CoreContractTests(unittest.TestCase):
    def test_shared_voice_style_is_opt_in_and_env_override_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'shared.sqlite3'
            settings = Path(directory) / 'settings.json'
            with patch('config.CONFIG_PATH', settings), patch.dict(os.environ, {'KAREN_CORE_DB': str(path)}):
                archive = Conversations()
                self.assertIsNone(archive.get_voice_style())
                archive.set_voice_style('warm')
                self.assertEqual(load_config().voice_style, 'warm')
                with patch.dict(os.environ, {'KAREN_VOICE_STYLE': 'serious'}):
                    self.assertEqual(load_config().voice_style, 'serious')
                save_config(KarenConfig(voice_style='bright'))
                self.assertEqual(archive.get_voice_style(), 'bright')
                self.assertEqual(load_config().voice_style, 'bright')
                with self.assertRaisesRegex(ValueError, 'desconocido'):
                    archive.set_voice_style('invalid')
            with patch('config.CONFIG_PATH', settings), patch.dict(os.environ, {'KAREN_CORE_DB': 'relative.sqlite3'}):
                self.assertFalse(save_config(KarenConfig(voice_style='neutral')))

    def test_explicit_shared_database_preserves_classic_conversations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'shared.sqlite3'
            with patch.dict(os.environ, {'KAREN_CORE_DB': str(path)}):
                archive = Conversations()
                chat = archive.create()
                archive.append(chat, 'Hola', 'Respuesta', True)
                self.assertEqual(Conversations().context(chat)[1]['content'], 'Respuesta')
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()[0], '1')

    def test_rejects_relative_path_and_newer_schema(self):
        with patch.dict(os.environ, {'KAREN_CORE_DB': 'relative.sqlite3'}):
            with self.assertRaisesRegex(ValueError, 'absoluta'):
                Conversations()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'newer.sqlite3'
            Conversations(path)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE core_meta SET value='99' WHERE key='schema_version'")
            with self.assertRaisesRegex(ValueError, 'no compatible'):
                Conversations(path)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()[0], '99')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'foreign.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE core_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                db.execute("INSERT INTO core_meta VALUES ('schema_version','99')")
            with self.assertRaisesRegex(ValueError, 'no compatible'):
                Conversations(path)
            with closing(sqlite3.connect(path)) as db:
                self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='chats'").fetchone())

    def test_classic_falls_back_to_local_history_when_shared_schema_is_newer(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = Path(directory) / 'shared.sqlite3'
            local = Path(directory) / 'local.sqlite3'
            Conversations(shared)
            with closing(sqlite3.connect(shared)) as db, db:
                db.execute("UPDATE core_meta SET value='99' WHERE key='schema_version'")
            with (patch.dict(os.environ, {'KAREN_CORE_DB': str(shared)}, clear=True),
                  patch('conversations.DEFAULT_PATH', local),
                  patch('config.CONFIG_PATH', Path(directory) / 'settings.json')):
                self.assertEqual(load_config().voice_style, 'serene')
                archive, chat_id, warning = open_archive()
                self.assertEqual(archive.path, local)
                self.assertIn('historial local', warning)
                archive.append(chat_id, 'Hola', 'Respuesta local', True)
                self.assertEqual(archive.context(chat_id)[1]['content'], 'Respuesta local')
            with closing(sqlite3.connect(shared)) as db:
                self.assertEqual(db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()[0], '99')

    def test_live_voice_style_read_applies_without_writing_back(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'core.sqlite3')
            archive.set_voice_style('warm')
            field = Mock()
            field.get.return_value = STYLE_LABELS['serene']
            app = SimpleNamespace(
                closed=Event(), core_sync_enabled=True, core_sync_failed=False,
                archive_style_pending=None,
                archive=archive, config=KarenConfig(voice_style='serene'),
                client=SimpleNamespace(voice_style='serene'),
                fields={'voice_style': field}, voice_style_labels=STYLE_LABELS,
                root=Mock(), log=Mock(),
            )
            with patch('karen_app.save_config', side_effect=AssertionError('No escribir de vuelta')):
                KarenApp.apply_shared_voice_style(app, archive.get_voice_style())
            self.assertEqual(app.config.voice_style, 'warm')
            self.assertEqual(app.client.voice_style, 'warm')
            field.set.assert_called_once_with(STYLE_LABELS['warm'])
            app.root.after.assert_not_called()
            app.config = KarenConfig(voice_style='serene')
            app.client.voice_style = 'serene'
            field.get.return_value = STYLE_LABELS['bright']  # Cambio del usuario aún sin guardar.
            field.set.reset_mock()
            KarenApp.apply_shared_voice_style(app, archive.get_voice_style())
            self.assertEqual(app.config.voice_style, 'serene')
            field.set.assert_not_called()


if __name__ == '__main__':
    unittest.main()
