"""Unexpected Proxmox values must not crash local status queries."""
import unittest
from unittest.mock import Mock

from proxmox_status import ProxmoxStatus


class ProxmoxResilienceTests(unittest.TestCase):
    def test_malformed_guest_status_does_not_drop_inventory(self):
        for status in ([], {}, None, 42, True, 'unexpected'):
            with self.subTest(status=status):
                self.session.get.return_value.json.return_value = {'data': [
                    {'vmid': 101, 'name': 'Backup', 'status': status},
                    {'vmid': 102, 'name': 'Media', 'status': 'running'}]}
                self.assertEqual(self.client.guests('pve1', 'qemu'), [
                    {'vmid': 101, 'name': 'Backup', 'status': 'unknown', 'type': 'qemu'},
                    {'vmid': 102, 'name': 'Media', 'status': 'running', 'type': 'qemu'}])

    def setUp(self):
        self.session = Mock()
        self.client = ProxmoxStatus('https://example.test:8006', 'user@pve!test', 'secret', self.session)

    def test_non_finite_metrics_are_ignored_without_losing_valid_cpu(self):
        for value in (float('inf'), float('-inf'), float('nan'), True, '123'):
            for field in ('uptime', 'memory', 'rootfs'):
                with self.subTest(value=value, field=field):
                    metric = value if field == 'uptime' else {'used': value, 'total': 4096}
                    self.session.get.return_value.json.return_value = {'data': {'cpu': 0.5, field: metric}}
                    self.assertEqual(self.client.node('pve1'), {'node': 'pve1', 'cpu_percent': 50.0})

    def test_non_finite_totals_are_ignored(self):
        self.session.get.return_value.json.return_value = {'data': {
            'uptime': 60, 'memory': {'used': 1, 'total': float('inf')}, 'cpu': float('nan')}}
        self.assertEqual(self.client.node('pve1'), {'node': 'pve1', 'uptime_seconds': 60})
