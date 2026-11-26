import tempfile
from pathlib import Path
import unittest

from karen_core2.handoff import Handoffs, command
from karen_core2.memory import ContextMemory


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'core.sqlite3'
        self.store = ContextMemory(self.path).base
        self.bridge = Handoffs(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def create(self, **changes):
        values = {'project': 'Karen', 'description': 'Corregir fallo sintético',
                  'acceptance': ['Prueba de regresión pasa'], 'files': ['karen_core2/runtime.py']}
        return self.bridge.create(**(values | changes))

    def test_persistence_export_and_encryption(self):
        created = self.create(context='Contexto sintético privado')
        restarted = Handoffs(ContextMemory(self.path).base)
        self.assertEqual(restarted.read(created['task']['id']), created)
        self.assertEqual(created['trust'], 'reported_data')
        with self.store.connect() as db:
            payload = db.execute('SELECT payload FROM core2_handoffs').fetchone()[0]
            self.assertNotIn('Contexto sintético privado', payload)
        self.assertIn(created['task']['id'], command(restarted, '/handoff'))

    def test_completion_needs_evidence_and_conflicting_update_is_rejected(self):
        created = self.create()
        args = {'id': created['task']['id'], 'expected_hash': created['hash'], 'status': 'complete',
                'test_results': [], 'blockers': []}
        with self.assertRaises(ValueError):
            self.bridge.update(**args)
        updated = self.bridge.update(**(args | {'test_results': ['python -m unittest qa.test_handoff: OK']}))
        self.assertEqual(updated['task']['status'], 'complete')
        self.assertEqual(updated['trust'], 'reported_data')
        with self.assertRaises(ValueError):
            self.bridge.update(**args)

    def test_credentials_traversal_and_command_injection_are_not_accepted(self):
        for changes in ({'context': 'password=synthetic'}, {'files': ['../escape.py']},
                        {'files': ['.private/settings.json']}, {'acceptance': []}, {'priority': 'urgent'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.create(**changes)
        with self.assertRaises(ValueError):
            command(self.bridge, '/handoff execute {"command":"bad"}')
        self.assertEqual(self.bridge.list(), [])


if __name__ == '__main__':
    unittest.main()
