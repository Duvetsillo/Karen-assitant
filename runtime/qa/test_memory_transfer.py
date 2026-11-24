"""Reviewed, one-turn memory context without external model calls."""

from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from conversations import Conversations
from karen_app import KarenClient
from karen_memory import MemoryStore
from karen_memory_transfer import MemoryTransfer


class MemoryTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.archive = Conversations(Path(self.temp.name) / 'core.sqlite3')
        self.chat_id = self.archive.current()
        self.store = MemoryStore(self.archive.path)
        self.client = KarenClient('http://localhost:11434')
        self.client.archive, self.client.chat_id = self.archive, self.chat_id

    def tearDown(self):
        self.temp.cleanup()

    def test_preview_confirmation_and_one_model_turn(self):
        public = self.store.add('Karen', 'Respuesta breve y clara', confirmed=True)
        self.store.add('Karen', 'Respuesta breve inferida', confirmed=False)
        self.store.add('Karen', 'Respuesta breve secreta', sensitive=True, allow_sensitive=True)
        with patch('karen_app.requests.post') as post, \
             patch('admin_tools.route_local', return_value=None):
            preview = self.client.ask('/memoria preparar Karen | Respuesta breve')
            self.assertIn(public['id'], preview)
            self.assertIn('Respuesta breve y clara', preview)
            self.assertNotIn('inferida', preview)
            self.assertNotIn('secreta', preview)
            self.assertIn('autorizados', self.client.ask('/memoria enviar'))
            post.assert_not_called()
            post.return_value.json.return_value = {'message': {'content': 'Sí, breve.'}}
            self.assertEqual(self.client.ask('Explica Karen'), 'Sí, breve.')
            first = post.call_args.kwargs['json']
            self.assertIn('Respuesta breve y clara', first['messages'][0]['content'])
            self.assertNotIn('secreta', str(first))
            self.client.ask('Otra consulta')
            second = post.call_args.kwargs['json']
            self.assertNotIn('Respuesta breve y clara', second['messages'][0]['content'])
        self.assertEqual([r[0] for r in self.archive.exchanges(self.chat_id)],
                         ['Explica Karen', 'Otra consulta'])
        with closing(sqlite3.connect(self.archive.path)) as db:
            usage = db.execute('SELECT memory_id,chat_id,backend FROM core_memory_usage').fetchall()
        self.assertEqual(usage, [(public['id'], self.chat_id, 'ollama')])

    def test_context_change_or_memory_edit_revokes_transfer(self):
        memory = self.store.add('Karen', 'Prefiero respuestas breves')
        with patch('karen_app.requests.post') as post, \
             patch('admin_tools.route_local', return_value=None):
            self.client.ask('/memoria preparar Karen | breves')
            self.client.model = 'otro:1'
            self.assertIn('caducó o cambió', self.client.ask('/memoria enviar'))
            post.assert_not_called()
            self.client.model = 'qwen2:0.5b'
            self.client.ask('/memoria preparar Karen | breves')
            self.client.ask('/memoria enviar')
            self.store.edit(memory['id'], 'Ahora prefiero respuestas largas')
            post.return_value.json.return_value = {'message': {'content': 'Entendido.'}}
            self.client.ask('Pregunta normal')
            self.assertNotIn('Prefiero respuestas breves',
                             str(post.call_args.kwargs['json']))
        with closing(sqlite3.connect(self.archive.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM core_memory_usage').fetchone()[0], 0)

    def test_expiry_and_cancel_clear_prepared_context(self):
        self.store.add('Karen', 'Respuestas breves')
        now = [100.0]
        transfer = MemoryTransfer(lambda: now[0])
        key = (self.chat_id, 'session', 'ollama', 'localhost', 'model')
        self.assertIn('Respuestas breves', transfer.prepare(self.store, 'Karen', 'breves', key))
        now[0] = 401.0
        with self.assertRaises(ValueError):
            transfer.confirm(self.store, key)
        transfer.prepare(self.store, 'Karen', 'breves', key)
        transfer.cancel()
        self.assertIsNone(transfer.consume(self.store, key))

    def test_deletion_after_approval_prevents_transmission(self):
        memory = self.store.add('Karen', 'Recordar la decisión de diseño')
        with patch('karen_app.requests.post') as post, \
             patch('admin_tools.route_local', return_value=None):
            self.client.ask('/memoria preparar Karen | diseño')
            self.client.ask('/memoria enviar')
            self.store.delete(memory['id'])
            post.return_value.json.return_value = {'message': {'content': 'Sin contexto.'}}
            self.client.ask('Explica la decisión')
            self.assertNotIn('Recordar la decisión de diseño', str(post.call_args.kwargs['json']))

    def test_custom_karen_api_receives_only_reviewed_context_once(self):
        self.store.add('Karen', 'Respuesta directa')
        self.client.backend = 'karen'
        with patch('karen_app.requests.post') as post, \
             patch('admin_tools.route_local', return_value=None):
            self.client.ask('/memoria preparar Karen | directa')
            self.client.ask('/memoria enviar')
            post.return_value.json.return_value = {'respuesta': 'Hecho.'}
            self.client.ask('Consulta')
            first = post.call_args.kwargs['json']
            self.assertIn('Respuesta directa', first['mensaje'])
            self.client.ask('Otra')
            second = post.call_args.kwargs['json']
            self.assertEqual(second['mensaje'], 'Otra')

    def test_audit_rechecks_sensitivity_and_content_atomically(self):
        memory = self.store.add('Karen', 'Dato que fue público')
        rows = [(memory['id'], memory['content'])]
        self.store.add('Karen', 'Dato que fue público', sensitive=True, allow_sensitive=True)
        with self.assertRaises(ValueError):
            self.store.log_transfer(rows, self.chat_id, 'ollama')
        other = self.store.add('Karen', 'Preferencia confirmada')
        self.store.edit(other['id'], 'Preferencia cambiada')
        with self.assertRaises(ValueError):
            self.store.log_transfer([(other['id'], 'Preferencia confirmada')], self.chat_id, 'ollama')
        with closing(sqlite3.connect(self.archive.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM core_memory_usage').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
