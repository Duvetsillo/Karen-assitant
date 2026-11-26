"""Memory contract and privacy regressions, using temporary SQLite only."""
import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from karen_core2.memory import ContextMemory, KINDS
from karen_memory import MemoryStore
from karen_core2.runtime import CoreRuntime
from qa.test_core2_mobile import FakeModels
from karen_core2.events import EventBus


class MemoryEngineTests(unittest.TestCase):
    def test_memory_events_are_after_commit_and_contain_no_content(self):
        with tempfile.TemporaryDirectory() as folder:
            memory = ContextMemory(Path(folder) / 'core.sqlite3')
            bus = EventBus()
            memory.events = bus
            committed = []
            bus.subscribe('memory.created', lambda event: committed.append(memory.base.get(event['entity_id'])['id']))
            row = memory.add('Karen', 'Dato sintético privado', fact_key='synthetic.key')
            memory.add('Karen', 'Dato sintético privado', fact_key='synthetic.key')
            memory.add('Karen', 'Dato diferente', fact_key='synthetic.key')
            events = bus.status()['recent']
            self.assertEqual(committed[0], row['id'])
            self.assertEqual([event['topic'] for event in events],
                             ['memory.created', 'memory.updated', 'memory.created', 'memory.conflict'])
            self.assertNotIn('Dato', json.dumps(events))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'memory.sqlite3'
        self.engine = ContextMemory(self.path)

    def test_categories_and_independent_clients_keep_memories_after_model_switch(self):
        for kind in KINDS - {'project'}:
            self.engine.add('Homelab', 'Jellyfin ' + kind, kind=kind, tags=['servidor'])
        first = CoreRuntime(archive_path=self.path, task_path=Path(self.temp.name) / 'tasks.db', models=FakeModels())
        for model in ('qwen', 'gemma', 'llama'):
            first.chat('Jellyfin', project='Homelab', preferred=model)
            second = ContextMemory(self.path)
            self.assertEqual(len(second.retrieve('Homelab', 'Jellyfin', limit=20)), len(KINDS - {'project'}))
            self.assertEqual(second.retrieve('Otro'), [])

    def test_contradictions_are_explicit_and_never_injected_as_confirmed_context(self):
        one = self.engine.add('Homelab', 'Jellyfin puerto 8096', fact_key='jellyfin.port')
        two = self.engine.add('Homelab', 'Jellyfin puerto 9000', fact_key='jellyfin.port')
        result = self.engine.consolidate('Homelab')
        self.assertTrue(result['requires_review'])
        self.assertEqual(len(result['contradictions']), 1)
        self.assertEqual(self.engine.retrieve('Homelab', 'Jellyfin', confirmed_only=True), [])
        self.assertEqual(len(self.engine.base.list('Homelab')), 2)
        self.engine.base.delete(two['id'])
        self.assertEqual(self.engine.retrieve('Homelab', confirmed_only=True)[0]['id'], one['id'])

    def test_versions_survive_legacy_edits_and_supersession(self):
        one = self.engine.add('Homelab', 'Puerto 8096', kind='temporal')
        legacy = MemoryStore(self.path)
        legacy.edit(one['id'], 'Puerto 9000')
        self.assertEqual([r['content'] for r in self.engine.history(one['id'])], ['Puerto 8096', 'Puerto 9000'])
        two = self.engine.add('Homelab', 'Puerto 8097', kind='temporal', supersedes=one['id'])
        self.assertIsNone(legacy.get(one['id']))
        self.assertEqual(self.engine.history(one['id'])[-1]['expires_at'], self.engine.history(one['id'])[-1]['recorded_at'])
        self.assertEqual(self.engine.retrieve('Homelab')[0]['id'], two['id'])

    def test_selective_deletion_purges_versions_links_and_procedure_evidence(self):
        plan = {'id': 'a' * 32, 'status': 'completed', 'goal': 'Leer CPU',
                'steps': [{'tool': 'cpu', 'status': 'completed', 'permission': 'read', 'result': {'value': 12}}]}
        row = self.engine.record_procedure(plan)
        other = self.engine.add('Karen', 'Equipo local')
        self.engine.relate(row['id'], other['id'], 'uses')
        self.engine.base.delete(row['id'])
        self.assertEqual(self.engine.history(row['id']), [])
        self.assertIsNone(self.engine.procedure(row['id']))
        self.assertEqual(self.engine.graph('Karen')['links'], [])
        with self.engine.base.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM core2_procedure_runs').fetchone()[0], 0)

    def test_procedure_requires_evidence_and_execution_count_is_idempotent(self):
        plan = {'id': 'a' * 32, 'status': 'completed', 'goal': 'Leer CPU',
                'steps': [{'tool': 'cpu', 'status': 'completed', 'permission': 'read', 'result': {'value': 12}}]}
        row = self.engine.record_procedure(plan)
        self.engine.record_procedure(plan)
        self.assertEqual(self.engine.procedure(row['id'])['successful_runs'], 1)
        plan['id'] = 'b' * 32
        self.engine.record_procedure(plan)
        detail = self.engine.procedure(row['id'])
        self.assertEqual(detail['successful_runs'], 2)
        self.assertEqual(detail['tools'], ['cpu'])
        self.assertNotIn('"value"', detail['executions'][0]['evidence'])
        del plan['steps'][0]['result']
        with self.assertRaises(ValueError):
            self.engine.record_procedure(plan)

    def test_pending_and_stale_never_leak_to_legacy_confirmed_context(self):
        for state in ('PENDIENTE', 'INFERIDO', 'DESACTUALIZADO'):
            row = self.engine.add('Karen', 'Dato ' + state, state=state)
            self.assertEqual(self.engine.base.get(row['id'])['status'], 'inferred')
        self.assertEqual(self.engine.retrieve('Karen', confirmed_only=True), [])
        self.assertEqual(len(self.engine.consolidate('Karen')['pending']), 2)

    def test_duplicate_cannot_promote_pending_without_review(self):
        row = self.engine.add('Karen', 'Dato sin confirmar', state='PENDIENTE')
        with self.assertRaises(ValueError):
            self.engine.add('Karen', 'Dato sin confirmar', state='VERIFICADO')
        self.assertEqual(self.engine.base.get(row['id'])['status'], 'inferred')

    def test_sensitive_promotion_hides_all_versions(self):
        row = self.engine.add('Karen', 'Texto privado')
        self.engine.base.add('Karen', 'Texto privado', sensitive=True, allow_sensitive=True)
        self.assertEqual(self.engine.history(row['id']), [])
        self.assertEqual(self.engine.graph('Karen')['nodes'], [])

    def test_secret_metadata_rejected_and_confidence_validated(self):
        for options in ({'tags': ['access_token']}, {'details': {'password': 'abc'}}, {'confidence': float('nan')}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.engine.add('Karen', 'Dato', **options)
        self.assertEqual(self.engine.base.list('Karen'), [])

    def test_export_backup_and_temporal_filters_preserve_metadata(self):
        from contextlib import closing
        import sqlite3
        row = self.engine.add('Homelab', 'Servicio anterior', kind='temporal', tags=['config'])
        self.engine.base.edit(row['id'], 'Servicio actual')
        secret = self.engine.base.add('Homelab', 'Privado', sensitive=True, allow_sensitive=True)
        bundle = self.engine.export_bundle('Homelab')
        self.assertEqual(len(bundle['versions']), 2)
        self.assertEqual(json.loads(bundle['memories'][0]['tags']), ['config'])
        self.assertNotIn(secret['id'], json.dumps(bundle))
        self.assertEqual(len(self.engine.timeline('Homelab', kind='temporal')), 2)
        self.assertEqual(self.engine.timeline('Homelab', since='2099-01-01T00:00:00+00:00'), [])
        with self.assertRaises(ValueError):
            self.engine.timeline('Homelab', since='2026-11-20')
        backup = Path(self.temp.name) / 'backup.sqlite3'
        with self.engine.base.connect() as source, closing(sqlite3.connect(backup)) as target:
            source.backup(target)
            self.assertEqual(target.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        recovered = ContextMemory(backup)
        self.assertEqual(recovered.export_bundle('Homelab'), bundle)

    def test_metadata_storage_failure_rolls_back_memory_and_journal(self):
        import sqlite3
        with self.engine.base.connect() as db:
            db.execute("CREATE TRIGGER reject_metadata BEFORE INSERT ON core2_memory_details BEGIN SELECT RAISE(ABORT,'storage failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.engine.add('Karen', 'No debe persistir parcialmente')
        self.assertEqual(self.engine.base.list('Karen'), [])
        with self.engine.base.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM core_memory_versions').fetchone()[0], 0)

    def test_fts_finds_relevant_memory_older_than_the_recent_200_limit(self):
        old = self.engine.add('Karen', 'Pléyades observadas con telescopio.', kind='episodic')
        for index in range(205):
            self.engine.base.add('Karen', 'Ruido sintético número ' + str(index))
        found = self.engine.retrieve('Karen', 'Pleyades OR NOT "*', confirmed_only=True)
        self.assertEqual([row['id'] for row in found], [old['id']])
        self.assertEqual(found[0]['access_count'], 1)
        restarted = ContextMemory(self.path)
        again = restarted.retrieve('Karen', 'Pléyades')[0]
        self.assertEqual(again['access_count'], 2)
        self.assertIsNotNone(datetime.fromisoformat(again['last_access_at']).utcoffset())
        bundle = restarted.export_bundle('Karen')
        exported = next(row for row in bundle['memories'] if row['id'] == old['id'])
        self.assertEqual(exported['access_count'], 2)

    def test_fts_updates_from_legacy_edits_sensitivity_and_delete_without_reindex(self):
        old = self.engine.base.add('Karen', 'Saturno anterior')
        self.assertEqual(self.engine.retrieve('Karen', 'Saturno')[0]['id'], old['id'])
        self.engine.base.edit(old['id'], 'Neptuno corregido')
        self.assertEqual(self.engine.retrieve('Karen', 'Saturno'), [])
        self.assertEqual(self.engine.retrieve('Karen', 'Neptuno')[0]['id'], old['id'])
        self.engine.base.add('Karen', 'Neptuno corregido', sensitive=True, allow_sensitive=True)
        self.assertEqual(self.engine.retrieve('Karen', 'Neptuno'), [])
        with self.engine.base.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM core2_memory_search WHERE memory_id=?', (old['id'],)).fetchone()[0], 0)
        self.engine.base.delete(old['id'], allow_sensitive=True)
        with self.engine.base.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM core2_memory_access WHERE memory_id=?', (old['id'],)).fetchone()[0], 0)

    def test_new_memory_types_persist_and_credentials_are_rejected_by_legacy_store(self):
        for kind in ('user', 'autobiographical', 'prospective'):
            self.engine.add('Karen', 'Dato específico ' + kind, kind=kind)
        restored = ContextMemory(self.path)
        self.assertEqual({row['kind'] for row in restored.retrieve('Karen', 'específico')}, {'user', 'autobiographical', 'prospective'})
        for value in ('password=synthetic', '-----BEGIN PRIVATE KEY-----'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                restored.base.add('Karen', value, sensitive=True, allow_sensitive=True)
        self.assertEqual(restored.reindex()['indexed'], 3)

    def test_existing_memory_cli_exposes_user_category_and_rebuildable_index(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from memory_cli import main
        output = StringIO()
        with redirect_stdout(output):
            main(['--db', str(self.path), 'add', 'Karen', 'Preferencia sintética', '--kind', 'user'])
        identity = json.loads(output.getvalue())['id']
        self.assertEqual(self.engine.retrieve('Karen', 'Preferencia')[0]['id'], identity)
        output = StringIO()
        with redirect_stdout(output):
            main(['--db', str(self.path), 'reindex'])
        self.assertEqual(json.loads(output.getvalue())['indexed'], 1)


if __name__ == '__main__':
    unittest.main()
