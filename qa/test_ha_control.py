"""Safety checks for Karen's direct device-command parser."""

import unittest
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

from ha_control import HomeAssistantDiscovery, parse_command
from conversations import Conversations
from karen_app import KarenClient


class DirectHomeCommands(unittest.TestCase):
    def test_explicit_device_commands(self):
        self.assertEqual(parse_command("Karen, apaga el abanico"), ("off", ("abanico",)))
        self.assertEqual(parse_command("Prende el cargador del escritorio"), ("on", ("cargador",)))
        self.assertEqual(parse_command("¿Cómo está la nevera?"), ("status", ("nevera",)))
        self.assertEqual(parse_command("Apaga todo el cuarto"),
                         ("off", ("luz", "abanico", "cargador")))

    def test_not_commands(self):
        self.assertIsNone(parse_command("No prende la nevera"))
        self.assertIsNone(parse_command("Por qué se apaga la luz"))
        self.assertIsNone(parse_command("Qué hora es"))
        self.assertEqual(parse_command("Enciende y apaga la luz"), ("ambiguous", ()))
        self.assertEqual(parse_command("Enciende todo"), ("ambiguous_target", ()))

    def test_read_only_discovery_filters_real_api_shape(self):
        session = Mock()
        session.get.return_value.json.return_value = [
            {'entity_id': 'switch.desk', 'state': 'on', 'attributes': {'friendly_name': 'Escritorio'}},
            {'entity_id': 'sensor.temperature', 'state': '23', 'attributes': {}},
            {'entity_id': 'bad id', 'state': 'on'},
        ]
        discovery = HomeAssistantDiscovery('http://127.0.0.1:8123', 'test-token', session)
        self.assertEqual(discovery.list_entities('switch'), [
            {'entity_id': 'switch.desk', 'name': 'Escritorio', 'state': 'on'}])
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(session.get.call_args.kwargs['headers'],
                         {'Authorization': 'Bearer test-token'})
        with self.assertRaisesRegex(ValueError, 'URL'):
            HomeAssistantDiscovery('http://user:pass@127.0.0.1:8123', 'token', session).list_entities()
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            HomeAssistantDiscovery('http://192.168.1.20:8123', 'token', session).list_entities()

    def test_discovery_command_never_reaches_model_or_history(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat = archive.create()
            client = KarenClient('http://127.0.0.1:11434')
            client.archive, client.chat_id = archive, chat
            fake = [{'entity_id': 'switch.desk', 'name': 'Escritorio', 'state': 'on'}]
            with (patch('karen_app.HomeAssistantDiscovery') as discovery,
                  patch('karen_app.requests.post', side_effect=AssertionError('No enviar al modelo')),
                  patch.object(client.home, 'execute', side_effect=AssertionError('No controlar HA'))):
                discovery.return_value.list_entities.return_value = fake
                self.assertIn('switch.desk', client.ask('/casa entidades switch'))
                self.assertIn('no se pudieron consultar', client.ask('/casa entidades switch.invalid'))
                discovery.return_value.list_entities.assert_called_once_with('switch')
            self.assertEqual(archive.exchanges(chat), [])


if __name__ == "__main__":
    unittest.main()
