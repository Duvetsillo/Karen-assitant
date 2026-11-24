"""Real probe adapter and optional headless alert loop."""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from alert_monitor import check_cpu, check_disk, check_memory, check_pc, main, watch_disk
from karen_alerts import AlertEngine
from conversations import Conversations
from karen_app import KarenClient


def quarter_free(_args, _stop):
    return {'drive': 'C:', 'disk_total_bytes': 100, 'disk_free_bytes': 25}


class AlertMonitorTests(unittest.TestCase):
    def test_cpu_and_ram_rules_use_real_probe_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = AlertEngine(Path(directory) / 'alerts.sqlite3')
            engine.add_rule('pc', 'cpu_percent', '>', 80)
            engine.add_rule('pc', 'ram_available_percent', '<', 15)
            cpu = lambda _a, _s: {'cpu_percent': 91.2}
            memory = lambda _a, _s: {'ram_total_bytes': 1000, 'ram_available_bytes': 100}
            self.assertEqual(len(check_cpu(engine, cpu)['alerts']), 1)
            self.assertEqual(len(check_memory(engine, memory)['alerts']), 1)
            self.assertEqual(check_cpu(engine, cpu)['alerts'], [])
            self.assertEqual(check_memory(engine, memory)['alerts'], [])
            self.assertEqual(len(engine.history(status='active')), 2)

    def test_invalid_cpu_and_ram_samples_do_not_trigger(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = AlertEngine(Path(directory) / 'alerts.sqlite3')
            engine.add_rule('pc', 'cpu_percent', '>', 80)
            engine.add_rule('pc', 'ram_available_percent', '<', 15)
            for value in (True, float('nan'), 101, -1):
                with self.assertRaises(ValueError):
                    check_cpu(engine, lambda _a, _s: {'cpu_percent': value})
            for total, free in ((0, 0), (100, 101), (100, True), (-1, 0)):
                with self.assertRaises(ValueError):
                    check_memory(engine, lambda _a, _s: {
                        'ram_total_bytes': total, 'ram_available_bytes': free})
            self.assertEqual(engine.history(), [])

    def test_pc_check_preserves_valid_sources_when_cpu_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = AlertEngine(Path(directory) / 'alerts.sqlite3')
            engine.add_rule('pc', 'disk_free_percent', '<', 30)
            engine.add_rule('pc', 'ram_available_percent', '<', 15)
            with patch('alert_monitor.check_disk', side_effect=lambda e: check_disk(e, quarter_free)), \
                 patch('alert_monitor.check_cpu', side_effect=OSError('CPU no disponible')), \
                 patch('alert_monitor.check_memory', side_effect=lambda e: check_memory(
                     e, lambda _a, _s: {'ram_total_bytes': 100, 'ram_available_bytes': 10})):
                result = check_pc(engine)
            self.assertEqual(len(result['alerts']), 2)
            self.assertEqual(set(result['measurements']), {'disk', 'memory'})
            self.assertEqual(result['errors'], {'cpu': 'CPU no disponible'})

    def test_cli_creates_cpu_and_ram_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'alerts.sqlite3'
            with patch('sys.stdout'):
                self.assertEqual(main(['--db', str(path), 'add-cpu-rule', '>', '85']), 0)
                self.assertEqual(main(['--db', str(path), 'add-memory-rule', '<', '12']), 0)
            self.assertEqual({r['metric'] for r in AlertEngine(path).rules()},
                             {'cpu_percent', 'ram_available_percent'})

    def test_cli_disables_and_restores_rule_and_source_without_history_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'alerts.sqlite3'
            engine = AlertEngine(path)
            rule_id = engine.add_rule('pc', 'disk_free_percent', '<', 30)
            self.assertEqual(len(check_disk(engine, quarter_free)['alerts']), 1)
            with patch('sys.stdout'):
                self.assertEqual(main(['--db', str(path), 'rule', rule_id, 'off']), 0)
                self.assertEqual(main(['--db', str(path), 'rule', rule_id, 'on']), 0)
                self.assertEqual(main(['--db', str(path), 'source', 'pc', 'off']), 0)
            self.assertEqual(len(engine.history(status='resolved')), 1)
            self.assertEqual(check_disk(engine, quarter_free)['alerts'], [])
            with patch('sys.stdout'):
                self.assertEqual(main(['--db', str(path), 'source', 'pc', 'on']), 0)
            self.assertTrue(AlertEngine(path).rules()[0]['enabled'])
            self.assertEqual(len(check_disk(engine, quarter_free)['alerts']), 0)  # cooldown
            self.assertEqual(len(engine.history()), 1)

    def test_disk_measurement_creates_one_persistent_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'alerts.sqlite3'
            engine = AlertEngine(path)
            engine.add_rule('pc', 'disk_free_percent', '<', 30, priority='high')
            result = check_disk(engine, quarter_free)
            self.assertEqual(result['disk_free_percent'], 25)
            self.assertEqual(len(result['alerts']), 1)
            self.assertEqual(check_disk(engine, quarter_free)['alerts'], [])
            self.assertEqual(len(AlertEngine(path).history(status='active')), 1)

    def test_watch_stops_after_alert_without_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = AlertEngine(Path(directory) / 'alerts.sqlite3')
            engine.add_rule('pc', 'disk_free_percent', '<', 30)
            stop, alerts = threading.Event(), []
            def emit(alert):
                alerts.append(alert)
                stop.set()
            watch_disk(engine, 10, stop, emit, quarter_free)
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]['value'], 25.0)

    def test_invalid_disk_measurement_cannot_create_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = AlertEngine(Path(directory) / 'alerts.sqlite3')
            engine.add_rule('pc', 'disk_free_percent', '<', 30)
            with self.assertRaises(ValueError):
                check_disk(engine, lambda _a, _s: {
                    'drive': 'C:', 'disk_total_bytes': 0, 'disk_free_bytes': 0})
            self.assertEqual(engine.history(), [])

    def test_classic_alert_commands_stay_local_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            alert_path = Path(directory) / 'alerts.sqlite3'
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat_id = archive.current()
            client = KarenClient('http://localhost:11434')
            client.archive, client.chat_id = archive, chat_id
            public, private = Mock(), Mock()
            with patch('karen_alerts.DEFAULT_PATH', alert_path), \
                 patch('alert_monitor.check_disk', side_effect=lambda engine: check_disk(engine, quarter_free)), \
                 patch('karen_app.requests.post') as post:
                engine = AlertEngine()
                engine.add_rule('pc', 'disk_free_percent', '<', 30, label='Disco bajo')
                self.assertIn('Alertas nuevas: 1', client.ask('/alertas disco', public, private))
                self.assertIn('Alertas nuevas: 0', client.ask('/alertas disco', public, private))
                self.assertIn('Disco bajo', client.ask('/alertas historial', public, private))
                alert_id = engine.history()[0]['id']
                self.assertEqual(client.ask(f'/alertas confirmar {alert_id}', public, private),
                                 'Alerta confirmada.')
                post.assert_not_called()
            public.assert_not_called()
            self.assertEqual(private.call_count, 4)
            self.assertEqual(archive.exchanges(chat_id), [])

    def test_classic_pc_alerts_report_partial_failure_without_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'alerts.sqlite3'
            archive = Conversations(Path(directory) / 'core.sqlite3')
            chat_id = archive.current()
            client = KarenClient('http://localhost:11434')
            client.archive, client.chat_id = archive, chat_id
            private = Mock()
            with patch('karen_alerts.DEFAULT_PATH', path), \
                 patch('alert_monitor.check_disk', side_effect=lambda e: check_disk(e, quarter_free)), \
                 patch('alert_monitor.check_cpu', side_effect=OSError('CPU no disponible')), \
                 patch('alert_monitor.check_memory', side_effect=lambda e: check_memory(
                     e, lambda _a, _s: {'ram_total_bytes': 100, 'ram_available_bytes': 10})), \
                 patch('karen_app.requests.post') as post:
                AlertEngine(path).add_rule('pc', 'ram_available_percent', '<', 15)
                answer = client.ask('/alertas pc', on_private_sentence=private)
                post.assert_not_called()
            self.assertIn('RAM disponible: 10.00%', answer)
            self.assertIn('Lecturas fallidas: cpu', answer)
            self.assertIn('Alertas nuevas: 1', answer)
            private.assert_called_once_with(answer)
            self.assertEqual(archive.exchanges(chat_id), [])


if __name__ == '__main__':
    unittest.main()
