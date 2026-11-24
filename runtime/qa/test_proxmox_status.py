"""Proxmox read-only contract and local routing."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from conversations import Conversations
from karen_app import KarenClient
from proxmox_status import ProxmoxStatus


class ProxmoxStatusTests(unittest.TestCase):
    def test_node_status_uses_https_get_and_reduces_response(self):
        session = Mock()
        session.get.return_value.json.return_value = {'data': {
            'uptime': 3600, 'cpu': 0.25,
            'memory': {'used': 2048, 'total': 4096},
            'rootfs': {'used': 1024, 'total': 8192},
            'sensitive_extra': 'discard',
        }}
        client = ProxmoxStatus('https://127.0.0.1:8006', 'user@pve!karen', 'secret', session)
        self.assertEqual(client.node('pve1'), {
            'node': 'pve1', 'uptime_seconds': 3600, 'cpu_percent': 25.0,
            'memory_used_bytes': 2048, 'memory_total_bytes': 4096,
            'rootfs_used_bytes': 1024, 'rootfs_total_bytes': 8192,
        })
        self.assertEqual(session.get.call_args.args[0],
                         'https://127.0.0.1:8006/api2/json/nodes/pve1/status')
        self.assertEqual(session.get.call_args.kwargs['headers']['Authorization'],
                         'PVEAPIToken=user@pve!karen=secret')
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            ProxmoxStatus('http://127.0.0.1:8006', 'user@pve!karen', 'secret', session).node('pve1')
        with self.assertRaisesRegex(ValueError, 'inválido'):
            client.node('../other')
        self.assertEqual(session.get.call_count, 1)

    def test_proxmox_command_stays_local_and_out_of_history(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat = archive.create()
            client = KarenClient('http://127.0.0.1:11434')
            client.archive, client.chat_id = archive, chat
            with (patch('karen_app.ProxmoxStatus') as status,
                  patch('karen_app.requests.post', side_effect=AssertionError('No enviar al modelo')),
                  patch.object(client.home, 'execute', side_effect=AssertionError('No llamar HA'))):
                status.return_value.node.return_value = {'node': 'pve1', 'cpu_percent': 25.0}
                self.assertIn('cpu_percent: 25.0', client.ask('/proxmox nodo pve1'))
                status.return_value.guests.return_value = [{'vmid': 101, 'name': 'Jellyfin', 'status': 'running'}]
                self.assertIn('101 Jellyfin: running', client.ask('/proxmox contenedores pve1'))
                status.return_value.cluster.return_value = {'cluster': 'lab', 'quorate': True}
                self.assertIn('quorate: True', client.ask('/proxmox quorum'))
                status.return_value.storage.return_value = [{'storage': 'local', 'active': True, 'avail_bytes': 2 * 1024 ** 3}]
                self.assertIn('local: activo: sí, disponible: 2.00 GiB', client.ask('/proxmox almacenamiento pve1'))
                self.assertIn('no pude consultar', client.ask('/proxmox nodo ../otro'))
                status.return_value.node.assert_called_once_with('pve1')
                status.return_value.guests.assert_called_once_with('pve1', 'lxc')
                status.return_value.cluster.assert_called_once_with()
                status.return_value.storage.assert_called_once_with('pve1')
            self.assertEqual(archive.exchanges(chat), [])

    def test_guest_inventory_filters_unexpected_fields_and_limits_rows(self):
        session = Mock()
        session.get.return_value.json.return_value = {'data': [
            {'vmid': 101, 'name': 'Jellyfin\n  TV', 'status': 'running', 'secret': 'discard'},
            {'vmid': True, 'name': 'Invalid', 'status': 'running'},
            {'vmid': 102, 'name': 'Backup', 'status': 'unavailable'},
        ]}
        client = ProxmoxStatus('https://127.0.0.1:8006', 'user@pve!karen', 'secret', session)
        self.assertEqual(client.guests('pve1', 'lxc'), [
            {'vmid': 101, 'name': 'Jellyfin TV', 'status': 'running', 'type': 'lxc'},
            {'vmid': 102, 'name': 'Backup', 'status': 'unknown', 'type': 'lxc'},
        ])
        self.assertTrue(session.get.call_args.args[0].endswith('/nodes/pve1/lxc'))
        with self.assertRaisesRegex(ValueError, 'inválido'):
            client.guests('pve1', 'disk')

    def test_cluster_quorum_requires_explicit_api_value(self):
        session = Mock()
        client = ProxmoxStatus('https://127.0.0.1:8006', 'user@pve!karen', 'secret', session)
        session.get.return_value.json.return_value = {'data': [
            {'type': 'node', 'name': 'pve1', 'online': 1},
            {'type': 'cluster', 'name': 'Home\n Lab', 'quorate': 1, 'nodes': 2, 'secret': 'discard'},
        ]}
        self.assertEqual(client.cluster(), {'cluster': 'Home Lab', 'quorate': True, 'nodes': 2})
        self.assertTrue(session.get.call_args.args[0].endswith('/cluster/status'))
        self.assertEqual(session.get.call_args.kwargs['timeout'], (2.0, 8.0))
        session.get.return_value.json.return_value = {'data': [{'type': 'cluster', 'name': 'lab'}]}
        with self.assertRaisesRegex(ValueError, 'quorum verificable'):
            client.cluster()

    def test_storage_inventory_filters_unknown_fields_and_missing_metrics(self):
        session = Mock()
        session.get.return_value.json.return_value = {'data': [
            {'storage': 'local', 'active': 1, 'used': 1024, 'avail': 2048, 'total': 3072, 'token': 'discard'},
            {'storage': '../invalid', 'active': 1},
            {'storage': 'unknown', 'active': 'yes'},
            {'storage': 'offline', 'active': 0, 'avail': -1},
        ]}
        client = ProxmoxStatus('https://127.0.0.1:8006', 'user@pve!karen', 'secret', session)
        self.assertEqual(client.storage('pve1'), [
            {'storage': 'local', 'active': True, 'used_bytes': 1024, 'avail_bytes': 2048, 'total_bytes': 3072},
            {'storage': 'offline', 'active': False},
        ])
        self.assertTrue(session.get.call_args.args[0].endswith('/nodes/pve1/storage'))


if __name__ == '__main__':
    unittest.main()
