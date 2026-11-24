import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import admin_tools
from admin_runtime import policy


class PolicyDefaultsTests(unittest.TestCase):
    def test_missing_policy_allows_startup_without_authorizing_external_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'absent.json'
            with patch('admin_tools.POLICY', path):
                self.assertEqual(policy()['allowed_subnets'], [])
                self.assertEqual(policy()['ssh_aliases'], [])
                with self.assertRaises(ValueError):
                    admin_tools.checked_network('192.168.1.0/24')
                with patch('admin_tools.run') as execute:
                    with self.assertRaises(ValueError):
                        admin_tools.ssh_status('unapproved')
                    execute.assert_not_called()
            self.assertFalse(path.exists())

    def test_existing_scope_is_preserved_and_malformed_data_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'policy.json'
            expected = {'allowed_subnets': ['192.168.1.0/24'], 'ssh_aliases': ['synthetic'], 'default_subnet': '192.168.1.0/24'}
            path.write_text(json.dumps(expected), encoding='utf-8')
            with patch('admin_tools.POLICY', path):
                self.assertEqual(policy(), expected)
                for bad in ('[]', '{}', '{"allowed_subnets":true,"ssh_aliases":[]}'):
                    path.write_text(bad, encoding='utf-8')
                    with self.assertRaises(ValueError):
                        policy()
