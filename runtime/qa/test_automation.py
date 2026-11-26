from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from karen_core2.automation import Automations, command
from karen_core2.runtime import CoreRuntime
from qa.test_core2 import registry, plan
from karen_core2.planning import Plans


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'tasks.sqlite3'
        self.calls = []
        self.registry = registry(lambda args, stop: self.calls.append(1) or {'value': 1})
        self.plans = Plans(self.registry, self.path)
        self.scheduler = Automations(self.plans)
        self.now = datetime.now(timezone.utc)
        self.due = (self.now - timedelta(seconds=1)).isoformat()

    def create(self, **extra):
        return self.scheduler.create(name='Synthetic read', recipe=plan(count=1), due_at=self.due, **extra)

    def test_schedule_survives_restart_and_executes_once_without_llm(self):
        created = self.create()
        restarted = Automations(Plans(self.registry, self.path))
        result = restarted.tick(now=self.now.isoformat())
        self.assertEqual(result['runs'][0]['status'], 'completed')
        self.assertEqual(self.calls, [1])
        self.assertEqual(restarted.tick(now=self.now.isoformat())['runs'], [])
        self.assertEqual(restarted.history()[0]['schedule_id'], created['id'])
        self.assertEqual(restarted.list()[0]['enabled'], 0)
        with self.plans.engine._connect() as db:
            self.assertNotIn('Synthetic task', db.execute('SELECT payload FROM core2_schedules').fetchone()[0])

    def test_simulation_never_executes_or_consumes_occurrence(self):
        self.create()
        result = self.scheduler.tick(dry_run=True, now=self.now.isoformat())
        self.assertTrue(result['runs'][0]['simulation'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.scheduler.history(), [])
        self.assertEqual(self.scheduler.list()[0]['enabled'], 1)

    def test_write_recipe_only_has_simulation_and_cannot_be_scheduled(self):
        other = Automations(Plans(registry(permission='sensitive'), Path(self.temp.name) / 'write.sqlite3'))
        self.assertEqual(other.simulate(plan(count=1))['steps'][0]['permission'], 'sensitive')
        with self.assertRaises(ValueError):
            other.create(name='Write', recipe=plan(count=1), due_at=self.due)
        self.assertEqual(other.list(), [])

    def test_gaming_and_disabled_schedules_do_not_execute(self):
        created = self.create()
        self.scheduler.mode = lambda: 'gaming'
        self.assertEqual(self.scheduler.tick(now=self.now.isoformat())['deferred'], 'gaming')
        self.scheduler.mode = lambda: 'normal'
        self.scheduler.enable(id=created['id'], enabled=False)
        self.assertEqual(self.scheduler.tick(now=self.now.isoformat())['runs'], [])
        self.assertEqual(self.calls, [])

    def test_missed_intervals_are_coalesced_and_failures_have_bounded_retries(self):
        created = self.create(interval_seconds=60)
        later = self.now + timedelta(hours=1)
        self.scheduler.tick(now=later.isoformat())
        self.assertEqual(len(self.calls), 1)
        self.assertGreater(datetime.fromisoformat(self.scheduler.list()[0]['next_run']), later)
        self.scheduler.enable(id=created['id'], enabled=False)
        failing = Automations(Plans(registry(lambda args, stop: self.calls.append(0) or {'value': 0}),
                                    Path(self.temp.name) / 'failing.sqlite3'))
        failing.create(name='Bounded failure', recipe=plan(count=1), due_at=self.due, retries=2)
        self.assertEqual(failing.tick(now=self.now.isoformat())['runs'][0]['status'], 'failed')
        self.assertEqual(self.calls.count(0), 6)  # Three schedule attempts; two read retries per plan.
        self.assertEqual(failing.tick(now=self.now.isoformat())['runs'], [])

    def test_timezone_validation_and_unknown_commands_fail_without_execution(self):
        with self.assertRaises(ValueError):
            self.scheduler.create(name='Bad', recipe=plan(count=1), due_at='2026-11-26T12:00:00')
        with self.assertRaises(ValueError):
            command(self.scheduler, '/automation shell {"command":"bad"}')
        self.assertEqual(self.calls, [])

    def test_changed_tool_permissions_block_a_saved_recipe_after_restart(self):
        created = self.create()
        restarted = Automations(Plans(registry(permission='sensitive'), self.path))
        self.assertEqual(restarted.tick(now=self.now.isoformat())['runs'][0]['status'], 'blocked')
        self.assertEqual(restarted.history()[0]['status'], 'blocked')
        self.assertEqual(restarted.list()[0]['enabled'], 0)
        self.assertEqual(restarted.history()[0]['schedule_id'], created['id'])
        self.assertEqual(self.calls, [])

    def test_real_process_crash_recovers_read_occurrence_without_duplicate_plan(self):
        path = Path(self.temp.name) / 'crash.sqlite3'
        script = '''
import os,sys
from karen_core2.automation import Automations
from karen_core2.planning import Plans
from qa.test_core2 import registry,plan
engine=Automations(Plans(registry(lambda args,stop: os._exit(17)),sys.argv[1]))
engine.create(name='Crash probe',recipe=plan(count=1),due_at=sys.argv[2])
engine.tick()
'''
        crashed = subprocess.run([sys.executable, '-c', script, str(path), self.due],
                                 cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=10)
        self.assertEqual(crashed.returncode, 17)
        restarted = Automations(Plans(self.registry, path))
        prior = restarted.history()[0]['plan_id']
        result = restarted.tick(now=self.now.isoformat())['runs'][0]
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['plan_id'], prior)
        self.assertEqual(self.calls, [1])
        self.assertEqual(len(restarted.plans.list()), 1)

    def test_real_windows_sensor_plan_persists_execution_history(self):
        root = Path(self.temp.name)
        runtime = CoreRuntime(archive_path=root / 'core.sqlite3', task_path=root / 'real-tasks.sqlite3')
        try:
            recipe = {'goal': 'Medir RAM local sintética', 'steps': [
                {'id': 'ram', 'label': 'Leer RAM real', 'tool': 'memory_sample', 'args': {}, 'depends': []}]}
            runtime.automations.create(name='Real RAM sample', recipe=recipe, due_at=self.due)
            result = runtime.automations.tick(now=self.now.isoformat())['runs'][0]
            self.assertEqual(result['status'], 'completed')
            evidence = runtime.plans.inspect(result['plan_id'])['steps'][0]['result']
            self.assertGreater(evidence['ram_available_bytes'], 0)
            self.assertEqual(runtime.automations.history()[0]['status'], 'completed')
        finally:
            runtime.close()


if __name__ == '__main__':
    unittest.main()
