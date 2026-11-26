import tempfile
import unittest
import threading
from datetime import datetime, timezone
from pathlib import Path
from karen_core2.memory import ContextMemory


class MusicMemoryTests(unittest.TestCase):
    def test_summary_is_registered_as_read_without_starting_the_runner(self):
        from karen_core2.runtime import CoreRuntime
        with tempfile.TemporaryDirectory() as root:
            runtime = CoreRuntime(archive_path=Path(root) / 'core.sqlite', task_path=Path(root) / 'tasks.sqlite')
            try:
                spec = runtime.plans.engine.tools['music_summary']
                self.assertEqual(spec.permission, 'read')
                spec.validate({})
                self.assertTrue(spec.verify({}, spec.handler({}, threading.Event())))
                now = datetime.now(timezone.utc).isoformat()
                recipe = {'goal': 'Resumen musical sintético', 'steps': [
                    {'id': 'read', 'label': 'Resumen musical local', 'tool': 'music_summary', 'args': {}, 'depends': []}]}
                runtime.automations.create(name='Resumen musical QA', recipe=recipe, due_at=now)
                self.assertEqual(runtime.automations.tick(now=now)['runs'][0]['status'], 'completed')
            finally:
                runtime.close()

    def test_music_is_read_only_and_empty_until_opt_in_schema_exists(self):
        with tempfile.TemporaryDirectory() as root:
            memory = ContextMemory(Path(root) / 'core.sqlite')
            self.assertEqual(memory.music.history(), [])
            with memory.base.connect() as db:
                self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='core_music_tracks'").fetchone())

    def test_shared_schema_reads_reported_metadata_without_promoting_observations(self):
        with tempfile.TemporaryDirectory() as root:
            memory = ContextMemory(Path(root) / 'core.sqlite')
            with memory.base.connect() as db:
                db.executescript('''INSERT INTO core_meta VALUES('music_version','1');
                    CREATE TABLE core_music_tracks(track_id TEXT,title TEXT,artist TEXT,album TEXT,
                    platform TEXT,plays INTEGER,seconds REAL,repeats INTEGER DEFAULT 0,skips INTEGER DEFAULT 0,
                    preference INTEGER,remembered INTEGER DEFAULT 0,last_at INTEGER);''')
                db.execute('''INSERT INTO core_music_tracks(track_id,title,platform,plays,seconds,preference,last_at)
                    VALUES('synthetic','Canción QA','spotify',2,45,0,1000)''')
            summary = memory.music.summary()
            self.assertEqual(summary['plays'], 2)
            self.assertEqual(summary['explicit_likes'], [])
            self.assertTrue(summary['reported_metadata'])
            with memory.base.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM core_memories').fetchone()[0], 0)
            with self.assertRaises(ValueError):
                memory.music.history(True)


if __name__ == '__main__':
    unittest.main()
