"""Real temporary SQLite contract checks; no UI, microphones, or providers."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from conversations import Conversations
from core_events import CoreActivity, read_activity, read_events


class CoreEventTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'core.sqlite3'
        self.archive = Conversations(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_legacy_migration_preserves_data_and_event_sequence(self):
        chat = self.archive.create()
        self.archive.append(chat, 'Private prompt', 'Private answer', True)
        self.archive.set_voice_style('warm')
        with closing(sqlite3.connect(self.path)) as db:
            events = read_events(db)
        self.assertEqual([event['seq'] for event in events['events']], sorted(set(event['seq'] for event in events['events'])))
        self.assertIn('conversation', [event['topic'] for event in events['events']])
        self.assertNotIn('Private', json.dumps(events))
        Conversations(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(read_events(db, events['cursor'])['events'], [])
        self.assertEqual(self.archive.exchanges(chat), [('Private prompt', 'Private answer', 1)])

    def test_retention_gap_and_cursor_validation(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany("INSERT INTO core_events(topic,entity_id,action) VALUES('test',?,'changed')",
                           [(str(index),) for index in range(2100)])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM core_events').fetchone()[0], 2000)
            first = read_events(db)
            self.assertTrue(first['reset_required'])
            self.assertEqual(len(first['events']), 100)
            self.assertFalse(read_events(db, first['cursor'])['reset_required'])
            self.assertTrue(read_events(db, 99999)['reset_required'])
            for cursor in (-1, True, '0', 2**63):
                with self.assertRaises(ValueError): read_events(db, cursor)

    def test_activity_heartbeat_does_not_flood_events_or_expose_stale_clients(self):
        now = time.time()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO core_activity VALUES('test','classic','THINKING',?)", (now,))
            before = read_events(db)['cursor']
            db.execute("UPDATE core_activity SET updated_at=? WHERE client_id='test'", (now + 1,))
            self.assertEqual(read_events(db, before)['events'], [])
            self.assertEqual(read_activity(db, now + 1)['clients'][0]['state'], 'THINKING')
            self.assertEqual(read_activity(db, now + 17)['clients'], [])

    def test_background_activity_releases_on_orderly_shutdown(self):
        activity = CoreActivity(self.path)
        try:
            activity.set_state('SPEAKING')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                with closing(sqlite3.connect(self.path)) as db:
                    clients = read_activity(db)['clients']
                if clients and clients[0]['state'] == 'SPEAKING': break
                time.sleep(0.01)
            self.assertEqual(clients[0]['state'], 'SPEAKING')
        finally:
            activity.close()
            activity.thread.join(2)
        self.assertFalse(activity.thread.is_alive())
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(read_activity(db)['clients'], [])

    def test_chat_lifecycle_does_not_leave_orphaned_turns(self):
        chat = self.archive.create()
        self.archive.append(chat, 'proyecto Proxmox 100%', 'Seguimos el miércoles', True)
        self.assertEqual(self.archive.search('100%')[0][0], chat)
        self.assertEqual(self.archive.search('100_'), [])
        self.archive.rename(chat, 'Laboratorio')
        self.assertEqual(json.loads(self.archive.export_json(chat))['chat']['title'], 'Laboratorio')
        self.assertTrue(self.archive.delete(chat))
        self.assertFalse(self.archive.delete(chat))
        self.assertEqual(self.archive.exchanges(chat), [])
        with self.assertRaises(KeyError): self.archive.append(chat, 'late', 'late', True)
        with self.assertRaises(KeyError): self.archive.activate(chat)
        with self.assertRaises(KeyError): self.archive.export_json(chat)

    def test_first_turn_preserves_an_explicit_title(self):
        chat = self.archive.create()
        self.archive.rename(chat, 'Servidor pendiente')
        self.archive.append(chat, 'Primera pregunta', 'Respuesta', True)
        self.assertEqual(self.archive.list()[0][1], 'Servidor pendiente')


if __name__ == '__main__':
    unittest.main()
