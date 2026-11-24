"""Exercise the real Tk shell with Core 2 and isolated persistence."""
import gc
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config import KarenConfig
from conversations import Conversations
from karen_app import KarenApp
from karen_core2.runtime import CoreRuntime
from qa.ui_helpers import close_app, pump_until, wait_archive


class CoreGuiTests(unittest.TestCase):
    def test_existing_shell_attaches_planner_and_closes_without_losing_legacy_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'core.sqlite3'
            archive = Conversations(path)
            chat = archive.create()
            archive.append(chat, 'Historial existente', 'Respuesta existente', True)
            runtime = CoreRuntime(archive_path=path, task_path=Path(directory) / 'tasks.sqlite3')
            with (patch('karen_app.open_archive', return_value=(archive, chat, None)),
                  patch.object(KarenApp, 'load_catalog'), patch.object(KarenApp, 'connect_benchmark'),
                  patch.object(KarenApp, 'detect_microphone', return_value=None)):
                app = KarenApp(KarenConfig(tts_enabled=False, wake_auto_start=False), core2=runtime)
                try:
                    wait_archive(app)
                    self.assertIs(app.client.core2, runtime)
                    self.assertEqual(runtime.approve, app.confirm_admin)
                    panel = app.core2_panel
                    panel.prepare()
                    pump_until(app, lambda: bool(panel.identity), timeout=5)
                    plan = runtime.plans.inspect(panel.identity)
                    self.assertEqual(plan['status'], 'pending')
                    self.assertEqual(len(plan['steps']), 6)
                    self.assertTrue(all(step['attempts'] == 0 for step in plan['steps']))
                    self.assertIn('Respuesta existente', str(archive.exchanges(chat)))
                    note = Path(directory) / 'synthetic.md'
                    note.write_text('Proyecto telescopio: observar Saturno.', encoding='utf-8')
                    with (patch('karen_core2.panel.filedialog.askopenfilename', return_value=str(note)),
                          patch('karen_core2.panel.messagebox.askokcancel', return_value=True),
                          patch('karen_core2.panel.messagebox.askyesnocancel', return_value=False)):
                        panel.import_knowledge()
                        pump_until(app, lambda: len(runtime.knowledge.list('Karen')) == 1, timeout=5)
                        pump_until(app, lambda: not panel.worker.is_alive(), timeout=5)
                    self.assertEqual(runtime.knowledge.search('Karen', 'telescopio'), [])
                    document = runtime.knowledge.list('Karen')[0]
                    runtime.command('/conocimiento aprobar ' + document['id'])
                    self.assertEqual(len(runtime.knowledge.search('Karen', 'telescopio')), 1)
                finally:
                    # Keep the temporary DB alive until asynchronous cancellation completes.
                    with patch.object(panel, 'cancel') as cancel:
                        close_app(app)
                        cancel.assert_called_once()
                    self.assertTrue(runtime.vision.paused)
                    app = None
                    gc.collect()


if __name__ == '__main__':
    unittest.main()
