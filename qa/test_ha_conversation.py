import http.client
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from qa import test_mobile_server as mobile_tests
from ha_conversation import provision


class HAConversationTests(unittest.TestCase):
    tearDown = mobile_tests.MobileTests.tearDown
    request = mobile_tests.MobileTests.request

    def setUp(self):
        mobile_tests.MobileTests.setUp(self)
        self.path = Path(self.temp.name) / 'ha.dpapi'
        self.key = provision(self.path)
        self.app.ha_key_path = self.path
        self.app.core2 = Mock()
        self.app.core2.chat.side_effect = lambda text, history, **kw: 'Karen: ' + text

    def ha(self, path='/api/ha/conversation', data=None, key=None, origin=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        headers = {'Authorization': 'Bearer ' + (self.key if key is None else key)}
        if origin:
            headers['Origin'] = origin
        if data is not None:
            headers['Content-Type'] = 'application/json'
        connection.request('GET' if data is None else 'POST', path, json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_scoped_secret_encrypted_and_reloaded_after_revocation(self):
        self.assertNotIn(self.key, self.path.read_text())
        self.assertEqual(self.ha('/api/ha/status')[0], 200)
        self.assertEqual(self.ha('/api/ha/status', key='wrong')[0], 401)
        self.path.unlink()
        self.assertEqual(self.ha('/api/ha/status')[0], 401)

    def test_browser_origin_and_mobile_cookie_never_grant_bridge_access(self):
        self.assertEqual(self.ha(data={'text': 'Hola'}, origin=self.origin)[0], 403)
        self.assertEqual(self.request('/api/ha/conversation', {'text': 'Hola'})[0], 403)
        self.assertEqual(self.ha('/api/ha/plans', data={})[0], 404)
        self.assertEqual(self.ha('/api/core2/plans')[0], 401)
        self.app.core2.chat.assert_not_called()

    def test_history_shared_context_persisted_and_desktop_selection_preserved(self):
        self.archive.activate(self.chat)
        body = {'text': 'Recuerda el contexto sintético', 'conversation_id': 'ha-session', 'user_id': 'owner'}
        self.assertEqual(self.ha(data=body)[0], 200)
        self.assertEqual(self.ha(data={**body, 'text': 'Continúa'})[0], 200)
        self.assertEqual(self.archive.current(), self.chat)
        history = self.app.core2.chat.call_args.args[1]
        self.assertTrue(any('contexto sintético' in item['content'] for item in history))
        with self.archive.connect() as db:
            chat = db.execute('SELECT chat_id FROM core_ha_conversations').fetchone()[0]
        self.assertEqual(len(self.archive.exchanges(chat)), 2)

    def test_ha_users_do_not_share_private_conversation_ids(self):
        for user in ('one', 'two'):
            self.assertEqual(self.ha(data={'text': user, 'conversation_id': 'same', 'user_id': user})[0], 200)
        self.assertEqual(self.app.core2.chat.call_args.args[1], [])
        with self.archive.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(DISTINCT chat_id) FROM core_ha_conversations').fetchone()[0], 2)

    def test_invalid_queries_and_model_failure_never_store_success(self):
        for data in ({'text': ''}, {'text': 'a' * 4001}, {'text': 'Hola', 'execute': True}, {'text': 'Hola', 'conversation_id': '../../chat'}):
            self.assertEqual(self.ha(data=data)[0], 400)
        self.app.core2.chat.side_effect = OSError('private diagnostic must not escape')
        status, data = self.ha(data={'text': 'Hola'})
        self.assertEqual(status, 503)
        self.assertNotIn('private diagnostic', json.dumps(data))
        with self.archive.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM exchanges').fetchone()[0], 0)

    def test_conversation_never_calls_plan_execution(self):
        self.assertEqual(self.ha(data={'text': '/ejecutar ' + 'a' * 32})[0], 200)
        self.app.core2.run.assert_not_called()
        self.app.core2.command.assert_not_called()
