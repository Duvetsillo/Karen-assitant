"""Read-only musical observations in the existing MemoryStore, never implicit tastes."""
class MusicMemory:
    def __init__(self, base):
        self.base = base

    def history(self, limit=200):
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('Límite musical inválido.')
        with self.base.connect() as db:
            version = db.execute("SELECT value FROM core_meta WHERE key='music_version'").fetchone()
            if not version:
                return []
            if version[0] != '1':
                raise ValueError('Versión de memoria musical incompatible.')
            rows = db.execute('''SELECT track_id,title,artist,album,platform,plays,seconds,repeats,
                skips,preference,remembered,last_at FROM core_music_tracks ORDER BY last_at DESC LIMIT ?''', (limit,)).fetchall()
            return [dict(row) for row in rows]

    def summary(self):
        rows = self.history()
        return {'tracks': len(rows), 'plays': sum(row['plays'] for row in rows),
                'estimated_listening_seconds': sum(row['seconds'] for row in rows),
                'explicit_likes': [row for row in rows if row['preference'] == 1],
                'explicit_dislikes': [row for row in rows if row['preference'] == -1],
                'reported_metadata': True, 'bounded_to_recent': 200}
