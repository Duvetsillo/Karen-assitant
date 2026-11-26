CREATE TABLE IF NOT EXISTS core_music_tracks (
  track_id TEXT PRIMARY KEY, title TEXT NOT NULL, artist TEXT, album TEXT, platform TEXT NOT NULL,
  plays INTEGER NOT NULL DEFAULT 0, seconds REAL NOT NULL DEFAULT 0, repeats INTEGER NOT NULL DEFAULT 0,
  skips INTEGER NOT NULL DEFAULT 0, preference INTEGER NOT NULL DEFAULT 0, remembered INTEGER NOT NULL DEFAULT 0,
  last_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS core_music_plays (
  play_id TEXT PRIMARY KEY, track_id TEXT NOT NULL, started_at INTEGER NOT NULL,
  listened REAL NOT NULL DEFAULT 0, skipped INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS core_music_plays_time ON core_music_plays(started_at);
INSERT OR IGNORE INTO core_meta(key,value) VALUES('music_version','1');
