"""Private local results must not enter a callback that may use network TTS."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from karen_app import KarenClient
from voice import speech_is_local


class PrivateLocalOutputTests(unittest.TestCase):
    def test_private_commands_stay_out_of_tts_model_and_chat_history(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'history.db')
            chat_id = archive.current()
            client = KarenClient('http://localhost:11434')
            client.archive, client.chat_id = archive, chat_id
            spoken = Mock()
            with patch('karen_app.memory_command', return_value='Recuerdo privado'), \
                 patch('karen_app.ProxmoxStatus') as proxmox, \
                 patch('karen_app.HomeAssistantDiscovery') as home, \
                 patch('karen_app.requests.post') as post:
                proxmox.return_value.cluster.return_value = {'quorate': True}
                home.return_value.list_entities.return_value = [
                    {'entity_id': 'sensor.private', 'name': 'Casa', 'state': 'on'},
                ]
                self.assertIn('Recuerdo privado', client.ask('/memoria buscar Karen | secreto', spoken))
                self.assertIn('quorate: True', client.ask('/proxmox quorum', spoken))
                self.assertIn('sensor.private', client.ask('/casa entidades', spoken))
            spoken.assert_not_called()
            post.assert_not_called()
            self.assertEqual(archive.exchanges(chat_id), [])

    def test_local_tools_use_only_explicit_private_callback(self):
        client = KarenClient('http://localhost:11434')
        client.home.execute = Mock(return_value=None)
        public, private = Mock(), Mock()
        with patch('admin_tools.route_local', return_value='Agenda privada'), \
             patch('karen_app.requests.post') as post:
            self.assertEqual(client.ask('Muestra mi calendario', public, private), 'Agenda privada')
        public.assert_not_called()
        private.assert_called_once_with('Agenda privada')
        post.assert_not_called()

    def test_home_and_admin_results_use_private_callback(self):
        client = KarenClient('http://localhost:11434')
        public, private = Mock(), Mock()
        client.home.execute = Mock(return_value='Luz: encendida.')
        self.assertEqual(client.ask('enciende luz', public, private), 'Luz: encendida.')
        client.home.execute.return_value = None
        client.admin_enabled = True
        client.admin_runtime = Mock()
        with patch('admin_agent.administration_request', return_value=True), \
             patch('admin_agent.administer', return_value='Estado interno'):
            self.assertEqual(client.ask('revisa el servidor', public, private), 'Estado interno')
        public.assert_not_called()
        self.assertEqual(private.call_args_list[0].args, ('Luz: encendida.',))
        self.assertEqual(private.call_args_list[1].args, ('Estado interno',))

    def test_private_speech_requires_local_engine(self):
        with tempfile.TemporaryDirectory() as directory, patch('voice.BASE', Path(directory)):
            self.assertFalse(speech_is_local(SimpleNamespace(tts_engine='edge')))
            self.assertTrue(speech_is_local(SimpleNamespace(tts_engine='kokoro')))
            self.assertTrue(speech_is_local(SimpleNamespace(tts_engine='qwen3')))


if __name__ == '__main__':
    unittest.main()
