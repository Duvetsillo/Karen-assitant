import { readFileSync } from 'node:fs';
import type { DatabaseSync } from 'node:sqlite';
import type { MediaSession, MusicHistoryRow } from '../shared/music.js';

/** Uses the existing Core connection; listening never becomes a user preference. */
export class MusicMemory {
  constructor(private db: DatabaseSync) {
    const version = db.prepare("SELECT value FROM core_meta WHERE key='music_version'").get() as { value: string } | undefined;
    if (version && version.value !== '1') throw new Error('Memoria musical incompatible.');
    db.exec(readFileSync(new URL('../shared/music-schema.sql', import.meta.url), 'utf8'));
  }
  observe(session: MediaSession, playId: string, at: number, seconds: number, skipped: boolean) {
    if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86400) throw new Error('Duración escuchada inválida.');
    this.db.exec('BEGIN IMMEDIATE');
    try {
      this.track(session, at);
      const previous = this.db.prepare('SELECT listened,skipped FROM core_music_plays WHERE play_id=? AND track_id=?').get(playId, session.trackId) as { listened: number; skipped: number } | undefined;
      const delta = Math.max(0, seconds - (previous?.listened ?? 0));
      const old = this.db.prepare('SELECT plays FROM core_music_tracks WHERE track_id=?').get(session.trackId) as { plays: number };
      this.db.prepare(`INSERT INTO core_music_plays(play_id,track_id,started_at,listened,skipped) VALUES(?,?,?,?,?)
        ON CONFLICT(play_id) DO UPDATE SET listened=MAX(listened,excluded.listened),skipped=MAX(skipped,excluded.skipped)`)
        .run(playId, session.trackId, at, seconds, skipped ? 1 : 0);
      this.db.prepare(`UPDATE core_music_tracks SET seconds=seconds+?,plays=plays+?,repeats=repeats+?,skips=skips+?,last_at=? WHERE track_id=?`)
        .run(delta, previous ? 0 : 1, !previous && old.plays > 0 ? 1 : 0, skipped && !previous?.skipped ? 1 : 0, at, session.trackId);
      this.db.prepare('DELETE FROM core_music_plays WHERE play_id IN (SELECT play_id FROM core_music_plays ORDER BY started_at DESC LIMIT -1 OFFSET 10000)').run();
      this.db.exec('COMMIT');
    } catch (error) { this.db.exec('ROLLBACK'); throw error; }
  }
  private track(s: MediaSession, at: number) {
    this.db.prepare(`INSERT INTO core_music_tracks(track_id,title,artist,album,platform,last_at) VALUES(?,?,?,?,?,?)
      ON CONFLICT(track_id) DO UPDATE SET title=excluded.title,artist=excluded.artist,album=excluded.album,last_at=excluded.last_at`)
      .run(s.trackId, s.title, s.artist ?? null, s.album ?? null, s.platform ?? s.source, at);
  }
  preference(s: MediaSession, preference: -1 | 0 | 1 | undefined, remember: boolean) {
    this.track(s, Date.now());
    this.db.prepare('UPDATE core_music_tracks SET preference=COALESCE(?,preference),remembered=MAX(remembered,?) WHERE track_id=?').run(preference ?? null, remember ? 1 : 0, s.trackId);
  }
  history(): MusicHistoryRow[] {
    return this.db.prepare(`SELECT track_id AS trackId,title,artist,album,platform,plays,seconds,repeats,skips,preference,last_at AS lastAt
      FROM core_music_tracks ORDER BY last_at DESC LIMIT 200`).all() as unknown as MusicHistoryRow[];
  }
  summary() {
    const rows = this.history();
    const tracks = '# Preferencias musicales de Karen\n\nDatos locales reportados; escuchar no implica preferencia.\n\n' + rows.slice(0, 30).map(r => {
      const clean = (v: string) => v.replace(/[\r\n\[\]<>#`]/g, ' ').slice(0, 150);
      return `- ${clean(r.title)}${r.artist ? ' — ' + clean(r.artist) : ''}: ${r.plays} reproducciones, ${Math.round(r.seconds)} s; preferencia explícita: ${r.preference === 1 ? 'me gusta' : r.preference === -1 ? 'no me gusta' : 'sin indicar'}.`;
    }).join('\n');
    const artists = this.db.prepare(`SELECT artist,SUM(plays) AS plays,SUM(seconds) AS seconds FROM core_music_tracks
      WHERE artist IS NOT NULL AND artist<>'' GROUP BY artist ORDER BY seconds DESC LIMIT 10`).all() as { artist: string; plays: number; seconds: number }[];
    return tracks + '\n\n## Patrones observados\n\nFrecuencia acumulada, sin inferir gustos ni emociones:\n\n' + artists.map(a =>
      `- ${a.artist.replace(/[\r\n\[\]<>#`]/g, ' ').slice(0,150)}: ${a.plays} reproducciones y ${Math.round(a.seconds)} s estimados.`).join('\n');
  }
  clear() { this.db.exec('BEGIN IMMEDIATE; DELETE FROM core_music_plays; DELETE FROM core_music_tracks; COMMIT;'); }
}
