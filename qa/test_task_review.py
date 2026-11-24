"""Manual task audit CLI with temporary data and no system tools."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from karen_tasks import TaskEngine, ToolSpec
from task_review import main


class TaskReviewTests(unittest.TestCase):
    def test_cli_needs_exact_id_before_recording_human_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tasks.sqlite3'
            engine = TaskEngine({'change': ToolSpec('sensitive', lambda _a, _s: None)}, path)
            identity = engine.create([{'tool': 'change', 'args': {}}])
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE task_jobs SET status='uncertain' WHERE id=?", (identity,))
            with patch('sys.stdout'), patch('sys.stderr'):
                self.assertEqual(main(['--db', str(path), 'list']), 0)
                with self.assertRaises(SystemExit) as declined:
                    main(['--db', str(path), 'review', identity, 'applied'], confirm=lambda _: 'wrong')
                self.assertEqual(declined.exception.code, 2)
                self.assertEqual(engine.inspect(identity)['status'], 'uncertain')
                self.assertEqual(main(['--db', str(path), 'review', identity, 'applied'],
                                      confirm=lambda _: identity), 0)
            self.assertEqual(TaskEngine({}, path).inspect(identity)['status'], 'reviewed_applied')


if __name__ == '__main__':
    unittest.main()
