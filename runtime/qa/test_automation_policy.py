from datetime import datetime, timedelta, timezone
import tempfile
from pathlib import Path
import unittest

from karen_core2.automation import Automations, TRIGGER_TOPICS
from karen_core2.automation_policy import read_metrics
from karen_core2.events import EventBus, TOPICS
from karen_core2.planning import Plans
from qa.test_core2 import registry, plan


class AutomationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = []
        self.bus = EventBus()
        self.now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        self.clock = {'now': self.now}
        self.plans = Plans(registry(lambda args, stop: self.calls.append(1) or {'value': 1}), Path(self.temp.name) / 'tasks.sqlite3')
        self.engine = Automations(self.plans, events=self.bus, clock=lambda: self.clock['now'])
        self.addCleanup(self.engine.close)

    def create(self, **values):
        return self.engine.create(**({'name': 'Policy probe', 'recipe': plan(count=1),
                                      'due_at': (self.now - timedelta(seconds=1)).isoformat()} | values))

    def tick(self):
        return self.engine.tick(now=self.clock['now'].isoformat())

    def test_quiet_hours_persist_across_midnight_and_do_not_consume_occurrence(self):
        self.create()
        self.engine.quiet(start='22:00', end='07:00', offset_minutes=0)
        restarted = Automations(Plans(self.plans.registry, self.plans.path))
        for hour in (23, 2):
            when = self.now.replace(hour=hour)
            self.assertEqual(restarted.tick(now=when.isoformat())['deferred'], 'quiet_hours')
        self.assertEqual(self.calls, [])
        self.assertEqual(restarted.history(), [])
        self.assertEqual(restarted.tick(now=self.now.replace(hour=7).isoformat())['runs'], [])
        self.assertEqual(restarted.tick(now=self.now.replace(hour=13).isoformat())['runs'][0]['status'], 'completed')

    def test_resource_conditions_fail_closed_then_run_with_sufficient_measured_resources(self):
        self.create(conditions={'min_ram_available_mib': 1024, 'max_cpu_percent': 50})
        metrics = {'ram_available_bytes': 512 * 1024**2, 'cpu_percent': 20}
        self.engine.probe = lambda keys: metrics
        self.assertEqual(self.tick()['runs'][0]['reason'], 'ram_condition')
        metrics.update(ram_available_bytes=2 * 1024**3, cpu_percent=80)
        self.assertEqual(self.tick()['runs'][0]['reason'], 'cpu_condition')
        metrics['cpu_percent'] = None
        self.assertEqual(self.tick()['runs'][0]['reason'], 'metric_unavailable')
        self.assertEqual(self.calls, [])
        metrics['cpu_percent'] = 10
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')
        self.assertEqual(self.calls, [1])

    def test_windows_ram_condition_uses_real_sensor_without_loading_models(self):
        measured = read_metrics({'ram_available_bytes'})
        self.assertGreater(measured['ram_available_bytes'], 0)
        self.create(conditions={'min_ram_available_mib': 0})
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')

    def test_runtime_memory_and_vault_events_trigger_real_windows_read_plans(self):
        from karen_core2.runtime import CoreRuntime
        from karen_core2.obsidian import ObsidianManager
        root = Path(self.temp.name)
        vault = root / 'vault'
        (vault / 'Notes').mkdir(parents=True)
        manager = ObsidianManager(vault, ['Notes'], root / 'index.sqlite3')
        runtime = CoreRuntime(archive_path=root / 'core.sqlite3', task_path=root / 'real-tasks.sqlite3', obsidian=manager)
        try:
            recipe = {'goal': 'Read real RAM after memory conflict', 'steps': [
                {'id': 'ram', 'label': 'RAM', 'tool': 'memory_sample', 'args': {}, 'depends': []}]}
            runtime.automations.create(name='Conflict read', recipe=recipe, event={'topic': 'memory.conflict'})
            runtime.automations.create(name='Vault read', recipe=recipe, event={'topic': 'obsidian.index.updated'})
            runtime.automations.listen()
            runtime.memory.add('Karen', 'Puerto sintético 1234', fact_key='test.port')
            runtime.memory.add('Karen', 'Puerto sintético 4321', fact_key='test.port')
            result = runtime.automations.tick()['runs'][0]
            self.assertEqual(result['status'], 'completed')
            self.assertGreater(runtime.plans.inspect(result['plan_id'])['steps'][0]['result']['ram_available_bytes'], 0)
            (vault / 'Notes/External.md').write_text('Cambio externo sintético.', encoding='utf-8')
            manager.reindex()
            self.assertEqual(runtime.automations.tick()['runs'][0]['status'], 'completed')
        finally:
            runtime.close()

    def test_weekday_window_and_mode_conditions(self):
        self.create(conditions={'weekdays': [self.now.weekday()], 'allowed_modes': ['normal'],
                                'window': {'start': '10:00', 'end': '14:00', 'offset_minutes': 0}})
        self.engine.mode = lambda: 'do_not_disturb'
        self.assertEqual(self.tick()['runs'][0]['reason'], 'mode_condition')
        self.engine.mode = lambda: 'normal'
        self.clock['now'] = self.now.replace(hour=15)
        self.assertEqual(self.tick()['runs'][0]['reason'], 'time_window')
        self.clock['now'] = self.now + timedelta(days=1)
        self.assertEqual(self.tick()['runs'][0]['reason'], 'weekday_condition')
        self.clock['now'] = self.now
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')

    def test_event_filters_pending_coalescing_cooldown_and_persistent_deduplication(self):
        self.create(due_at=None, event={'topic': 'obsidian.note.changed', 'code': 'ok', 'entity_id': 'a' * 64})
        self.engine.listen()
        self.engine.listen()
        self.assertEqual(self.bus.status()['listeners'], len(TRIGGER_TOPICS))
        self.bus.emit('obsidian.note.changed', entity_id='b' * 64)
        self.assertEqual(self.tick()['runs'], [])
        self.bus.emit('obsidian.note.changed', entity_id='a' * 64)
        accepted = self.bus.status()['recent'][-1]
        self.assertEqual(self.engine.capture_event(accepted)['queued'], 0)
        self.bus.emit('obsidian.note.changed', entity_id='a' * 64)
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')
        self.assertEqual(self.tick()['runs'], [])
        self.bus.emit('obsidian.note.changed', entity_id='a' * 64)
        self.assertEqual(self.tick()['runs'], [])
        self.clock['now'] += timedelta(seconds=61)
        restarted = Automations(Plans(self.plans.registry, self.plans.path), clock=lambda: self.clock['now'])
        self.assertEqual(restarted.capture_event(accepted)['queued'], 0)
        self.bus.emit('obsidian.note.changed', entity_id='a' * 64)
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')
        self.assertEqual(len(self.calls), 2)
        self.engine.close()
        self.assertEqual(self.bus.status()['listeners'], 0)

    def test_queued_event_survives_restart_and_quiet_hours_without_new_event(self):
        self.create(due_at=None, event={'topic': 'memory.conflict'})
        self.engine.listen()
        self.bus.emit('memory.conflict')
        self.engine.quiet(start='11:00', end='13:00', offset_minutes=0)
        self.assertEqual(self.tick()['deferred'], 'quiet_hours')
        self.engine.close()
        restarted = Automations(Plans(self.plans.registry, self.plans.path), clock=lambda: self.clock['now'])
        self.clock['now'] = self.now.replace(hour=13)
        self.assertEqual(restarted.tick()['runs'][0]['status'], 'completed')
        self.assertEqual(len(restarted.history()), 1)
        self.assertEqual(restarted.tick()['runs'], [])

    def test_scheduled_tool_events_do_not_trigger_other_jobs_or_form_loops(self):
        self.create(due_at=None, event={'topic': 'obsidian.note.changed'})
        other = self.create(due_at=None, event={'topic': 'memory.conflict'})
        self.engine.listen()
        self.bus.emit('obsidian.note.changed')
        original = self.plans.engine.tools['probe']
        from karen_tasks import ToolSpec
        def emit(args, stop):
            self.bus.emit('memory.conflict')
            return {'value': 1}
        self.plans.engine.tools['probe'] = ToolSpec('read', emit, original.validate, original.verify, original.timeout)
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')
        self.assertIsNone(self.engine.policy(id=other['id'])['pending_at'])
        self.clock['now'] += timedelta(seconds=61)
        self.assertEqual(self.tick()['runs'], [])

    def test_invalid_policies_fail_before_any_schedule_is_written(self):
        cases = [{'conditions': {'expression': 'execute()'}}, {'conditions': {'max_cpu_percent': True}},
                 {'conditions': {'min_ram_available_mib': -1}}, {'conditions': {'allowed_modes': ['gaming']}},
                 {'event': {'topic': 'task.completed'}}, {'event': {'topic': 'memory.conflict', 'cooldown_seconds': 0}},
                 {'event': {'topic': 'memory.conflict'}, 'interval_seconds': 60}]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.create(**values)
        self.assertEqual(self.engine.list(), [])
        with self.assertRaises(ValueError):
            self.engine.quiet(start='22:00', end='22:00')

    def test_dry_run_does_not_disable_corrupt_schedule_and_actual_run_blocks_it(self):
        row = self.create()
        with self.plans.engine._connect() as db:
            db.execute('UPDATE core2_schedule_policy SET conditions=? WHERE schedule_id=?', ('{"expression":"bad"}', row['id']))
        self.engine.tick(dry_run=True, now=self.now.isoformat())
        self.assertEqual(self.engine.list()[0]['enabled'], 1)
        self.assertEqual(self.engine.history(), [])
        self.assertEqual(self.tick()['runs'][0]['status'], 'blocked')
        self.assertEqual(self.engine.list()[0]['enabled'], 0)

    def test_completion_cannot_reenable_a_schedule_paused_by_another_instance(self):
        row = self.create(interval_seconds=60)
        original = self.plans.engine.tools['probe']
        from karen_tasks import ToolSpec
        def pause(args, stop):
            with self.plans.engine._connect() as db:
                db.execute('UPDATE core2_schedules SET enabled=0 WHERE id=?', (row['id'],))
            return {'value': 1}
        self.plans.engine.tools['probe'] = ToolSpec('read', pause, original.validate, original.verify, original.timeout)
        self.assertEqual(self.tick()['runs'][0]['status'], 'completed')
        self.assertEqual(self.engine.list()[0]['enabled'], 0)

    def test_ten_deferred_jobs_do_not_starve_a_later_runnable_job(self):
        for _ in range(10):
            self.create(conditions={'allowed_modes': ['do_not_disturb']})
        self.create(due_at=self.now.isoformat())
        results = self.tick()['runs']
        self.assertEqual(sum(row['status'] == 'completed' for row in results), 1)
        self.assertEqual(self.calls, [1])

    def test_quiet_hours_are_rechecked_between_jobs_using_current_clock(self):
        self.create()
        self.create(due_at=self.now.isoformat())
        self.engine.quiet(start='13:00', end='14:00', offset_minutes=0)
        original = self.plans.engine.tools['probe']
        from karen_tasks import ToolSpec
        def advance(args, stop):
            self.calls.append(1)
            self.clock['now'] = self.now.replace(hour=13)
            return {'value': 1}
        self.plans.engine.tools['probe'] = ToolSpec('read', advance, original.validate, original.verify, original.timeout)
        result = self.engine.tick()
        self.assertEqual(result['deferred'], 'quiet_hours')
        self.assertEqual(len(self.calls), 1)
        self.engine.quiet()
        self.engine.tick()
        self.assertEqual(len(self.calls), 2)


if __name__ == '__main__':
    unittest.main()
