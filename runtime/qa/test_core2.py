import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from karen_tasks import ToolSpec
from karen_core2.skills import Skill, SkillRegistry, validate_schema
from karen_core2.planning import Plans
from karen_core2.memory import ContextMemory
from karen_core2.models import LocalModels, local_endpoint, local_model
from karen_core2.vision import Vision
from karen_core2.diagnostics import Diagnostics
from karen_core2.runtime import effective_local_config, CoreRuntime
from config import KarenConfig


EMPTY = {'type': 'object', 'properties': {}, 'additionalProperties': False}


def registry(handler=None, permission='read', verify=None):
    result = SkillRegistry()
    result.register(Skill('probe', 'Probe', 'Synthetic measurement', 'SYSTEM', permission, EMPTY,
                          ToolSpec(permission, handler or (lambda args, stop: {'value': 1}),
                                   lambda args: validate_schema(EMPTY, args), verify or (lambda args, result: result == {'value': 1}), 2)))
    return result


def plan(goal='Synthetic task', count=2):
    return {'goal': goal, 'steps': [{'id': f's{i}', 'label': 'Read synthetic evidence', 'tool': 'probe', 'args': {},
            'depends': [f's{i-1}'] if i else []} for i in range(count)]}


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'tasks.sqlite3'
        self.plans = Plans(registry(), self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_plan_is_persisted_encrypted_and_reused_by_key(self):
        task = self.plans.create(plan('Private synthetic goal'), 'same-key')
        self.assertEqual(self.plans.create(plan('Private synthetic goal'), 'same-key')['id'], task['id'])
        with closing(sqlite3.connect(self.path)) as db:
            envelope = db.execute('SELECT envelope FROM core2_plans').fetchone()[0]
            self.assertNotIn('Private synthetic goal', envelope)
        with self.assertRaises(ValueError):
            self.plans.create(plan('Other goal'), 'same-key')

    def test_dependency_sort_and_cycle_rejection(self):
        raw = plan()
        raw['steps'].reverse()
        self.assertEqual(self.plans.validate(raw)['steps'][0]['id'], 's0')
        raw['steps'][1]['depends'] = ['s1']
        with self.assertRaises(ValueError):
            self.plans.validate(raw)

    def test_unknown_tools_permissions_and_arguments_rejected(self):
        for mutation in ('tool', 'permission', 'args'):
            raw = plan()
            if mutation == 'tool': raw['steps'][0]['tool'] = 'exec'
            elif mutation == 'permission': raw['steps'][0]['permission'] = 'read'
            else: raw['steps'][0]['args'] = {'command': 'anything'}
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.plans.create(raw)

    def test_results_verified_persisted_and_no_replay(self):
        task = self.plans.create(plan())
        result = self.plans.run(task['id'])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['steps'][1]['result'], {'value': 1})
        recovered = Plans(registry(), self.path)
        self.assertEqual(recovered.run(task['id'])['steps'][0]['attempts'], 1)
        self.assertEqual(len([r for r in recovered.audit(task['id']) if r['state'] == 'verified']), 2)

    def test_failed_reads_retry_only_twice_and_writes_never_retry(self):
        calls = []
        def fail(args, stop):
            calls.append(1)
            raise OSError()
        for permission, expected in [('read', 2), ('sensitive', 1)]:
            target = Plans(registry(fail, permission), Path(self.temp.name) / (permission + '.sqlite3'))
            task = target.create(plan(count=1))
            calls.clear()
            result = target.run(task['id'], approve=lambda _: True)
            self.assertEqual(len(calls), expected)
            self.assertEqual(result['status'], 'failed' if permission == 'read' else 'uncertain')

    def test_mutation_needs_exact_interactive_approval(self):
        target = Plans(registry(permission='sensitive'), Path(self.temp.name) / 'write.sqlite3')
        task = target.create(plan(count=1))
        self.assertEqual(target.run(task['id'])['status'], 'awaiting_approval')
        self.assertEqual(target.run(task['id'], approve=lambda _: True, actor='test-owner')['status'], 'completed')
        record = next(row for row in target.audit(task['id']) if row['state'] == 'approved')
        self.assertEqual(record['actor'], 'test-owner')

    def test_recovery_resumes_reads_without_repeating_completed_dependencies(self):
        task = self.plans.create(plan())
        self.plans.run(task['id'])
        with self.plans.engine._connect() as db:
            db.execute("UPDATE core2_plans SET status='running' WHERE id=?", (task['id'],))
            db.execute("UPDATE core2_plan_steps SET status='running',evidence=NULL WHERE plan_id=? AND step_id='s1'", (task['id'],))
        restarted = Plans(registry(), self.path)
        self.assertEqual(restarted.inspect(task['id'])['status'], 'interrupted')
        self.assertEqual(restarted.run(task['id'])['status'], 'interrupted')
        result = restarted.run(task['id'], resume=True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['steps'][0]['attempts'], 1)
        self.assertEqual(result['steps'][1]['attempts'], 2)

    def test_crashed_write_stays_uncertain(self):
        target = Plans(registry(permission='sensitive'), Path(self.temp.name) / 'crash.sqlite3')
        task = target.create(plan(count=1))
        with target.engine._connect() as db:
            db.execute("UPDATE core2_plans SET status='running'")
            db.execute("UPDATE core2_plan_steps SET status='running'")
        restarted = Plans(registry(permission='sensitive'), target.path)
        self.assertEqual(restarted.run(task['id'], resume=True, approve=lambda _: True)['status'], 'uncertain')

    def test_cancel_stops_cooperative_work_and_does_not_run_dependent_step(self):
        started = threading.Event()
        def wait(args, stop):
            started.set()
            if stop.wait(2): raise InterruptedError()
            return {'value': 1}
        target = Plans(registry(wait), Path(self.temp.name) / 'cancel.sqlite3')
        task = target.create(plan())
        worker = threading.Thread(target=target.run, args=(task['id'],))
        worker.start()
        self.assertTrue(started.wait(2))
        target.cancel(task['id'])
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(target.inspect(task['id'])['status'], 'canceled')
        self.assertEqual(target.inspect(task['id'])['steps'][1]['attempts'], 0)

    def test_failed_verification_never_reports_success(self):
        target = Plans(registry(verify=lambda a, r: False), Path(self.temp.name) / 'verify.sqlite3')
        task = target.create(plan(count=1))
        self.assertEqual(target.run(task['id'])['status'], 'failed')

    def test_public_api_never_returns_private_arguments_or_evidence(self):
        from karen_core2.api import read_plans
        task = self.plans.create(plan())
        self.plans.run(task['id'])
        public = read_plans(self.path, '/v1/plans/' + task['id'])
        text = json.dumps(public)
        self.assertNotIn('envelope', text)
        self.assertNotIn('evidence', text)
        self.assertNotIn('arguments', text)
        self.assertNotIn('result', text)
        self.assertEqual(public['plan']['steps'][0]['status'], 'completed')

    def test_destructive_operation_requires_plan_and_step_bound_confirmation(self):
        target = Plans(registry(permission='destructive'), Path(self.temp.name) / 'destructive.sqlite3')
        task = target.create(plan(count=1))
        self.assertEqual(target.run(task['id'], approve=lambda _: True)['status'], 'denied')
        other = target.create(plan('Second explicit operation', count=1))
        decision = lambda request: {'confirmed_plan': request['plan_id'], 'confirmed_step': request['step_id']}
        self.assertEqual(target.run(other['id'], approve=decision)['status'], 'completed')

    def test_unknown_extension_version_rejected(self):
        with self.plans.engine._connect() as db:
            db.execute("UPDATE core2_meta SET value='999' WHERE key='schema_version'")
        with self.assertRaises(ValueError): Plans(registry(), self.path)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = ContextMemory(Path(self.temp.name) / 'core.sqlite3')
    def tearDown(self): self.temp.cleanup()

    def test_typed_dedup_hypotheses_and_project_isolation(self):
        first = self.memory.add('Karen', 'CPU usa modo local', kind='semantic')
        second = self.memory.add('Karen', ' CPU   USA modo local ', kind='semantic')
        self.assertEqual(first['id'], second['id'])
        self.memory.add('Karen', 'CPU podría tener carga alta', status='hypothesis')
        self.memory.add('Otro', 'CPU privada de otro proyecto')
        rows = self.memory.retrieve('Karen', 'CPU', confirmed_only=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'semantic')

    def test_superseded_information_expires_for_legacy_clients(self):
        first = self.memory.add('Karen', 'Modelo anterior')
        self.memory.add('Karen', 'Modelo vigente', supersedes=first['id'])
        self.assertIsNone(self.memory.base.get(first['id']))
        self.assertEqual(len(self.memory.base.list('Karen')), 1)

    def test_relationships_do_not_cross_projects_and_credentials_not_stored(self):
        first = self.memory.add('Karen', 'Hecho confirmado')
        other = self.memory.add('Otro', 'Otro hecho')
        with self.assertRaises(ValueError): self.memory.relate(first['id'], other['id'])
        with self.assertRaises(ValueError): self.memory.add('Karen', 'password=secreto')

    def test_only_verified_procedures_are_remembered(self):
        with self.assertRaises(ValueError): self.memory.record_procedure({'status': 'pending'})
        result = self.memory.record_procedure({'status': 'completed', 'goal': 'Diagnóstico sintético',
            'id': 'a' * 32, 'steps': [{'tool': 'cpu_sample', 'status': 'completed', 'result': {'cpu_percent': 12}}]})
        self.assertEqual(result['kind'], 'procedural')


