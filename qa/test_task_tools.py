"""Fixed local PC task report and Karen command routing."""

import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from conversations import Conversations
from karen_app import KarenApp, KarenClient
from karen_task_tools import run_pc_report
from karen_tasks import TaskEngine, ToolSpec
from qa.ui_helpers import wait_archive, close_app, pump_until
from config import load_config


class PcReportTests(unittest.TestCase):
    def test_three_step_report_returns_real_tool_outputs_only_in_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = {
                'cpu_sample': ToolSpec('read', lambda _a, _s: {'cpu_percent': 25.0}),
                'memory_sample': ToolSpec('read', lambda _a, _s: {
                    'ram_available_bytes': 2 * 1024 ** 3, 'ram_total_bytes': 4 * 1024 ** 3}),
                'disk_sample': ToolSpec('read', lambda _a, _s: {
                    'drive': 'C:', 'disk_free_bytes': 3 * 1024 ** 3,
                    'disk_total_bytes': 8 * 1024 ** 3}),
            }
            engine = TaskEngine(tools, Path(directory) / 'tasks.sqlite3')
            answer = run_pc_report(engine)
            self.assertIn('CPU: 25.0%', answer)
            self.assertIn('RAM disponible: 2.00/4.00 GiB', answer)
            self.assertIn('Disco C: 3.00/8.00 GiB', answer)
            task_id = answer.split('ID: ', 1)[1].split('.', 1)[0]
            self.assertEqual(engine.inspect(task_id)['status'], 'completed')
            self.assertNotIn(b'25.0%', engine.path.read_bytes())

    def test_task_command_stays_out_of_model_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat_id = archive.current()
            client = KarenClient('http://localhost:11434')
            client.archive, client.chat_id = archive, chat_id
            public, private = Mock(), Mock()
            with patch('karen_task_tools.run_pc_report', return_value='Informe privado'), \
                 patch('karen_app.requests.post') as post:
                self.assertEqual(client.ask('/tareas informe pc', public, private), 'Informe privado')
            public.assert_not_called()
            private.assert_called_once_with('Informe privado')
            post.assert_not_called()
            self.assertEqual(archive.exchanges(chat_id), [])

    def test_task_status_and_cancel_are_local(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tasks.sqlite3'
            with patch('karen_tasks.DEFAULT_PATH', path):
                engine = TaskEngine({'cpu_sample': ToolSpec('read', lambda _a, _s: 1)})
                task_id = engine.create([{'tool': 'cpu_sample', 'args': {}}])
                client = KarenClient('http://localhost:11434')
                self.assertIn('pending', client.ask(f'/tareas estado {task_id}'))
                self.assertIn('canceled', client.ask(f'/tareas cancelar {task_id}'))
                self.assertIn('canceled', client.ask(f'/tareas estado {task_id}'))

    def test_ui_button_cancels_running_task(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'tasks.sqlite3'
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat_id = archive.current()
            started = threading.Event()
            tools = {'cpu_sample': ToolSpec('read', lambda _a, stop: started.set() or stop.wait(2), timeout=3)}
            engine = TaskEngine(tools, database)
            identity = []
            def slow_report(on_started=None):
                plan = [{'tool': 'cpu_sample', 'args': {}}]
                task_id = engine.create(plan)
                identity.append(task_id)
                on_started(task_id)
                return 'Informe detenido.' if engine.run(task_id, plan)['status'] == 'canceled' else 'Error de prueba.'
            with (patch('karen_tasks.DEFAULT_PATH', database),
                  patch('karen_app.open_archive', return_value=(archive, chat_id, None)),
                  patch.object(KarenApp, 'load_catalog'),
                  patch.object(KarenApp, 'connect_benchmark'),
                  patch.object(KarenApp, 'ensure_target', return_value=True),
                  patch('karen_task_tools.run_pc_report', side_effect=slow_report)):
                app = KarenApp(replace(load_config(), tts_enabled=False, wake_auto_start=False))
                try:
                    wait_archive(app)
                    app.send_prompt('/tareas informe pc')
                    self.assertTrue(started.wait(1))
                    pump_until(app, lambda: app.cancel_task_button.cget('state') == 'normal')
                    self.assertEqual(app.cancel_task_button.cget('state'), 'normal')
                    app.cancel_task_button.invoke()
                    app.request_thread.join(2)
                    time.sleep(0.06)
                    app.root.update()
                    self.assertFalse(app.request_thread.is_alive())
                    self.assertEqual(engine.inspect(identity[0])['status'], 'canceled')
                    self.assertEqual(app.cancel_task_button.cget('state'), 'disabled')
                finally:
                    close_app(app)


if __name__ == '__main__':
    unittest.main()
