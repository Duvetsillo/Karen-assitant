"""Live loopback checks for the bounded, authenticated Core HTTP contract."""

import http.client
from contextlib import closing
from http.server import ThreadingHTTPServer
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from core_local_api import ClientRegistry, load_token, make_handler, save_token, read_contract
from karen_tasks import TaskEngine, ToolSpec
from karen_memory import MemoryStore
from karen_alerts import AlertEngine


class CoreLocalApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / 'core.db'
        self.token_file = Path(self.temp.name) / 'api.dpapi'
        self.clients_file = Path(self.temp.name) / 'clients.db'
        self.tasks_file = Path(self.temp.name) / 'tasks.db'
        self.alerts_file = Path(self.temp.name) / 'alerts.db'
        self.archive = Conversations(self.db_path)
        self.chat_id = self.archive.current()
        self.archive.append(self.chat_id, 'Pregunta', 'Respuesta', True)
        self.token = save_token(self.token_file)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0),
                                          make_handler(self.db_path, self.token,
                                                       self.clients_file, self.tasks_file,
                                                       self.alerts_file))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, token=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        try:
            conn.request(method, path, headers=headers)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            conn.close()

    def test_dpapi_token_and_rotation(self):
        self.assertEqual(load_token(self.token_file), self.token)
        self.assertNotIn(self.token.encode('ascii'), self.token_file.read_bytes())
        replacement = save_token(self.token_file)
        self.assertNotEqual(self.token, replacement)
        self.assertEqual(load_token(self.token_file), replacement)
        self.assertEqual(self.request('GET', '/v1/status', replacement)[0], 401)
        # The running server needs restart to pick up token rotation.
        self.assertEqual(self.request('GET', '/v1/status', self.token)[0], 200)

    def test_authenticated_read_contract(self):
        status, headers, body = self.request('GET', '/v1/status', self.token)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(body, {'contract': 1, 'active_chat_id': self.chat_id, 'mode': 'normal'})
        self.archive.set_mode('gaming')
        self.assertEqual(self.request('GET', '/v1/status', self.token)[2]['mode'], 'gaming')
        chats = self.request('GET', '/v1/chats', self.token)[2]
        self.assertEqual(chats['chats'][0]['id'], self.chat_id)
        exchanges = self.request('GET', f'/v1/chats/{self.chat_id}/exchanges', self.token)[2]
        self.assertEqual(exchanges['exchanges'][0]['answer'], 'Respuesta')
        self.assertEqual(exchanges['limit'], 20)

    def test_pet_chats_events_and_activity_use_the_same_authenticated_contract(self):
        pet_chat = 'openclaw-' + 'a' * 32
        with self.archive.connect() as db:
            db.execute('INSERT INTO chats(id,title) VALUES(?,?)', (pet_chat, 'Pet'))
        self.archive.append(pet_chat, 'Pet question', 'Pet answer', True)
        self.archive.activate(pet_chat)
        self.assertEqual(self.request('GET', '/v1/status', self.token)[2]['active_chat_id'], pet_chat)
        self.assertEqual(self.request('GET', f'/v1/chats/{pet_chat}/exchanges', self.token)[2]['exchanges'][0]['answer'], 'Pet answer')
        status, _, body = self.request('GET', '/v1/events?after=0', self.token)
        self.assertEqual(status, 200)
        self.assertNotIn('Pet question', json.dumps(body))
        cursor = body['cursor']
        self.assertEqual(self.request('GET', f'/v1/events?after={cursor}', self.token)[2]['events'], [])
        for path in ('/v1/events?after=-1', '/v1/events?after=1&after=2', '/v1/events?bad=0', '/v1/events?after=9999999999999999999'):
            self.assertEqual(self.request('GET', path, self.token)[0], 400)
        self.assertEqual(self.request('GET', '/v1/activity', self.token)[0], 200)
        self.assertEqual(self.request('GET', '/v1/events')[0], 401)
        limited = ClientRegistry(self.clients_file).issue('status-only', 'core.status')['token']
        self.assertEqual(self.request('GET', '/v1/events', limited)[0], 403)
        self.assertEqual(self.request('GET', '/v1/activity', limited)[0], 403)

    def test_denials_do_not_write_or_leak(self):
        self.assertEqual(self.request('GET', '/v1/chats')[0], 401)
        self.assertEqual(self.request('GET', '/v1/chats', 'wrong')[0], 401)
        self.assertEqual(self.request('GET', '/v1/chats?x=1', self.token)[0], 400)
        self.assertEqual(self.request('GET', '/v1/chats/../../secrets', self.token)[0], 404)
        self.assertEqual(self.request('GET', '/v1/chats/' + 'f' * 32 + '/exchanges', self.token)[0], 404)
        self.assertEqual(self.request('POST', '/v1/chats', self.token)[0], 405)
        self.assertEqual(self.archive.exchanges(self.chat_id), [('Pregunta', 'Respuesta', 1)])

    def test_missing_database_is_not_created(self):
        missing = Path(self.temp.name) / 'missing.db'
        with self.assertRaises(FileNotFoundError):
            read_contract(missing, '/v1/status')
        self.assertFalse(missing.exists())

    def test_individual_client_can_be_revoked_without_server_restart(self):
        registry = ClientRegistry(self.clients_file)
        client = registry.issue('Portátil')
        self.assertEqual(client['scope'], 'core.read')
        self.assertEqual(self.request('GET', '/v1/chats', client['token'])[0], 200)
        self.assertNotIn(client['token'].encode(), self.clients_file.read_bytes())
        self.assertNotIn('token', registry.list()[0])
        self.assertEqual(self.request('POST', '/v1/chats', client['token'])[0], 405)
        self.assertTrue(registry.revoke(client['id']))
        self.assertFalse(registry.revoke(client['id']))
        self.assertEqual(self.request('GET', '/v1/chats', client['token'])[0], 401)
        self.assertEqual(self.request('GET', '/v1/status', self.token)[0], 200)

    def test_client_registry_fails_closed(self):
        registry = ClientRegistry(self.clients_file)
        with self.assertRaises(ValueError):
            registry.issue('bad\nname')
        with self.assertRaises(ValueError):
            registry.revoke('../x')
        self.clients_file.write_bytes(b'not a sqlite database')
        self.assertEqual(self.request('GET', '/v1/status', 'x' * 40)[0], 401)
        self.assertEqual(self.request('GET', '/v1/status', self.token)[0], 200)

    def test_status_only_client_cannot_read_private_resources(self):
        registry = ClientRegistry(self.clients_file)
        client = registry.issue('Indicador', 'core.status')
        self.assertEqual(registry.list()[0]['scope'], 'core.status')
        self.assertEqual(self.request('GET', '/v1/status', client['token'])[0], 200)
        for path in ('/v1/chats', '/v1/tasks', '/v1/alerts', '/v1/memories?project=Karen'):
            self.assertEqual(self.request('GET', path, client['token'])[0], 403)
        self.assertTrue(registry.revoke(client['id']))
        self.assertEqual(self.request('GET', '/v1/status', client['token'])[0], 401)

    def test_legacy_client_registry_migrates_without_losing_token(self):
        old_token = 'legacy-' + 'x' * 40
        digest = hashlib.sha256(old_token.encode()).hexdigest()
        with closing(sqlite3.connect(self.clients_file)) as db, db:
            db.execute('''CREATE TABLE clients (
                id TEXT PRIMARY KEY,name TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,
                scope TEXT NOT NULL CHECK(scope='core.read'),created_at TEXT NOT NULL,
                revoked_at TEXT)''')
            db.execute('INSERT INTO clients VALUES (?,?,?,?,?,NULL)',
                       ('a' * 32, 'Anterior', digest, 'core.read', '2026-01-01'))
        registry = ClientRegistry(self.clients_file)
        self.assertEqual(self.request('GET', '/v1/chats', old_token)[0], 200)
        new = registry.issue('Indicador', 'core.status')
        self.assertEqual(self.request('GET', '/v1/chats', old_token)[0], 200)
        self.assertEqual(self.request('GET', '/v1/chats', new['token'])[0], 403)
        self.assertEqual({row['scope'] for row in registry.list()}, {'core.read', 'core.status'})

    def test_task_state_excludes_arguments_and_hashes(self):
        engine = TaskEngine({'read_demo': ToolSpec('read', lambda _args: None)}, self.tasks_file)
        task_id = engine.create([{'tool': 'read_demo', 'args': {'private': 'do not return'}}])
        status, _headers, listed = self.request('GET', '/v1/tasks', self.token)
        self.assertEqual(status, 200)
        self.assertEqual(listed['tasks'][0]['id'], task_id)
        status, _headers, detail = self.request('GET', '/v1/tasks/' + task_id, self.token)
        self.assertEqual(status, 200)
        self.assertEqual(detail['task']['steps'][0]['permission'], 'read')
        self.assertNotIn('do not return', json.dumps(detail))
        self.assertNotIn('args_hash', json.dumps(detail))
        self.assertNotIn('plan_hash', json.dumps(detail))
        self.assertEqual(self.request('GET', '/v1/tasks/' + 'f' * 32, self.token)[0], 404)

    def test_missing_task_store_is_unavailable(self):
        status, _headers, body = self.request('GET', '/v1/tasks', self.token)
        self.assertEqual(status, 503)
        self.assertEqual(body['error'], 'Karen Core no está disponible.')
        self.assertFalse(self.tasks_file.exists())

    def test_memory_read_filters_sensitive_expired_and_other_projects(self):
        store = MemoryStore(self.db_path)
        public = store.add('Karen', 'Preferencia pública', confirmed=True)
        store.add('Karen', 'Dato sensible', sensitive=True, allow_sensitive=True)
        store.add('Otro', 'Proyecto separado')
        expired = store.add('Karen', 'Dato vencido')
        with store.connect() as db:
            db.execute('UPDATE core_memories SET expires_at=? WHERE id=?',
                       ('2000-01-01T00:00:00+00:00', expired['id']))
        status, _headers, body = self.request('GET', '/v1/memories?project=Karen', self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body['contract'], 1)
        self.assertEqual([row['id'] for row in body['memories']], [public['id']])
        self.assertNotIn('Dato sensible', json.dumps(body))
        self.assertNotIn('fingerprint', json.dumps(body))
        self.assertEqual(self.request('GET', '/v1/memories?project=Otro', self.token)[2]['memories'][0]['content'],
                         'Proyecto separado')

    def test_memory_route_validates_query_and_missing_store(self):
        self.assertEqual(self.request('GET', '/v1/memories?project=Karen', self.token)[0], 503)
        self.assertEqual(self.request('GET', '/v1/memories', self.token)[0], 400)
        self.assertEqual(self.request('GET', '/v1/memories?project=Karen&extra=1', self.token)[0], 400)
        self.assertEqual(self.request('GET', '/v1/memories?project=', self.token)[0], 400)
        self.assertEqual(self.request('GET', '/v1/memories?project=Karen')[0], 401)

    def test_alert_history_is_read_only_and_freshly_persisted(self):
        engine = AlertEngine(self.alerts_file)
        engine.add_rule('pc', 'disk_free', '<', 20, label='Disco bajo')
        generated = engine.observe('pc', 'disk_free', 12.5)
        self.assertEqual(len(generated), 1)
        status, _headers, body = self.request('GET', '/v1/alerts', self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body['alerts'][0]['label'], 'Disco bajo')
        self.assertEqual(body['alerts'][0]['value'], 12.5)
        self.assertNotIn('threshold', json.dumps(body))
        self.assertEqual(self.request('POST', '/v1/alerts', self.token)[0], 405)

    def test_missing_alert_store_is_unavailable(self):
        self.assertEqual(self.request('GET', '/v1/alerts', self.token)[0], 503)
        self.assertFalse(self.alerts_file.exists())


if __name__ == '__main__':
    unittest.main()
