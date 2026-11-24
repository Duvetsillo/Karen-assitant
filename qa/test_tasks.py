"""Task execution and recovery invariants without system tools."""

from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from karen_tasks import TaskEngine, ToolSpec


class TaskEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'tasks.sqlite3'

    def tearDown(self):
        self.temp.cleanup()

    def test_persistent_progress_idempotency_and_no_raw_arguments(self):
        calls = []
        tools = {'read_status': ToolSpec('read', lambda args, stop: calls.append(args['value']) or 'ok',
                                    verify=lambda args, result: result == 'ok')}
        engine = TaskEngine(tools, self.path)
        steps = [{'tool': 'read_status', 'args': {'value': 'private host alias'}}]
        identity = engine.create(steps, idempotency_key='status:123')
        self.assertEqual(engine.create(steps, idempotency_key='status:123'), identity)
        with self.assertRaises(ValueError):
            engine.create([{'tool': 'read_status', 'args': {'value': 'other'}}],
                          idempotency_key='status:123')
        completed = engine.run(identity, steps)
        self.assertEqual(completed['status'], 'completed')
        self.assertEqual(completed['results'][0]['result'], 'ok')
        self.assertNotIn('results', engine.inspect(identity))
        self.assertEqual(calls, ['private host alias'])
        self.assertEqual(TaskEngine(tools, self.path).run(identity, steps)['status'], 'completed')
        self.assertEqual(calls, ['private host alias'])
        self.assertNotIn(b'private host alias', self.path.read_bytes())
        self.assertIn('completed', [event['state'] for event in engine.events(identity)])

    def test_sensitive_step_requires_review_and_exact_plan(self):
        calls = []
        engine = TaskEngine({'change': ToolSpec('sensitive', lambda args, stop: calls.append(args['target']) or True)},
                            self.path)
        plan = [{'tool': 'change', 'args': {'target': 'synthetic'}}]
        identity = engine.create(plan)
        self.assertEqual(engine.run(identity, plan)['status'], 'awaiting_approval')
        self.assertEqual(calls, [])
        with self.assertRaises(ValueError):
            engine.run(identity, [{'tool': 'change', 'args': {'target': 'different'}}],
                       approve=lambda _: True)
        approvals = []
        def approve(request):
            approvals.append(request)
            return True
        self.assertEqual(engine.run(identity, plan, approve=approve)['status'], 'completed')
        self.assertEqual(calls, ['synthetic'])
        self.assertEqual(approvals[0]['args'], {'target': 'synthetic'})

    def test_denial_and_cancel_before_execution(self):
        calls = []
        engine = TaskEngine({'change': ToolSpec('reversible', lambda args, stop: calls.append(1))}, self.path)
        plan = [{'tool': 'change', 'args': {}}]
        denied = engine.create(plan)
        self.assertEqual(engine.run(denied, plan, approve=lambda _: False)['status'], 'denied')
        canceled = engine.create(plan)
        self.assertEqual(engine.cancel(canceled)['status'], 'canceled')
        self.assertEqual(engine.run(canceled, plan, approve=lambda _: True)['status'], 'canceled')
        self.assertEqual(calls, [])

    def test_cancel_during_approval_never_starts_tool(self):
        calls = []
        engine = TaskEngine({'change': ToolSpec('sensitive', lambda args, stop: calls.append(1))}, self.path)
        plan = [{'tool': 'change', 'args': {}}]
        identity = engine.create(plan)
        def approve(_request):
            engine.cancel(identity)
            return True
        self.assertEqual(engine.run(identity, plan, approve=approve)['status'], 'canceled')
        self.assertEqual(calls, [])

    def test_write_timeout_is_uncertain_and_never_retried(self):
        calls = []
        def slow(args, stop):
            calls.append('started')
            stop.wait(1)
            return True
        engine = TaskEngine({'change': ToolSpec('reversible', slow, timeout=0.05)}, self.path)
        plan = [{'tool': 'change', 'args': {}}]
        identity = engine.create(plan)
        self.assertEqual(engine.run(identity, plan, approve=lambda _: True)['status'], 'uncertain')
        self.assertEqual(engine.run(identity, plan, approve=lambda _: True)['status'], 'uncertain')
        self.assertEqual(calls, ['started'])

    def test_cancel_running_write_signals_tool_and_stays_uncertain(self):
        started, released = threading.Event(), threading.Event()
        def cooperative(args, stop):
            started.set()
            stop.wait(2)
            released.set()
            return True
        engine = TaskEngine({'change': ToolSpec('sensitive', cooperative, timeout=3)}, self.path)
        plan = [{'tool': 'change', 'args': {}}]
        identity = engine.create(plan)
        result = []
        worker = threading.Thread(target=lambda: result.append(engine.run(identity, plan, approve=lambda _: True)))
        worker.start()
        self.assertTrue(started.wait(1))
        self.assertTrue(engine.cancel(identity)['cancel_requested'])
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertTrue(released.is_set())
        self.assertEqual(result[0]['status'], 'uncertain')

    def test_running_at_restart_is_never_automatically_replayed(self):
        calls = []
        tools = {'read': ToolSpec('read', lambda args, stop: calls.append(1))}
        engine = TaskEngine(tools, self.path)
        plan = [{'tool': 'read', 'args': {}}]
        identity = engine.create(plan)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE task_jobs SET status='running' WHERE id=?", (identity,))
        recovered = TaskEngine(tools, self.path)
        self.assertEqual(recovered.inspect(identity)['status'], 'interrupted')
        self.assertEqual(recovered.run(identity, plan)['status'], 'interrupted')
        self.assertEqual(calls, [])
        self.assertIn('interrupted', [event['state'] for event in recovered.events(identity)])

    def test_restart_marks_inflight_write_uncertain_without_replay(self):
        calls = []
        tools = {'change': ToolSpec('sensitive', lambda _a, _s: calls.append(1))}
        engine = TaskEngine(tools, self.path)
        plan = [{'tool': 'change', 'args': {}}]
        identity = engine.create(plan)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE task_jobs SET status='running' WHERE id=?", (identity,))
            db.execute("UPDATE task_steps SET status='running' WHERE task_id=?", (identity,))
        recovered = TaskEngine(tools, self.path)
        self.assertEqual(recovered.inspect(identity)['status'], 'uncertain')
        self.assertEqual(recovered.inspect(identity)['steps'][0]['status'], 'uncertain')
        self.assertEqual(recovered.run(identity, plan, approve=lambda _: True)['status'], 'uncertain')
        self.assertEqual(calls, [])

    def test_manual_review_records_claim_without_replaying_write(self):
        calls = []
        tools = {'change': ToolSpec('sensitive', lambda _a, _s: calls.append(1))}
        engine = TaskEngine(tools, self.path)
        plan = [{'tool': 'change', 'args': {}}]
        identity = engine.create(plan)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE task_jobs SET status='uncertain' WHERE id=?", (identity,))
            db.execute("UPDATE task_steps SET status='uncertain' WHERE task_id=?", (identity,))
        self.assertEqual(engine.uncertain_jobs()[0]['id'], identity)
        with self.assertRaises(ValueError):
            engine.review_uncertain(identity, 'unknown')
        state = engine.review_uncertain(identity, 'not_applied')
        self.assertEqual(state['status'], 'reviewed_not_applied')
        self.assertEqual(state['steps'][0]['status'], 'uncertain')
        self.assertEqual(engine.uncertain_jobs(), [])
        self.assertEqual(engine.run(identity, plan, approve=lambda _: True)['status'], 'reviewed_not_applied')
        self.assertEqual(calls, [])
        self.assertIn('reviewed_not_applied', [event['state'] for event in engine.events(identity)])
        with self.assertRaises(ValueError):
            engine.review_uncertain(identity, 'applied')

    def test_second_engine_does_not_recover_a_live_job(self):
        started, release = threading.Event(), threading.Event()
        calls = []
        def slow(_args, _stop):
            calls.append(1)
            started.set()
            release.wait(2)
            return 'ok'
        tools = {'read': ToolSpec('read', slow, timeout=3)}
        engine = TaskEngine(tools, self.path)
        plan = [{'tool': 'read', 'args': {}}]
        identity = engine.create(plan)
        results = []
        worker = threading.Thread(target=lambda: results.append(engine.run(identity, plan)))
        worker.start()
        try:
            self.assertTrue(started.wait(1))
            observer = TaskEngine(tools, self.path)
            self.assertEqual(observer.inspect(identity)['status'], 'running')
            self.assertEqual(observer.run(identity, plan)['status'], 'running')
            self.assertEqual(calls, [1])
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results[0]['status'], 'completed')

    def test_killed_worker_is_reconciled_in_another_process(self):
        tools = {'read': ToolSpec('read', lambda _a, _s: None)}
        engine = TaskEngine(tools, self.path)
        plan = [{'tool': 'read', 'args': {}}]
        identity = engine.create(plan)
        script = ("import sys,time\n"
                  "from karen_tasks import TaskEngine,ToolSpec\n"
                  "def slow(args,stop):\n"
                  "    time.sleep(30)\n"
                  "TaskEngine({'read':ToolSpec('read',slow,timeout=60)},sys.argv[1]).run("
                  "sys.argv[2],[{'tool':'read','args':{}}])\n")
        worker = subprocess.Popen([sys.executable, '-c', script, str(self.path), identity],
                                  cwd=Path(__file__).resolve().parents[1],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if engine.inspect(identity)['steps'][0]['status'] == 'running':
                    break
                if worker.poll() is not None:
                    self.fail(f'Worker terminó antes de iniciar: {worker.stderr.read().decode()}')
                time.sleep(0.05)
            else:
                self.fail('Worker no inició la herramienta a tiempo.')
            self.assertEqual(TaskEngine(tools, self.path).inspect(identity)['status'], 'running')
        finally:
            worker.kill()
            worker.wait(timeout=5)
            worker.stderr.close()
        recovered = TaskEngine(tools, self.path)
        self.assertEqual(recovered.inspect(identity)['status'], 'interrupted')
        self.assertEqual(recovered.run(identity, plan)['status'], 'interrupted')


if __name__ == '__main__':
    unittest.main()
