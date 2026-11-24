from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from maintenance import backup, verify


class MaintenanceTests(unittest.TestCase):
    def test_online_sqlite_backup_contains_committed_wal_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            private = root / '.private'
            private.mkdir(parents=True)
            path = private / 'history.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE sample(value TEXT)')
                db.execute("INSERT INTO sample VALUES('synthetic data')")
                db.commit()
                (private / 'credential.dpapi').write_bytes(b'opaque encrypted test bytes')
                (root / 'settings.json').write_text('{}')
                destination = Path(directory) / 'backup'
                count = backup(destination, root)
                self.assertEqual(verify(destination), count)
                restored = destination / 'user-data' / '.private' / 'history.sqlite3'
                with closing(sqlite3.connect(restored)) as copy:
                    self.assertEqual(copy.execute('SELECT value FROM sample').fetchone()[0], 'synthetic data')
                self.assertFalse((restored.parent / 'history.sqlite3-wal').exists())
                self.assertFalse((restored.parent / 'history.sqlite3-shm').exists())
                restored.write_bytes(b'corrupted')
                with self.assertRaises(ValueError): verify(destination)

    def test_never_overwrites_an_existing_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError): backup(directory, Path(directory) / 'source')
