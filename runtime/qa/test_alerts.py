"""Persistent alert rules: only supplied readings can trigger notifications."""

from datetime import datetime, timedelta, timezone
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from karen_alerts import AlertEngine
from conversations import Conversations


BASE = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)


class AlertEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'alerts.sqlite3'
        self.engine = AlertEngine(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def observe(self, value, minute=0, *, source='pc', metric='disk_free_percent'):
        moment = BASE + timedelta(minutes=minute)
        return self.engine.observe(source, metric, value, now=moment)

    def test_dedup_ack_resolution_cooldown_and_restart(self):
        rule = self.engine.add_rule('pc', 'disk_free_percent', '<', 10,
                                    priority='high', cooldown_seconds=300)
        self.assertEqual(self.observe(12), [])
        first = self.observe(9, 1)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]['rule_id'], rule)
        self.assertEqual(self.observe(8, 2), [])
        self.assertTrue(self.engine.acknowledge(first[0]['id']))
        self.assertFalse(self.engine.acknowledge(first[0]['id']))
        restarted = AlertEngine(self.path)
        self.assertEqual(restarted.history(status='acknowledged')[0]['id'], first[0]['id'])
        self.assertEqual(self.observe(11, 3), [])
        self.assertEqual(self.engine.history(status='resolved')[0]['id'], first[0]['id'])
        self.assertEqual(self.observe(9, 4), [])  # still inside cooldown
        second = self.observe(8, 7)
        self.assertEqual(len(second), 1)
        self.assertNotEqual(second[0]['id'], first[0]['id'])
        self.assertEqual(len(self.engine.history()), 2)

    def test_quiet_hours_defer_normal_alert_but_critical_passes(self):
        self.engine.set_quiet_hours('19:00', '07:00')
        self.engine.add_rule('pc', 'disk_free_percent', '<', 10, priority='normal')
        self.engine.add_rule('pc', 'disk_free_percent', '<', 5, priority='critical')
        self.engine = AlertEngine(self.path)
        at_night = datetime(2026, 10, 28, 23, 0, tzinfo=timezone.utc)
        self.assertEqual(self.engine.observe('pc', 'disk_free_percent', 8, now=at_night), [])
        critical = self.engine.observe('pc', 'disk_free_percent', 4, now=at_night + timedelta(minutes=1))
        self.assertEqual([a['priority'] for a in critical], ['critical'])
        morning = datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
        deferred = self.engine.observe('pc', 'disk_free_percent', 4, now=morning)
        self.assertEqual([a['priority'] for a in deferred], ['normal'])
        self.assertEqual(self.engine.observe('pc', 'disk_free_percent', 4,
                                             now=morning + timedelta(minutes=1)), [])

    def test_gaming_persists_and_filters_noncritical(self):
        self.engine.add_rule('pc', 'disk_free_percent', '<', 10, priority='high')
        self.engine.add_rule('pc', 'disk_free_percent', '<', 5, priority='critical')
        self.engine.set_gaming(True)
        self.assertEqual(self.observe(8), [])
        critical = self.observe(4, 1)
        self.assertEqual([a['priority'] for a in critical], ['critical'])
        self.engine = AlertEngine(self.path)
        self.assertEqual(self.observe(4, 2), [])
        self.engine.set_gaming(False)
        self.assertEqual([a['priority'] for a in self.observe(4, 3)], ['high'])

    def test_shared_pet_mode_filters_normal_alerts_and_keeps_critical(self):
        core_path = Path(self.temp.name) / 'core.sqlite3'
        Conversations(core_path)
        self.engine.add_rule('pc', 'disk_free_percent', '<', 10, priority='high')
        self.engine.add_rule('pc', 'disk_free_percent', '<', 5, priority='critical')
        with patch.dict(os.environ, {'KAREN_CORE_DB': str(core_path)}):
            with closing(sqlite3.connect(core_path)) as db, db:
                db.execute("INSERT INTO preferences (key,value) VALUES ('core.mode','gaming')")
            self.assertEqual(self.observe(8), [])
            self.assertEqual([a['priority'] for a in self.observe(4, 1)], ['critical'])
            with closing(sqlite3.connect(core_path)) as db, db:
                db.execute("UPDATE preferences SET value='do_not_disturb' WHERE key='core.mode'")
            self.assertEqual(self.observe(4, 2), [])
            with closing(sqlite3.connect(core_path)) as db, db:
                db.execute("UPDATE preferences SET value='normal' WHERE key='core.mode'")
            self.assertEqual([a['priority'] for a in self.observe(4, 3)], ['high'])

    def test_missing_or_incompatible_core_does_not_block_local_alerts(self):
        self.engine.add_rule('pc', 'disk_free_percent', '<', 10, priority='high')
        missing = Path(self.temp.name) / 'missing.sqlite3'
        with patch.dict(os.environ, {'KAREN_CORE_DB': str(missing)}):
            self.assertEqual(len(self.observe(8)), 1)
        self.assertFalse(missing.exists())

    def test_stale_future_and_out_of_order_samples_do_not_change_state(self):
        self.engine.add_rule('pc', 'disk_free_percent', '<', 10)
        with self.assertRaises(ValueError):
            self.engine.observe('pc', 'disk_free_percent', 8,
                                observed_at=BASE - timedelta(minutes=6), now=BASE)
        with self.assertRaises(ValueError):
            self.engine.observe('pc', 'disk_free_percent', 8,
                                observed_at=BASE + timedelta(minutes=1), now=BASE)
        first = self.observe(8, 2)
        self.assertEqual(len(first), 1)
        # A late healthy reading must not resolve a newer breach.
        self.assertEqual(self.observe(20, 1), [])
        self.assertEqual(self.engine.history(status='active')[0]['id'], first[0]['id'])
        self.assertEqual(self.observe(20, 3), [])
        self.assertEqual(self.engine.history(status='active'), [])

    def test_disabled_rule_resolves_and_no_sensor_is_polled(self):
        self.assertEqual(self.observe(0), [])
        rule = self.engine.add_rule('pc', 'disk_free_percent', '<=', 10)
        first = self.observe(10, 1)
        self.assertEqual(len(first), 1)
        self.engine.set_rule_enabled(rule, False)
        self.assertEqual(self.engine.history(status='active'), [])
        self.assertEqual(self.observe(1, 2), [])
        self.assertFalse(self.engine.rules()[0]['enabled'])

    def test_source_can_be_disabled_across_rules_and_restart(self):
        self.engine.add_rule('pc', 'disk_free_percent', '<', 10)
        self.engine.add_rule('pc', 'cpu_percent', '>', 90)
        self.assertEqual(len(self.observe(8, 1)), 1)
        self.engine.set_source_enabled('pc', False)
        self.assertEqual(self.engine.history(status='active'), [])
        self.engine = AlertEngine(self.path)
        self.assertEqual(self.observe(7, 2), [])
        self.engine.set_source_enabled('pc', True)
        self.assertEqual(len(self.observe(7, 7)), 1)

    def test_validation_and_incompatible_schema(self):
        with self.assertRaises(ValueError):
            self.engine.add_rule('pc', 'disk_free_percent', '<', float('nan'))
        with self.assertRaises(ValueError):
            self.engine.add_rule('pc', 'disk_free_percent', '<', 10, priority='urgent')
        with self.assertRaises(ValueError):
            self.engine.observe('pc', 'disk_free_percent', True, now=BASE)
        with self.assertRaises(ValueError):
            self.engine.set_quiet_hours('25:00', '07:00')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE alert_meta SET value='99' WHERE key='schema_version'")
        with self.assertRaisesRegex(ValueError, 'no compatible'):
            AlertEngine(self.path)


if __name__ == '__main__':
    unittest.main()
