"""Real OS-lock subprocess tests on the current OS, without opening audio."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from core_resources import ResourceBusy, microphone_guard, microphone_path

WORKER = Path(__file__).resolve().parents[1] / 'desktop-pet' / 'python' / 'core_resource.py'


class CoreResourceTests(unittest.TestCase):
    def test_worker_excludes_classic_and_crash_releases_ownership(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'KAREN_RESOURCE_DIR': directory}):
            worker = subprocess.Popen([sys.executable, '-u', str(WORKER)], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                self.assertEqual(worker.stdout.readline().strip(), b'ACQUIRED')
                with self.assertRaises(ResourceBusy):
                    with microphone_guard(): self.fail('No debe adquirir un recurso ocupado')
                worker.kill()
                worker.wait(3)
                with microphone_guard(): pass
            finally:
                worker.kill() if worker.poll() is None else None
                worker.communicate(timeout=3)

    def test_worker_releases_on_parent_pipe_eof(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'KAREN_RESOURCE_DIR': directory}):
            worker = subprocess.Popen([sys.executable, '-u', str(WORKER)], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                self.assertEqual(worker.stdout.readline().strip(), b'ACQUIRED')
                worker.communicate(timeout=3)
                self.assertEqual(worker.returncode, 0)
                with microphone_guard(): pass
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate(timeout=3)

    def test_listener_does_not_open_hardware_when_other_client_owns_it(self):
        from voice import VoiceListener
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'KAREN_RESOURCE_DIR': directory}):
            stop, states = threading.Event(), []
            listener = VoiceListener(SimpleNamespace(wake_word_enabled=False, wake_mode='transcript'),
                                     None, stop, threading.Event(), lambda _: None,
                                     lambda state: (states.append(state), stop.set()) if state == 'Micrófono ocupado por otra interfaz' else None,
                                     lambda _: None)
            with microphone_guard(), patch('voice.sd.RawInputStream') as opened:
                listener.run()
            opened.assert_not_called()
            self.assertEqual(states, ['Micrófono ocupado por otra interfaz'])

    def test_rejects_relative_resource_directory(self):
        with patch.dict(os.environ, {'KAREN_RESOURCE_DIR': 'relative'}):
            with self.assertRaises(ValueError): microphone_path()


if __name__ == '__main__':
    unittest.main()
