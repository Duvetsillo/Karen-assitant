import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from iphone_routines import Routines, make_handler, initialize, prepare_legacy_migration


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = 1000
        self.calls = []
        self.path = Path(self.temp.name) / 'plans.db'
        self.r = Routines(self.path, lambda: self.calls.append(True) or [], lambda: self.clock)

    def test_prepare_cancel_and_retry_never_launch(self):
        plan = self.r.prepare()
        self.assertEqual(plan['ticket'], self.r.prepare()['ticket'])
        self.assertEqual(self.r.confirm(plan['ticket'], False)['status'], 'cancelled')
        self.r.confirm(plan['ticket'], True)
        self.assertEqual(self.calls, [])

    def test_confirmation_executes_once_even_after_restart(self):
        plan = self.r.prepare()
        self.r.confirm(plan['ticket'], True)
        restarted = Routines(self.path, lambda: self.calls.append(True) or [], lambda: self.clock)
        self.assertTrue(restarted.confirm(plan['ticket'], True)['repeated'])
        self.assertEqual(self.calls, [True])

    def test_expired_or_invalid_confirmation_does_not_launch(self):
        plan = self.r.prepare()
        with self.assertRaises(ValueError):
            self.r.confirm(plan['ticket'], 'true')
        self.clock += 301
        self.assertEqual(self.r.confirm(plan['ticket'], True)['status'], 'expired')
        self.assertEqual(self.calls, [])

    def test_concurrent_confirmation_does_not_duplicate(self):
        ticket = self.r.prepare()['ticket']
        threads = [threading.Thread(target=self.r.confirm, args=(ticket, True)) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(self.calls, [True])

    def test_http_rejects_unauthenticated_and_arbitrary_actions(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.r, 'test-key'))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        def post(path, data, key='test-key'):
            return urlopen(Request(base + path, data=json.dumps(data).encode(), headers={
                'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key}), timeout=3)
        for path, data, key, code in [('/prepare', {'routine': 'arrival_apps'}, '', 401),
                                    ('/prepare', {'routine': 'shell'}, 'test-key', 400),
                                    ('/confirm', {'ticket': 'fake', 'confirmed': True}, 'test-key', 400)]:
            with self.assertRaises(HTTPError) as error:
                post(path, data, key)
            try:
                self.assertEqual(error.exception.code, code)
            finally:
                error.exception.close()
        with post('/prepare', {'routine': 'arrival_apps'}) as response:
            plan = json.load(response)
        self.assertIn('ticket', plan)
        self.assertEqual(self.calls, [])

    def test_new_bridge_token_is_dpapi_protected(self):
        legacy = Path(self.temp.name) / 'iphone.json'
        protected = Path(self.temp.name) / 'iphone.dpapi'
        config = initialize(legacy, protected)
        self.assertFalse(legacy.exists())
        self.assertTrue(protected.is_file())
        self.assertNotIn(config['token'].encode(), protected.read_bytes())
        self.assertEqual(initialize(legacy, protected), config)

    def test_legacy_token_migrates_without_changing_source(self):
        legacy = Path(self.temp.name) / 'iphone.json'
        protected = Path(self.temp.name) / 'iphone.dpapi'
        config = {'token': 'a' * 40, 'port': 18791}
        original = json.dumps(config)
        legacy.write_text(original, encoding='utf-8')
        self.assertEqual(initialize(legacy, protected), config)
        self.assertFalse(protected.exists())
        self.assertEqual(prepare_legacy_migration(legacy, protected), config)
        self.assertEqual(legacy.read_text(encoding='utf-8'), original)
        self.assertEqual(initialize(legacy, protected), config)
        with self.assertRaises(FileExistsError):
            prepare_legacy_migration(legacy, protected)

    def test_invalid_or_damaged_config_fails_closed(self):
        legacy = Path(self.temp.name) / 'iphone.json'
        protected = Path(self.temp.name) / 'iphone.dpapi'
        legacy.write_text(json.dumps({'token': 'short', 'port': 18791}), encoding='utf-8')
        with self.assertRaises(ValueError):
            initialize(legacy, protected)
        self.assertFalse(protected.exists())
        legacy.write_text(json.dumps({'token': 'b' * 40, 'port': 18791}), encoding='utf-8')
        protected.write_bytes(b'invalid')
        with self.assertRaises((OSError, ValueError)):
            initialize(legacy, protected)


if __name__ == '__main__':
    unittest.main()
