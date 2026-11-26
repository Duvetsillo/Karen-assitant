import { describe, expect, it } from 'vitest';
import { classifyMusic, validateMediaSession, musicCommand, MusicCommentEngine, chooseMusicSession, musicPosition, type MediaSession, type MusicCommentContext } from '../shared/music';
import { defaults, validateSettings } from '../shared/settings';
import { canSendMessage } from '../shared/local-commands';

const song = (patch: Partial<MediaSession> = {}): MediaSession => ({ sessionId: 's1', trackId: 't1', source: 'Spotify.exe', title: 'Canción de prueba', artist: 'Artista sintético', album: 'Álbum QA', mediaType: 'music', evidence: 'native', status: 'playing', controls: ['play','pause'], position: 0, duration: 180, updatedAt: 1000, ...patch });
const context = (now: number, patch: Partial<MusicCommentContext> = {}): MusicCommentContext => ({ now, safeDesktop: true, callsKnownClear: true, present: true, voiceBusy: false, conversation: false, intro: false, ...patch });
describe('music classification and commands', () => {
  it('requires positive web evidence and excludes non-music and ambiguous YouTube', () => {
    expect(classifyMusic(song())).toBe('spotify');
    expect(classifyMusic(song({ source: 'AppleInc.AppleMusicWin_test!App' }))).toBe('apple');
    expect(classifyMusic(song({ domain: 'music.youtube.com', evidence: 'browser', source: 'browser', category: 'Music' }))).toBe('youtube-music');
    expect(classifyMusic(song({ domain: 'music.youtube.com', evidence: 'browser', source: 'browser' }))).toBeUndefined();
    const youtube = song({ source: 'browser', evidence: 'browser', domain: 'www.youtube.com', videoId: 'abcdefghijk' });
    expect(classifyMusic(youtube)).toBeUndefined();
    expect(classifyMusic({ ...youtube, category: 'Music' })).toBe('youtube');
    for (const title of ['Gameplay musical', 'Tutorial de guitarra', 'Podcast de hoy', 'Entrevista con artista']) expect(classifyMusic({ ...youtube, title, category: 'Music' })).toBeUndefined();
    expect(classifyMusic({ ...youtube, category: 'Gaming' })).toBeUndefined();
    expect(classifyMusic(song({ source: 'chrome.exe' }))).toBeUndefined();
    expect(classifyMusic(song({ category: 'podcast' }))).toBeUndefined();
    expect(classifyMusic(song({ evidence: 'browser', source: 'browser', domain: 'open.spotify.com', category: 'unknown' }))).toBeUndefined();
  });
  it('rejects malformed metadata and unsupported image URLs', () => {
    expect(validateMediaSession({ ...song(), title: null }, 'native')).toBeUndefined();
    expect(validateMediaSession({ ...song(), position: NaN, cover: 'https://evil.invalid/x', controls: ['pause','shell'] }, 'native')).toMatchObject({ controls: ['pause'], position: undefined, cover: undefined });
    expect(musicPosition(song(), 6000)).toBe(5); expect(musicPosition(song({ status: 'paused' }), 6000)).toBe(0);
    expect(chooseMusicSession([song({ sessionId: 'a', status: 'paused' }), song({ sessionId: 'b' })])?.sessionId).toBe('b');
    expect(chooseMusicSession([song({ sessionId: 'a', status: 'paused' }), song({ sessionId: 'b' })], 'a')?.sessionId).toBe('a');
  });
  it('routes every requested voice command offline and persists opt-in preferences', () => {
    for (const text of ['¿qué canción está sonando?', 'pausa la música', 'continúa la música', 'siguiente canción', 'canción anterior', 'sube el volumen', 'baja el volumen', 'abre tu reproductor', 'cierra tu reproductor', 'no comentes la música', 'me gusta esta canción', 'no me gusta esta canción', 'recuerda esta canción']) {
      expect(musicCommand(`Karen, ${text}`)).toBeDefined(); expect(canSendMessage(`Karen, ${text}`, 'disconnected')).toBe(true);
    }
    expect(musicCommand('Me dijo que pausa la música')).toBeUndefined();
    expect(defaults.musicEnabled).toBe(false); expect(defaults.musicHistory).toBe(false);
    expect(validateSettings(JSON.parse(JSON.stringify({ ...defaults, musicEnabled: true, musicPlatforms: ['spotify'] })))).toMatchObject({ musicEnabled: true, musicPlatforms: ['spotify'] });
    expect(() => validateSettings({ musicPlatforms: ['anything' as never] })).toThrow();
    expect(() => validateSettings({ musicCommentProbability: NaN })).toThrow();
  });
});
describe('spontaneous music policy', () => {
  const settings = { ...defaults, musicComments: true, musicCommentProbability: 1 };
  const listen = (engine: MusicCommentEngine, s: MediaSession, start: number, patch: Partial<MusicCommentContext> = {}) => {
    let result;
    for (let i = 0; i <= 46; i++) result = engine.tick(s, settings, context(start + i * 1000, patch)) ?? result;
    return result;
  };
  it('waits 45 listening seconds, evaluates only once, deduplicates songs and enforces cooldown', () => {
    const engine = new MusicCommentEngine(() => 0), start = 10 * 3600000;
    for (let i = 0; i < 45; i++) expect(engine.tick(song(), settings, context(start + i * 1000))).toBeUndefined();
    expect(engine.tick(song(), settings, context(start + 45000))?.trackId).toBe('t1');
    expect(listen(engine, song({ trackId: 't2' }), start + 60000)).toBeUndefined();
    expect(listen(engine, song(), start + 40 * 60000)).toBeUndefined();
    expect(listen(engine, song({ trackId: 't3' }), start + 80 * 60000)).toBeDefined();
    expect(listen(engine, song({ trackId: 't4' }), start + 120 * 60000)).toBeUndefined(); // two per three hours
  });
  it('blocks calls, unknown calls, intros, conversations, absent users and other voice', () => {
    for (const blocked of [{ callsKnownClear: false }, { intro: true }, { conversation: true }, { present: false }, { voiceBusy: true }, { safeDesktop: false }]) {
      expect(listen(new MusicCommentEngine(() => 0), song(), 10 * 3600000, blocked)).toBeUndefined();
    }
    const engine = new MusicCommentEngine(() => 0);
    for (let i = 0; i < 50; i++) expect(engine.tick(song(), { ...settings, mode: 'gaming' }, context(10 * 3600000 + i * 1000))).toBeUndefined();
  });
  it('does not count paused time, stalled ticks or a previous song toward a new song', () => {
    const engine = new MusicCommentEngine(() => 0), start = 10 * 3600000;
    engine.tick(song(), settings, context(start)); engine.tick(song(), settings, context(start + 3600000));
    expect(engine.tick(song(), settings, context(start + 3601000))).toBeUndefined();
    expect(engine.tick(song({ status: 'paused' }), settings, context(start + 3602000))).toBeUndefined();
    expect(engine.tick(song({ trackId: 'changed' }), settings, context(start + 7200000))).toBeUndefined();
  });
});
