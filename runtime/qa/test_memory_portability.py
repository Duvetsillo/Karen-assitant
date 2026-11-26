from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from karen_core2.memory import ContextMemory
from karen_core2.memory_portability import load_bundle
from memory_cli import main


class MemoryPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = ContextMemory(self.root / 'source.sqlite3')
        self.target = ContextMemory(self.root / 'target.sqlite3')
        self.one = self.source.add('Source', 'Telescopio puerto 1234', kind='user', tags=['espacio'], fact_key='telescope.port')
        self.two = self.source.add('Source', 'Telescopio puerto 4321', kind='semantic', fact_key='telescope.port')
        self.bundle = self.source.export_bundle('Source')

    def apply(self, bundle=None):
        bundle = self.bundle if bundle is None else bundle
        preview = self.target.portability.preview(bundle, 'Target')
        return self.target.portability.apply(bundle, 'Target', preview['expected_hash'])

    def test_preview_is_read_only_apply_is_pending_and_persists_source_claims(self):
        preview = self.target.portability.preview(self.bundle, 'Target')
        self.assertEqual(preview['memories'], 2)
        self.assertEqual(self.target.base.list('Target'), [])
        result = self.apply()
        restarted = ContextMemory(self.target.path)
        self.assertEqual(restarted.retrieve('Target', 'Telescopio', confirmed_only=True), [])
        pending = restarted.retrieve('Target', 'Telescopio')
        self.assertEqual({row['state'] for row in pending}, {'PENDIENTE'})
        self.assertEqual({row['source'] for row in pending}, {'imported'})
        self.assertEqual(restarted.graph('Target')['links'], [])
        receipt = restarted.portability.inspect(result['created'][0])
        self.assertEqual(receipt['trust'], 'reported_data')
        self.assertTrue(receipt['reported'][0]['claims']['versions'])
        self.assertEqual(len(restarted.export_bundle('Target')['reported']), 2)

    def test_hash_binds_document_and_target_project_and_review_binds_current_memory(self):
        preview = self.target.portability.preview(self.bundle, 'Target')
        with self.assertRaises(ValueError):
            self.target.portability.apply(self.bundle, 'Other', preview['expected_hash'])
        altered = deepcopy(self.bundle)
        altered['memories'][0]['priority'] = 9
        with self.assertRaises(ValueError):
            self.target.portability.apply(altered, 'Target', preview['expected_hash'])
        result = self.apply()
        identity = result['created'][0]
        receipt = self.target.portability.inspect(identity)
        self.target.base.edit(identity, 'Telescopio corregido localmente')
        with self.assertRaises(ValueError):
            self.target.portability.review(identity, receipt['expected_hash'])
        current = self.target.portability.inspect(identity)
        self.target.portability.review(identity, current['expected_hash'])
        self.assertEqual(len(self.target.retrieve('Target', 'Telescopio', confirmed_only=True)), 1)

    def test_duplicate_import_does_not_mutate_existing_confirmed_or_sensitive_memory(self):
        local = self.target.add('Target', self.one['content'], kind='semantic', priority=8)
        hidden = self.target.base.add('Target', self.two['content'], sensitive=True, allow_sensitive=True)
        before = self.target.export_bundle('Target')
        result = self.apply()
        self.assertEqual(result['created'], [])
        self.assertEqual(result['duplicates_skipped'], 2)
        self.assertEqual(self.target.export_bundle('Target'), before)
        self.assertEqual(self.target.base.get(local['id'])['status'], 'confirmed')
        self.assertIsNone(self.target.base.get(hidden['id']))

    def test_review_of_conflicting_facts_suppresses_automatic_confirmed_context(self):
        result = self.apply()
        for identity in result['created']:
            receipt = self.target.portability.inspect(identity)
            reviewed = self.target.portability.review(identity, receipt['expected_hash'])
        self.assertTrue(reviewed['has_conflicts'])
        self.assertEqual(self.target.retrieve('Target', 'Telescopio', confirmed_only=True), [])
        self.assertEqual(len(self.target.graph('Target')['links']), 1)

    def test_all_records_and_provenance_validate_before_any_write(self):
        cases = []
        value = deepcopy(self.bundle); value['memories'][1]['content'] = 'password=synthetic'; cases.append(value)
        value = deepcopy(self.bundle); value['memories'][1]['sensitive'] = 1; cases.append(value)
        value = deepcopy(self.bundle); value['versions'][0]['content'] = 'Authorization: Bearer synthetic'; cases.append(value)
        value = deepcopy(self.bundle); value['links'][0]['target_id'] = 'f' * 32; cases.append(value)
        value = deepcopy(self.bundle); value['links'][0]['source_id'] = []; cases.append(value)
        value = deepcopy(self.bundle); value['memories'][0]['state'] = []; cases.append(value)
        value = deepcopy(self.bundle); duplicate = deepcopy(value['memories'][0]); duplicate['id'] = 'f' * 32; value['memories'].append(duplicate); cases.append(value)
        for value in cases:
            with self.subTest(value_type=type(value)), self.assertRaises(ValueError):
                self.apply(value)
        self.assertEqual(self.target.base.list('Target'), [])
        with self.target.base.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM core_memory_versions').fetchone()[0], 0)

    def test_storage_failure_rolls_back_memories_search_versions_and_claims(self):
        import sqlite3
        with self.target.base.connect() as db:
            db.execute("CREATE TRIGGER reject_report BEFORE INSERT ON core2_memory_reported BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.apply()
        with self.target.base.connect() as db:
            for table in ('core_memories', 'core_memory_versions', 'core2_memory_search', 'core2_memory_reported'):
                self.assertEqual(db.execute('SELECT count(*) FROM ' + table).fetchone()[0], 0)

    def test_procedure_claims_cannot_forge_identity_status_or_local_execution_evidence(self):
        source = ContextMemory(self.root / 'procedure.sqlite3')
        source.add('Source', 'Procedimiento declarado', kind='procedural',
                   details={'id': 'f' * 32, 'status': 'confirmed', 'successful_runs': 500, 'verified': True})
        result = self.apply(source.export_bundle('Source'))
        identity = result['created'][0]
        procedure = self.target.procedure(identity)
        self.assertEqual(procedure['id'], identity)
        self.assertEqual(procedure['status'], 'inferred')
        self.assertEqual(procedure['successful_runs'], 0)
        self.assertFalse(procedure['verified'])
        receipt = self.target.portability.inspect(identity)
        self.target.portability.review(identity, receipt['expected_hash'])
        self.assertFalse(self.target.procedure(identity)['verified'])
        self.assertEqual(self.target.procedure(identity)['executions'], [])

    def test_retired_and_expired_records_do_not_resurrect_on_import(self):
        old = deepcopy(self.bundle)
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for row in old['memories']:
            row['expires_at'] = past
        result = self.apply(old)
        self.assertEqual(self.target.retrieve('Target'), [])
        for identity in result['created']:
            receipt = self.target.portability.inspect(identity)
            with self.assertRaises(ValueError):
                self.target.portability.review(identity, receipt['expected_hash'])

    def test_round_trip_preserves_flat_reported_history_without_promoting_it(self):
        self.apply()
        other = ContextMemory(self.root / 'other.sqlite3')
        bundle = self.target.export_bundle('Target')
        preview = other.portability.preview(bundle, 'Other')
        other.portability.apply(bundle, 'Other', preview['expected_hash'])
        exported = other.export_bundle('Other')
        self.assertEqual(len(exported['reported']), 4)
        self.assertEqual(other.retrieve('Other', confirmed_only=True), [])
        original_ids = {item['claims']['memory']['id'] for item in exported['reported']}
        self.assertIn(self.one['id'], original_ids)
        self.assertIn(self.two['id'], original_ids)

    def test_cli_preview_apply_and_explicit_review_and_strict_local_json(self):
        path = self.root / 'bundle.json'
        path.write_text(json.dumps(self.bundle), encoding='utf-8')
        def call(*args):
            output = StringIO()
            with redirect_stdout(output):
                main(['--db', str(self.target.path), *args])
            return json.loads(output.getvalue())
        preview = call('import-engine', 'Target', str(path))
        result = call('import-engine', 'Target', str(path), '--apply', '--expected-hash', preview['expected_hash'])
        receipt = call('inspect-import', result['created'][0])
        reviewed = call('review-import', result['created'][0], '--expected-hash', receipt['expected_hash'])
        self.assertEqual(reviewed['basis'], 'explicit_user_review')
        self.assertEqual(self.target.retrieve('Target', confirmed_only=True)[0]['id'], result['created'][0])
        path.write_text('{"contract":"memory-engine-1","contract":"bad"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_bundle(path)
        with self.assertRaises(ValueError):
            load_bundle('//untrusted/share/bundle.json')


if __name__ == '__main__':
    unittest.main()
