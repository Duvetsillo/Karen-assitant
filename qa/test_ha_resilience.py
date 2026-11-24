"""Malformed webhook data must never crash the assistant or confirm an action."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import requests

from ha_control import DEVICES, HomeAssistantControl


class HomeAssistantResilienceTests(unittest.TestCase):
    def test_invalid_configuration_never_sends_a_command(self):
        for config in ([], None, {'url': 123, 'webhook_id': 'test'},
                       {'url': 'https://example.test', 'webhook_id': ''}):
            with self.subTest(config=config):
                self.path.write_text(json.dumps(config), encoding='utf-8')
                self.assertIn('no está confirmada', self.client.execute('enciende la luz'))
        self.session.post.assert_not_called()

    def test_unreadable_configuration_does_not_crash_or_send_a_command(self):
        with patch.object(Path, 'read_text', side_effect=PermissionError('locked')):
            self.assertIn('no está confirmada', self.client.execute('enciende la luz'))
        self.session.post.assert_not_called()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'ha.json'
        self.path.write_text(json.dumps({'url': 'https://example.test', 'webhook_id': 'test'}), encoding='utf-8')
        self.session = Mock()
        self.client = HomeAssistantControl(self.path, self.session)

    def test_malformed_responses_do_not_crash_or_confirm_action(self):
        for payload in (None, [], 'ok', {'ok': True, 'states': None}, {'ok': True, 'states': []}):
            with self.subTest(payload=payload):
                self.session.post.return_value.json.return_value = payload
                self.assertIn('no está confirmada', self.client.execute('enciende la luz'))

    def test_invalid_entity_state_is_reported_as_unknown(self):
        self.session.post.return_value.json.return_value = {
            'ok': True, 'states': {DEVICES['luz'][0]: {'invalid': True}}}
        self.assertEqual(self.client.execute('estado luz'), 'Luz: sin datos.')

    def test_http_error_never_reports_success_from_body(self):
        self.session.post.return_value.raise_for_status.side_effect = requests.HTTPError('503')
        self.session.post.return_value.json.return_value = {'ok': True, 'states': {DEVICES['luz'][0]: 'on'}}
        self.assertIn('no está confirmada', self.client.execute('enciende la luz'))
        self.session.post.return_value.json.assert_not_called()