class ModelPolicyTests(unittest.TestCase):
    def test_only_literal_loopback_and_noncloud_models(self):
        for value in ('https://example.com', 'http://192.168.1.2:11434', 'http://127.0.0.1.evil:11434',
                      'http://user@localhost:11434', 'http://localhost:11434/api'):
            with self.subTest(value=value), self.assertRaises(ValueError): local_endpoint(value)
        self.assertEqual(local_endpoint('http://127.0.0.1:11434'), 'http://127.0.0.1:11434')
        for name in ('beam:cloud', 'gemma4:31b-cloud', 'ollama/cloud/model'):
            self.assertFalse(local_model(name))
        self.assertFalse(local_model('safe:tag', {'remote_host': 'https://remote'}))

    def test_routing_capability_budget_and_task_fit(self):
        models = LocalModels(probe=lambda: {'ram_available_bytes': 10 * 1024**3})
        models.discover = lambda: [
            {'name': 'gemma3:1b', 'size': 800000000, 'capabilities': ['completion']},
            {'name': 'qwen2.5-coder:3b', 'size': 1900000000, 'capabilities': ['completion', 'tools']},
            {'name': 'qwen3.5:4b', 'size': 3300000000, 'capabilities': ['completion', 'vision', 'tools']},
            {'name': 'too-large', 'size': 12000000000, 'capabilities': ['completion', 'vision']}]
        self.assertEqual(models.rank()[0]['name'], 'gemma3:1b')
        self.assertEqual(models.rank('coding')[0]['name'], 'qwen2.5-coder:3b')
        self.assertEqual(models.rank('vision')[0]['name'], 'qwen3.5:4b')
        self.assertTrue(all('vision' in m['capabilities'] for m in models.rank('vision')))

    def test_local_runtime_does_not_mutate_saved_settings(self):
        config = KarenConfig(server='http://192.168.1.2:11434', model='beam:cloud', tts_engine='edge')
        result = effective_local_config(config)
        self.assertEqual(config.model, 'beam:cloud')
        self.assertEqual(result.server, 'http://127.0.0.1:11434')
        self.assertEqual(result.tts_engine, 'qwen3')
        self.assertEqual(result.model, 'gemma3:1b')


