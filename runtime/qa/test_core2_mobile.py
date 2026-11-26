import tempfile
from pathlib import Path

from qa import test_mobile_server as mobile_tests
from karen_core2.runtime import CoreRuntime
from karen_core2.skills import Skill, SkillRegistry, validate_schema
from karen_tasks import ToolSpec


class FakeModels:
    catalog = []
    def status(self):
        return {'endpoint': 'http://127.0.0.1:11434', 'models': [], 'active_model': None, 'hardware': {}, 'latency': [], 'local_only': True}
    def discover(self, force=False): return []
    def rank(self, *args): return []
    def chat(self, *args, **kwargs): return {'content': 'Local synthetic reply'}


class CoreMobileTests(mobile_tests.MobileTests):
    def setUp(self):
        super().setUp()
        self.app.core2 = CoreRuntime(archive_path=self.archive.path,
            task_path=Path(self.temp.name) / 'tasks.sqlite3', models=FakeModels())
        self.app.speech.prepare_chat = lambda **kwargs: None  # Offline fixtures never touch the real voice process.

    def test_jarvis_assets_and_core_data_require_correct_boundary(self):
        for path in ('/jarvis', '/jarvis.js', '/jarvis.css'):
            self.assertEqual(self.request(path, auth=False)[0], 200)
        self.assertEqual(self.request('/api/core2/status', auth=False)[0], 401)
        self.assertEqual(self.request('/api/core2/status')[0], 200)
        self.assertEqual(self.request('/api/core2/plans')[0], 200)
        self.assertEqual(self.request('/api/core2/home/status', auth=False)[0], 401)
        self.assertEqual(self.request('/api/core2/home/status')[0], 200)

    def test_provider_contract_rejects_malformed_or_analysis_only_answers(self):
        from unittest.mock import patch
        for answer in (None, [], {}, '<think>sin respuesta final'):
            with self.subTest(answer=answer), patch.object(self.app.core2, 'chat', return_value=answer):
                with self.assertRaises(ValueError):
                    self.app.generate(self.chat, 'Hola')

    def test_remote_run_cannot_inherit_desktop_approval_or_accept_approval_in_json(self):
        target = self.app.core2
        schema = {'type': 'object', 'properties': {}}
        spec = ToolSpec('sensitive', lambda args, stop: {'done': True}, lambda args: validate_schema(schema, args), lambda args, result: result['done'])
        target.registry.register(Skill('test_write', 'Write', 'Synthetic', 'SYSTEM', 'sensitive', schema, spec))
        target.plans.engine.tools['test_write'] = spec
        target.approve = lambda _: True
        plan = target.plans.create({'goal': 'Synthetic write', 'steps': [
            {'id': 's0', 'tool': 'test_write', 'label': 'Write', 'args': {}, 'depends': []}]})
        self.assertEqual(self.request('/api/core2/run', {'id': plan['id'], 'approved': True})[0], 400)
        status, _, _ = self.request('/api/core2/run', {'id': plan['id']})
        self.assertEqual(status, 200)
        self.assertEqual(target.plans.inspect(plan['id'])['status'], 'awaiting_approval')

    def test_invalid_goals_and_unknown_plan_ids_fail_without_tracebacks(self):
        self.assertEqual(self.request('/api/core2/plan', {'goal': 99})[0], 400)
        self.assertEqual(self.request('/api/core2/run', {'id': 'bad'})[0], 400)
        self.assertEqual(self.request('/api/core2/status', host='evil.example')[0], 403)

    def test_vision_missing_local_model_does_not_capture_and_restores_pause(self):
        self.assertEqual(self.request('/api/core2/vision', {'scope': 'window'})[0], 400)
        self.assertTrue(self.app.core2.vision.paused)

    def test_shared_memory_history_graph_timeline_and_authentication(self):
        memory = self.app.core2.memory
        one = memory.add('Homelab', 'Jellyfin en Proxmox', kind='relational')
        two = memory.add('Homelab', 'Contenedor de Jellyfin', kind='semantic')
        memory.relate(one['id'], two['id'], 'runs_on')
        memory.base.edit(one['id'], 'Jellyfin funciona en Proxmox')
        for route in ('graph?project=Homelab', 'consolidate?project=Homelab', 'timeline?project=Homelab',
                      one['id'] + '/history', one['id'] + '/procedure'):
            path = '/api/core2/memory/' + route
            self.assertEqual(self.request(path, auth=False)[0], 401)
            self.assertEqual(self.request(path)[0], 200)
        self.assertEqual(len(memory.history(one['id'])), 2)

    def test_schedule_and_development_metadata_are_authenticated_and_read_only(self):
        import json
        recipe = {'goal': 'PRIVATE_MOBILE_RECIPE', 'steps': [
            {'id': 'ram', 'label': 'Read RAM', 'tool': 'memory_sample', 'args': {}, 'depends': []}]}
        schedule = self.app.core2.automations.create(name='Routine', recipe=recipe, due_at='2100-01-01T00:00:00+00:00')
        handoff = self.app.core2.handoffs.create(project='Karen', description='PRIVATE_DESCRIPTION', acceptance=['PRIVATE_CRITERIA'])
        for kind, identity in (('schedules', schedule['id']), ('handoffs', handoff['task']['id'])):
            for prefix in ('/api/core2/', '/api/v1/'):
                route = prefix + kind
                self.assertEqual(self.request(route, auth=False)[0], 401)
                status, _, body = self.request(route)
                self.assertEqual(status, 200)
                parsed = json.loads(body)
                self.assertEqual(parsed[kind][0]['id'], identity)
                self.assertNotIn('PRIVATE_', body.decode())
            self.assertEqual(self.request('/api/core2/' + kind, {'enabled': True})[0], 400)
        self.assertEqual(self.app.core2.automations.history(), [])
        self.assertEqual(self.request('/api/core2/schedules?unknown=1')[0], 400)
