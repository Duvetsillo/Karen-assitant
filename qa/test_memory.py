"""Memory persistence, project isolation, sensitivity and explicit management."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from karen_memory import MemoryStore
from conversations import Conversations
from karen_app import KarenClient


ROOT = Path(__file__).resolve().parents[1]


class MemoryTests(unittest.TestCase):
    def test_crud_search_deduplication_and_project_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / 'core.sqlite3')
            first = store.add('Karen', 'Prefiero respuestas breves.', confirmed=True)
            self.assertEqual(store.add('Karen', '  prefiero   respuestas breves. ')["id"], first['id'])
            store.add('Home Lab', 'Prefiero respuestas breves.', confirmed=False)
            inferred = store.add('Estudio', 'Preparar tesis', confirmed=False)
            confirmed = store.add('Estudio', 'preparar tesis', confirmed=True)
            self.assertEqual(confirmed['id'], inferred['id'])
            self.assertEqual(confirmed['status'], 'confirmed')
            self.assertEqual(len(store.list('Karen', 'respuestas')), 1)
            self.assertEqual(store.list('Karen', 'Home Lab'), [])
            edited = store.edit(first['id'], 'Prefiero respuestas concisas.', confirmed=False)
            self.assertEqual(edited['status'], 'inferred')
            self.assertEqual(store.get(first['id'])['content'], 'Prefiero respuestas concisas.')
            self.assertEqual(json.loads(store.export_json('Karen'))['memories'][0]['id'], first['id'])
            self.assertTrue(store.delete(first['id']))
            self.assertIsNone(store.get(first['id']))
            self.assertFalse(store.delete(first['id']))
            self.assertEqual(len(store.list('Home Lab')), 1)

    def test_sensitive_memory_requires_explicit_access(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / 'core.sqlite3')
            with self.assertRaises(PermissionError):
                store.add('Karen', 'Dato privado', sensitive=True)
            saved = store.add('Karen', 'Dato privado', sensitive=True, allow_sensitive=True,
                              retention_days=30)
            self.assertIsNotNone(saved['expires_at'])
            self.assertEqual(store.list('Karen'), [])
            self.assertIsNone(store.get(saved['id']))
            self.assertEqual(json.loads(store.export_json('Karen'))['memories'], [])
            with self.assertRaises(PermissionError):
                store.add('Karen', 'Dato privado')
            with self.assertRaises(PermissionError):
                store.edit(saved['id'], 'Otro dato')
            with self.assertRaises(PermissionError):
                store.delete(saved['id'])
            self.assertEqual(len(store.list('Karen', include_sensitive=True)), 1)
            self.assertTrue(store.delete(saved['id'], allow_sensitive=True))

    def test_duplicate_explicitly_marked_sensitive_becomes_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / 'core.sqlite3')
            public = store.add('Karen', 'Mi nombre es Ana', confirmed=False)
            with self.assertRaises(PermissionError):
                store.add('Karen', 'Mi nombre es Ana', sensitive=True)
            private = store.add('Karen', 'Mi nombre es Ana', confirmed=True,
                                sensitive=True, allow_sensitive=True)
            self.assertEqual(private['id'], public['id'])
            self.assertTrue(private['sensitive'])
            self.assertEqual(private['status'], 'confirmed')
            self.assertIsNone(store.get(public['id']))
            self.assertEqual(store.list('Karen'), [])
            self.assertEqual(json.loads(store.export_json('Karen'))['memories'], [])
            with self.assertRaises(PermissionError):
                store.add('Karen', 'Mi nombre es Ana')
            self.assertTrue(store.add('Karen', 'Mi nombre es Ana', allow_sensitive=True)['sensitive'])

    def test_expired_duplicate_can_be_saved_again(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / 'core.sqlite3')
            original = store.add('Karen', 'Prefiere el modo local', sensitive=True,
                                 allow_sensitive=True, retention_days=1)
            with store.connect() as db:
                db.execute('UPDATE core_memories SET expires_at=? WHERE id=?',
                           ('2020-01-01T00:00:00+00:00', original['id']))
            self.assertEqual(store.list('Karen'), [])
            self.assertIsNone(store.get(original['id'], include_sensitive=True))
            self.assertEqual(json.loads(store.export_json('Karen', include_sensitive=True))['memories'], [])
            renewed = store.add('Karen', 'Prefiere el modo local', retention_days=30)
            self.assertEqual(renewed['id'], original['id'])
            self.assertFalse(renewed['sensitive'])
            self.assertEqual(len(store.list('Karen')), 1)

    def test_cli_exports_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'core.sqlite3'
            output = Path(directory) / 'memories.json'
            command = [sys.executable, str(ROOT / 'memory_cli.py'), '--db', str(database)]
            subprocess.run(command + ['add', 'Estudio', 'Preparar tesis'], check=True,
                           capture_output=True, text=True)
            subprocess.run(command + ['export', 'Estudio', str(output)], check=True,
                           capture_output=True, text=True)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['memories'][0]['content'],
                             'Preparar tesis')
            repeated = subprocess.run(command + ['export', 'Estudio', str(output)],
                                      capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(len(MemoryStore(database).list('Estudio')), 1)

    def test_chat_commands_stay_local_and_out_of_conversation_history(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat = archive.create()
            client = KarenClient('http://127.0.0.1:11434')
            client.archive, client.chat_id = archive, chat
            with (patch.object(client.home, 'execute', side_effect=AssertionError('No llamar HA')),
                  patch('karen_app.requests.post', side_effect=AssertionError('No llamar modelo'))):
                saved = client.ask('/memoria guardar Karen | Responder brevemente')
                memory_id = saved.rsplit('ID: ', 1)[1].rstrip('.')
                self.assertIn('Responder brevemente', client.ask('/memoria buscar Karen | brevemente'))
                self.assertIn('editada', client.ask(f'/memoria editar {memory_id} | Responder conciso'))
                self.assertIn('borrada', client.ask(f'/memoria borrar {memory_id}'))
            self.assertEqual(archive.exchanges(chat), [])


if __name__ == '__main__':
    unittest.main()
