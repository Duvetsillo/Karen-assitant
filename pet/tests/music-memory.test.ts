import { describe, expect, it } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import { MusicMemory } from '../electron/music-memory';
import type { MediaSession } from '../shared/music';

const song: MediaSession = { sessionId: 'synthetic', trackId: 'synthetic-track', title: 'Prueba', artist: 'Artista QA', album: 'Álbum QA', platform: 'spotify', source: 'fixture', status: 'playing', updatedAt: 0, controls: [] };
describe('music memory uses existing Core connection', () => {
  it('counts incremental listening idempotently without inferring a preference', () => {
    const db = new DatabaseSync(':memory:'); db.exec('CREATE TABLE core_meta(key TEXT PRIMARY KEY,value TEXT)');
    try {
      const memory = new MusicMemory(db);
      memory.observe(song, 'play-1', 1000, 15, false);
      memory.observe(song, 'play-1', 1000, 30, false);
      memory.observe(song, 'play-1', 1000, 30, false);
      expect(memory.history()[0]).toMatchObject({ plays: 1, seconds: 30, preference: 0, repeats: 0 });
      memory.observe(song, 'play-2', 2000, 15, true);
      memory.observe(song, 'play-2', 2000, 15, true);
      expect(memory.history()[0]).toMatchObject({ plays: 2, seconds: 45, skips: 1, repeats: 1, preference: 0 });
      memory.preference(song, 1, false); memory.preference(song, undefined, true);
      expect(memory.history()[0].preference).toBe(1);
      expect(memory.summary()).toContain('me gusta');
      memory.clear(); expect(memory.history()).toEqual([]);
      expect(() => memory.observe(song, 'bad', 1000, NaN, false)).toThrow();
    } finally { db.close(); }
  });
});
