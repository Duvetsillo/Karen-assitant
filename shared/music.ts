import type { Settings } from './types.js';
export const MUSIC_PLATFORMS = ['spotify', 'apple', 'youtube-music', 'youtube'] as const;
export type MusicPlatform = typeof MUSIC_PLATFORMS[number];
export interface MusicPreferences {
  musicEnabled: boolean; musicPlayer: boolean; musicPlatforms: MusicPlatform[];
  musicPlayerPinned: boolean;
  musicStrictYouTube: boolean; musicComments: boolean; musicCommentProbability: number;
  musicCommentVolume: number; musicCooldownMinutes: number; musicMaxComments: number;
  musicAnimations: boolean; musicGamingReactions: boolean; musicHistory: boolean; musicObsidian: boolean;
}
export const musicDefaults: MusicPreferences = {
  musicEnabled: false, musicPlayer: true, musicPlayerPinned: false, musicPlatforms: [...MUSIC_PLATFORMS], musicStrictYouTube: true,
  musicComments: false, musicCommentProbability: .1, musicCommentVolume: .6,
  musicCooldownMinutes: 35, musicMaxComments: 2, musicAnimations: true,
  musicGamingReactions: false, musicHistory: false, musicObsidian: false,
};
export type MusicControl = 'play' | 'pause' | 'next' | 'previous' | 'seek' | 'shuffle' | 'repeat' | 'volume';
export interface MediaSession {
  sessionId: string; trackId: string; source: string; title: string; artist?: string; album?: string;
  status: 'playing' | 'paused' | 'stopped'; position?: number; duration?: number; updatedAt: number;
  controls: MusicControl[]; shuffle?: boolean; repeat?: 'none' | 'track' | 'list';
  cover?: string; mediaType?: string; domain?: string; videoId?: string; category?: string;
  volume?: number;
  officialMusic?: boolean; platform?: MusicPlatform; evidence?: 'native' | 'browser';
}
export interface MusicSnapshot {
  enabled: boolean; status: 'off' | 'starting' | 'ready' | 'unavailable';
  sessions: MediaSession[]; activeId?: string; error?: string; comment?: { id: string; text: string; trackId: string };
  historyAvailable?: boolean;
  playerPinned?: boolean;
}
export interface MusicHistoryRow {
  trackId: string; title: string; artist?: string; album?: string; platform: string;
  plays: number; seconds: number; repeats: number; skips: number; preference: number; lastAt: number;
}
export type MusicAction = MusicControl | 'open' | 'close' | 'minimize' | 'pin' | 'select' | 'like' | 'dislike' | 'remember' | 'clear-history' | 'summary' | 'pair-browser' | 'revoke-browser';
export interface MusicRequest { action: MusicAction; sessionId?: string; trackId?: string; value?: number | boolean | string; relative?: boolean }
export interface MusicBridge {
  snapshot(): Promise<MusicSnapshot>;
  action(request: MusicRequest): Promise<unknown>;
  history(): Promise<MusicHistoryRow[]>;
  comment(id: string): Promise<{ text: string; trackId: string; audio: Uint8Array; volume: number } | undefined>;
}
/** Missing source evidence remains unknown. A title alone never establishes music. */
export function classifyMusic(session: MediaSession, strict = true): MusicPlatform | undefined {
  const source = session.source.toLowerCase(), domain = session.domain?.toLowerCase();
  const text = `${session.title} ${session.artist ?? ''}`.toLowerCase();
  if (/\b(podcast|tutorial|gameplay|interview|entrevista|audiobook|audiolibro|trailer|advertisement)\b/.test(text) || session.category === 'advertisement') return;
  if (session.category === 'podcast' || session.category === 'video') return;
  if (domain === 'open.spotify.com' || /^(?:spotify\.exe|spotifyab\.spotify(?:music)?[_!\.].*)$/.test(source)) {
    if (session.evidence === 'browser' && session.category !== 'music') return;
    if (session.evidence === 'native' && (!session.artist || !session.album || session.mediaType !== 'music')) return;
    return 'spotify';
  }
  if (domain === 'music.apple.com' || /^appleinc\.applemusic(?:win)?[_!\.]/.test(source) || source === 'applemusic.exe') return 'apple';
  if (domain === 'music.youtube.com') {
    // This service also hosts podcasts. The domain alone is not sufficient.
    if (session.category === 'Music' || session.category === '10') return 'youtube-music';
    return;
  }
  if (domain === 'www.youtube.com' || domain === 'youtube.com') {
    if (!session.videoId || !/^[\w-]{11}$/.test(session.videoId)) return;
    // YouTube's explicit category 10 is strong evidence. Official-channel flags
    // and title hints without the category are intentionally insufficient in strict mode.
    if (session.category === 'Music' || session.category === '10') return 'youtube';
    if (!strict && session.officialMusic && session.artist && session.mediaType === 'music') return 'youtube';
  }
}
export function validateMediaSession(raw: unknown, evidence: 'native' | 'browser'): MediaSession | undefined {
  if (!raw || typeof raw !== 'object') return;
  const r = raw as Record<string, unknown>;
  const string = (key: string, max = 500) => typeof r[key] === 'string' ? (r[key] as string).replace(/[\x00-\x1f]/g, '').slice(0, max) : undefined;
  const sessionId = string('sessionId', 180), trackId = string('trackId', 180), source = string('source', 180), title = string('title');
  if (!sessionId || !trackId || !source || !title || !['playing','paused','stopped'].includes(String(r.status)) || !Array.isArray(r.controls)) return;
  const controls = r.controls.filter((c): c is MusicControl => typeof c === 'string' && ['play','pause','next','previous','seek','shuffle','repeat','volume'].includes(c));
  const number = (key: string) => typeof r[key] === 'number' && Number.isFinite(r[key]) && (r[key] as number) >= 0 && (r[key] as number) <= 7 * 86400 ? r[key] as number : undefined;
  const cover = string('cover', 360000);
  return { sessionId, trackId, source, title, artist: string('artist'), album: string('album'),
    status: r.status as MediaSession['status'], controls: [...new Set(controls)], updatedAt: Date.now(),
    position: number('position'), duration: number('duration'), evidence,
    volume: number('volume') !== undefined && number('volume')! <= 1 ? number('volume') : undefined,
    cover: cover && /^data:image\/(?:jpeg|png);base64,[A-Za-z0-9+/=]+$/.test(cover) ? cover : undefined,
    mediaType: string('mediaType', 20), domain: string('domain', 60), videoId: string('videoId', 20), category: string('category', 40),
    officialMusic: r.officialMusic === true, shuffle: typeof r.shuffle === 'boolean' ? r.shuffle : undefined,
    repeat: ['none','track','list'].includes(String(r.repeat)) ? r.repeat as MediaSession['repeat'] : undefined };
}
export function chooseMusicSession(sessions: MediaSession[], selected?: string): MediaSession | undefined {
  return sessions.find(s => s.sessionId === selected) ?? sessions.find(s => s.status === 'playing') ?? sessions[0];
}
export function musicPosition(session: MediaSession, now: number): number | undefined {
  if (session.position === undefined) return;
  return Math.max(0, Math.min(session.duration ?? Infinity, session.position + (session.status === 'playing' ? Math.max(0, now - session.updatedAt) / 1000 : 0)));
}
export type MusicCommand = MusicRequest | { action: 'identify' } | { action: 'mute-comments' };
export function musicCommand(text: string): MusicCommand | undefined {
  const s = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
    .replace(/^(?:karen|caren)[,.:!]?\s+/, '').replace(/[¿?¡!.]+/g, '').trim();
  const commands: Record<string, MusicCommand> = {
    'que cancion esta sonando': { action: 'identify' }, 'pausa la musica': { action: 'pause' },
    'continua la musica': { action: 'play' }, 'siguiente cancion': { action: 'next' }, 'cancion anterior': { action: 'previous' },
    'sube el volumen': { action: 'volume', value: .1, relative: true }, 'baja el volumen': { action: 'volume', value: -.1, relative: true },
    'abre tu reproductor': { action: 'open' }, 'cierra tu reproductor': { action: 'close' },
    'no comentes la musica': { action: 'mute-comments' }, 'me gusta esta cancion': { action: 'like' },
    'no me gusta esta cancion': { action: 'dislike' }, 'recuerda esta cancion': { action: 'remember' },
  };
  return commands[s];
}
export const MUSIC_COMMENT_TEXTS = ['Me quedo por aquí, acompañando la música.', 'Una pequeña pausa musical.', 'Te acompaño en silencio un rato más.', 'La música sigue. Yo también estoy aquí.', 'Aquí estoy, disfrutando de este rato contigo.', 'Un poco de música para acompañarnos.'];
export interface MusicCommentContext {
  now: number; safeDesktop: boolean; present: boolean; callsKnownClear: boolean; conversation: boolean; voiceBusy: boolean; intro: boolean;
}
/** One Bernoulli evaluation per eligible play, with bounded in-session deduplication. */
export class MusicCommentEngine {
  private current = ''; private listened = 0; private lastTick = 0; private lastStatus = '';
  private evaluated = false; private seen = new Set<string>(); private emitted: number[] = [];
  private recent: number[] = []; private lastAt = 0;
  constructor(private random = Math.random) {}
  resetTrack() { this.current = ''; this.listened = 0; this.lastTick = 0; this.lastStatus = ''; this.evaluated = false; }
  tick(session: MediaSession | undefined, settings: Settings, c: MusicCommentContext): { text: string; trackId: string } | undefined {
    if (!session || session.status !== 'playing') { this.lastTick = c.now; this.lastStatus = session?.status ?? ''; return; }
    const key = `${session.sessionId}:${session.trackId}`;
    if (this.current !== key) { this.current = key; this.listened = 0; this.evaluated = false; this.lastTick = c.now; this.lastStatus = ''; }
    if (this.lastTick && this.lastStatus === 'playing') this.listened += Math.min(2, Math.max(0, c.now - this.lastTick) / 1000);
    this.lastTick = c.now; this.lastStatus = session.status;
    const blocked = !settings.musicComments || settings.mode !== 'normal' || !c.safeDesktop || !c.present || !c.callsKnownClear || c.conversation || c.voiceBusy || c.intro;
    if (blocked || this.listened < 45 || this.evaluated) return;
    this.evaluated = true;
    this.emitted = this.emitted.filter(at => c.now - at < 3 * 3600000);
    if (this.seen.has(session.trackId) || c.now - this.lastAt < settings.musicCooldownMinutes * 60000 || this.emitted.length >= settings.musicMaxComments || this.random() >= settings.musicCommentProbability) return;
    const choices = MUSIC_COMMENT_TEXTS.map((_, i) => i).filter(i => !this.recent.includes(i));
    const index = choices[Math.min(choices.length - 1, Math.floor(this.random() * choices.length))];
    this.recent = [...this.recent, index].slice(-3); this.seen.add(session.trackId);
    if (this.seen.size > 4096) this.seen.delete(this.seen.values().next().value!);
    this.lastAt = c.now; this.emitted.push(c.now);
    return { text: MUSIC_COMMENT_TEXTS[index], trackId: session.trackId };
  }
}
