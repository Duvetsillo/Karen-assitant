import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from config import KarenConfig
from conversations import Conversations
from mobile_server import MobileApp, make_handler


class MobileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.archive = Conversations(Path(self.temp.name) / 'core.sqlite3')
        self.chat = self.archive.create()
        self.app = MobileApp(self.archive, KarenConfig(), 'a' * 43,
                             'https://test.tail.example', ask=lambda chat, msg: 'Respuesta: ' + msg)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.app))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        self.cookie = 'karen_mobile=' + self.app.session()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, auth=True, origin=None, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        headers = {'Origin': origin or self.origin}
        if auth:
            headers['Cookie'] = self.cookie
        if host:
            headers['Host'] = host
        if data is not None:
            headers['Content-Type'] = 'application/json'
        connection.request('GET' if data is None else 'POST', path,
                           json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_assets_public_and_private_data_requires_auth(self):
        for path in ('/', '/app.js', '/style.css', '/manifest.webmanifest', '/sw.js',
                     '/icon.svg', '/icon-192.png', '/apple-touch-icon.png'):
            self.assertEqual(self.request(path, auth=False)[0], 200, path)
        for path in ('/api/session', '/api/v1/chats', '/api/v1/memories?project=Karen'):
            self.assertEqual(self.request(path, auth=False)[0], 401)

    def test_login_cookie_and_wrong_code(self):
        self.assertEqual(self.request('/api/login', {'code': 'wrong'}, auth=False)[0], 401)
        status, headers, _ = self.request('/api/login', {'code': self.app.secret}, auth=False,
                                          origin='https://test.tail.example', host='test.tail.example')
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('Secure', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertTrue(self.app.authenticated(headers['Set-Cookie']))

    def test_bad_host_and_cross_origin_cannot_read_or_write(self):
        self.assertEqual(self.request('/api/v1/chats', host='evil.example')[0], 403)
        self.assertEqual(self.request('/api/chats', {}, origin='https://evil.example')[0], 403)
        self.assertEqual(self.request('/api/login', {'code': self.app.secret}, origin='null')[0], 403)

    def test_optional_direct_tailnet_access_keeps_host_and_origin_checks(self):
        from mobile_server import validate_tailnet_origin
        direct = 'http://100.73.94.38:18795'
        self.app.origins.add(validate_tailnet_origin(direct))
        status, headers, _ = self.request('/api/login', {'code': self.app.secret},
                                          origin=direct, host='100.73.94.38:18795')
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertEqual(self.request('/api/chats', {}, origin='http://100.73.94.39:18795',
                                      host='100.73.94.38:18795')[0], 403)
        for invalid in ('http://192.168.1.1:18795', 'http://8.8.8.8:18795',
                        'http://100.73.94.38:18795/path', 'http://100.73.94.38',
                        'http://100.73.94.38:bad'):
            with self.subTest(origin=invalid), self.assertRaises(ValueError):
                validate_tailnet_origin(invalid)

    def test_login_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.request('/api/login', {'code': 'wrong'}, auth=False)[0], 401)
        self.assertEqual(self.request('/api/login', {'code': self.app.secret}, auth=False)[0], 429)

    def test_chat_creation_does_not_change_active_desktop_chat(self):
        status, _, body = self.request('/api/chats', {})
        self.assertEqual(status, 201)
        self.assertNotEqual(json.loads(body)['id'], self.chat)
        self.assertEqual(self.archive.current(), self.chat)

    def test_message_persisted_and_readable_from_shared_archive(self):
        status, _, body = self.request('/api/message', {'chat_id': self.chat, 'message': 'Hola'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['answer'], 'Respuesta: Hola')
        self.assertEqual(self.archive.exchanges(self.chat), [('Hola', 'Respuesta: Hola', 1)])
        status, headers, body = self.request('/api/v1/chats/' + self.chat + '/exchanges')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['exchanges'][0]['prompt'], 'Hola')
        self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_commands_and_invalid_messages_never_reach_model(self):
        self.app.ask = lambda *args: self.fail('El modelo no debe recibir esta petición')
        for message in ('/casa encender luz', '', 'x' * 8001, 42):
            self.assertEqual(self.request('/api/message', {'chat_id': self.chat, 'message': message})[0], 400)
        self.assertEqual(self.request('/api/message', {'chat_id': 'bad', 'message': 'Hola'})[0], 400)
        self.assertEqual(self.archive.exchanges(self.chat), [])

    def test_missing_chat_and_busy_generation(self):
        self.assertEqual(self.request('/api/message', {'chat_id': '0' * 32, 'message': 'Hola'})[0], 404)
        self.app.generation.acquire()
        try:
            self.assertEqual(self.request('/api/message', {'chat_id': self.chat, 'message': 'Hola'})[0], 409)
        finally:
            self.app.generation.release()

    def test_failed_model_does_not_persist_turn(self):
        def fail(*args):
            raise ValueError('Respuesta inválida')
        self.app.ask = fail
        self.assertEqual(self.request('/api/message', {'chat_id': self.chat, 'message': 'Hola'})[0], 503)
        self.assertEqual(self.archive.exchanges(self.chat), [])
        self.assertTrue(self.app.generation.acquire(blocking=False))
        self.app.generation.release()

    def test_forged_expired_and_rotated_sessions(self):
        from unittest.mock import patch
        with patch('mobile_server.time.time', return_value=1):
            expired = 'karen_mobile=' + self.app.session()
        self.assertFalse(self.app.authenticated(expired))
        self.assertFalse(self.app.authenticated(self.cookie + 'bad'))
        self.assertFalse(self.app.authenticated('karen_mobile=bad'))
        self.app.secret = 'b' * 43
        self.assertFalse(self.app.authenticated(self.cookie))

    def test_provider_contract_rejects_malformed_or_analysis_only_answers(self):
        from unittest.mock import MagicMock, patch
        for payload in ([], {'message': None}, {'message': []},
                        {'message': {'content': '<think>sin respuesta final'}}):
            response = MagicMock()
            response.__enter__.return_value = response
            response.json.return_value = payload
            with self.subTest(payload=payload), patch('mobile_server.requests.post', return_value=response):
                with self.assertRaises(ValueError):
                    self.app.generate(self.chat, 'Hola')

    def test_query_validation_and_logout(self):
        self.assertEqual(self.request('/api/v1/memories?project=Karen&extra=1')[0], 400)
        status, headers, _ = self.request('/api/logout', {})
        self.assertEqual(status, 200)
        self.assertIn('Max-Age=0', headers['Set-Cookie'])


if __name__ == '__main__':
    unittest.main()