class VisionTests(unittest.TestCase):
    def test_pause_prevents_capture_and_missing_model_never_captures(self):
        class Models:
            catalog = []
            def rank(self, *args): return []
        calls = []
        vision = Vision(Models(), capture=lambda scope: calls.append(scope))
        with self.assertRaises(PermissionError): vision.capture()
        vision.pause(False)
        with self.assertRaises(ValueError): vision.analyze()
        self.assertEqual(calls, [])

    def test_image_stays_in_memory_and_visual_action_expires_on_pause(self):
        from PIL import Image
        class Models:
            catalog = [{'name': 'synthetic-vision', 'capabilities': ['vision']}]
            def rank(self, *args): return self.catalog
            def chat(self, messages, **kwargs):
                self.messages = messages
                return {'content': 'Error 503 visible.'}
        models = Models()
        vision = Vision(models, capture=lambda scope: (Image.new('RGB', (1600, 900)), {'hwnd': 1, 'bbox': (0, 0, 1600, 900)}))
        vision.pause(False)
        result = vision.analyze()
        self.assertLessEqual(result['width'], 1280)
        self.assertNotIn('image', result)
        self.assertTrue(models.messages[-1]['images'])
        vision.validate_click({'capture_id': result['capture_id'], 'x': 100, 'y': 100})
        vision.pause()
        with self.assertRaises(ValueError): vision.validate_click({'capture_id': result['capture_id'], 'x': 100, 'y': 100})


class DiagnosticTests(unittest.TestCase):
    def test_trends_require_multiple_real_samples_and_never_claim_causation(self):
        with tempfile.TemporaryDirectory() as temp:
            plans = Plans(registry(), Path(temp) / 'tasks.sqlite3')
            diagnostics = Diagnostics(plans.engine)
            self.assertEqual(diagnostics.report()['recommendations'], [])
            for index in range(6):
                diagnostics.record({'cpu_percent': 94, 'ram_available_bytes': (2 - .2 * index) * 1024**3})
            result = diagnostics.report()
            self.assertEqual(result['samples'], 6)
            self.assertTrue(any('no demuestra' in item for item in result['recommendations']))
            with self.assertRaises(ValueError): diagnostics.record({'cpu_percent': float('nan')})


if __name__ == '__main__': unittest.main()
