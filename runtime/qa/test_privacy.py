import json
from pathlib import Path
import tempfile
import unittest

from karen_core2.privacy import public
from karen_memory import MemoryStore


class PrivacyTests(unittest.TestCase):
    def test_redacts_complete_authorization_bearer_and_nested_private_keys(self):
        data = {'message': 'HTTP Authorization: Bearer synthetic.payload.value',
                'nested': ['Bearer synthetic.bare.value', {'refresh_token': 'synthetic-refresh',
                                                         'private_key': 'synthetic-key'}]}
        rendered = json.dumps(public(data))
        for secret in ('synthetic.payload.value', 'synthetic.bare.value', 'synthetic-refresh', 'synthetic-key'):
            self.assertNotIn(secret, rendered)
        self.assertIn('[redactado]', rendered)

    def test_spanish_password_assignments_are_rejected_before_any_memory_write(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / 'core.sqlite3')
            for text in ('contraseña=synthetic-password', 'contrasena: synthetic-password',
                         'refresh_token=synthetic-refresh', 'Authorization: Bearer synthetic-token'):
                with self.subTest(text=text), self.assertRaises(ValueError):
                    store.add('Karen', text)
                self.assertNotIn('synthetic', json.dumps(public(text)))
            self.assertEqual(store.list('Karen'), [])
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM core_memory_versions').fetchone()[0], 0)

    def test_private_key_pem_payload_is_fully_redacted(self):
        self.assertEqual(public('-----BEGIN PRIVATE KEY-----\nsynthetic-key-payload\n-----END PRIVATE KEY-----'), '[redactado]')


if __name__ == '__main__':
    unittest.main()
