"""Direct integration reads work without a model and never enter chat history."""

import unittest
from unittest.mock import Mock, patch

from karen_app import KarenClient, local_command


class DirectConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.client = KarenClient('http://127.0.0.1:5000', backend='karen')
        self.client.archive = Mock()
        self.client.chat_id = 'test'

    def test_server_read_bypasses_model_and_history(self):
        with (patch('admin_tools.ssh_status', return_value='home: running') as status,
              patch('karen_app.requests.post', side_effect=AssertionError('No model'))):
            answer = self.client.ask('/servidor estado friday-home')
        status.assert_called_once_with('friday-home')
        self.assertIn('home: running', answer)
        self.client.archive.append.assert_not_called()
        self.assertTrue(local_command('/servidor estado friday-home'))

    def test_server_failure_is_not_reported_as_connected(self):
        with patch('admin_tools.ssh_status', side_effect=RuntimeError('private details')):
            answer = self.client.ask('/servidor estado unknown')
        self.assertIn('no pude consultar', answer)
        self.assertNotIn('private details', answer)

    def test_home_read_bypasses_model_and_history(self):
        with (patch.object(self.client.home, 'execute', return_value='Luz: apagado.') as home,
              patch('karen_app.requests.post', side_effect=AssertionError('No model'))):
            self.assertEqual(self.client.ask('/casa estado luz'), 'Luz: apagado.')
        home.assert_called_once_with('estado de luz')
        self.client.archive.append.assert_not_called()
        self.assertTrue(local_command('/casa estado'))

    def test_home_command_cannot_inject_a_write(self):
        with patch.object(self.client.home, 'execute') as home:
            self.assertIn('Usa /casa estado', self.client.ask('/casa estado enciende luz'))
        home.assert_not_called()


if __name__ == '__main__':
    unittest.main()
