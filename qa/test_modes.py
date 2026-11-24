"""Local mode commands and Core preference contract."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from conversations import Conversations
from karen_app import KarenClient


class ModeTests(unittest.TestCase):
    def test_classic_mode_is_shared_persistent_and_never_sent_to_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'core.sqlite3'
            archive = Conversations(path)
            chat_id = archive.current()
            client = KarenClient('http://localhost:11434')
            client.archive, client.chat_id = archive, chat_id
            private = Mock()
            with patch('karen_app.requests.post') as post:
                self.assertEqual(client.ask('/modo gaming', on_private_sentence=private),
                                 'Modo compartido: gaming.')
                self.assertEqual(Conversations(path).get_mode(), 'gaming')
                self.assertEqual(client.ask('/modo', on_private_sentence=private),
                                 'Modo compartido: gaming.')
                self.assertEqual(client.ask('/modo no molestar', on_private_sentence=private),
                                 'Modo compartido: no molestar.')
                self.assertEqual(Conversations(path).get_mode(), 'do_not_disturb')
                self.assertEqual(client.ask('/modo normal', on_private_sentence=private),
                                 'Modo compartido: normal.')
                self.assertIn('Usa /modo', client.ask('/modo desconocido'))
                post.assert_not_called()
            self.assertEqual(private.call_count, 4)
            self.assertEqual(archive.exchanges(chat_id), [])

    def test_invalid_stored_mode_falls_back_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'core.sqlite3')
            with self.assertRaises(ValueError):
                archive.set_mode('admin')
            self.assertIsNone(archive.get_mode())


if __name__ == '__main__':
    unittest.main()
