"""Explicit foreground-window lookup remains local and out of speech/history."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from karen_app import KarenClient
from windows_context import _clean


class WindowContextTests(unittest.TestCase):
    def test_window_metadata_stays_out_of_model_speech_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'history.db')
            chat_id = archive.current()
            client = KarenClient('http://localhost:11434')
            client.archive, client.chat_id = archive, chat_id
            callback = Mock()
            with patch('windows_context.active_window', return_value={
                'title': 'Documento privado', 'pid': 123, 'process': 'editor.exe',
            }), patch('karen_app.requests.post') as post:
                answer = client.ask('/ventana activa', callback, callback)
            self.assertIn('Documento privado', answer)
            self.assertIn('editor.exe', answer)
            callback.assert_not_called()
            post.assert_not_called()
            self.assertEqual(archive.exchanges(chat_id), [])

    def test_unavailable_window_has_generic_error(self):
        client = KarenClient('http://localhost:11434')
        with patch('windows_context.active_window', side_effect=OSError('secret path')):
            self.assertEqual(client.ask('/ventana activa'),
                             'No pude consultar la ventana activa de Windows.')

    def test_window_title_is_bounded_and_control_characters_removed(self):
        self.assertEqual(_clean('A\nB\tC'), 'A B C')
        self.assertEqual(len(_clean('x' * 300)), 200)


if __name__ == '__main__':
    unittest.main()
