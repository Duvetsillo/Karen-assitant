import { randomUUID } from 'node:crypto';
import { join } from 'node:path';
import type { Settings } from '../shared/types.js';
import { MusicCommentEngine, chooseMusicSession, classifyMusic, type MediaSession, type MusicCommentContext, type MusicRequest, type MusicSnapshot } from '../shared/music.js';
import { WindowsMediaAdapter } from './music-adapter.js';
import { MusicBrowserHub } from './music-browser.js';
import type { MusicMemory } from './music-memory.js';
import { GreetingLibrary, ResourceCache, greetingVoiceVersion } from './greeting-library.js';

export class MusicPresence {
  private adapter: WindowsMediaAdapter;
  private browser?: MusicBrowserHub;
  private native: MediaSession[] = []; private web: MediaSession[] = [];
  private state: MusicSnapshot = { enabled: false, status: 'off', sessions: [] };
  private selected?: string; private timer?: ReturnType<typeof setInterval>; private ticking = false;
  private comments = new MusicCommentEngine(); private epoch = 0;
  private play?: { session: MediaSession; id: string; seconds: number; tick: number; saved: number; started: number };
  constructor(private options: {
    executable: string; directory: string; settings: () => Settings; token: () => string | undefined;
    context: () => Omit<MusicCommentContext, 'safeDesktop' | 'callsKnownClear'>;
    memory: () => MusicMemory | undefined; publish: (state: MusicSnapshot) => void;
  }) { this.adapter = new WindowsMediaAdapter(options.executable, (sessions, error) => { this.native = sessions; this.refresh(error); }); }
  snapshot() { return this.state; }
  private memory() { try { return this.options.memory(); } catch { return undefined; } }
  preferencesChanged() { if (!this.options.settings().musicComments) this.state.comment = undefined; this.refresh(); }
  configure() {
    this.stop();
    const s = this.options.settings();
    if (!s.musicEnabled) { this.refresh(); return; }
    this.state = { enabled: true, status: 'starting', sessions: [] }; this.options.publish(this.state);
    this.adapter.start();
    const token = this.options.token();
    if (token) {
      this.browser = new MusicBrowserHub(token, (sessions, error) => { this.web = sessions; this.refresh(error); });
      this.browser.start();
    }
  }
  private eligible() {
    const s = this.options.settings();
    return [...this.native, ...this.web].flatMap(session => {
      const platform = classifyMusic(session, s.musicStrictYouTube);
      return platform && s.musicPlatforms.includes(platform) ? [{ ...session, platform }] : [];
    });
  }
  private refresh(error?: string) {
    const settings = this.options.settings();
    const sessions = settings.musicEnabled ? this.eligible() : [];
    const active = chooseMusicSession(sessions, this.selected);
    const previous = this.play;
    const changed = previous && (!active || active.trackId !== previous.session.trackId || active.sessionId !== previous.session.sessionId);
    if (changed) { this.save(false); this.play = undefined; this.comments.resetTrack(); }
    if (active && !this.play) this.play = { session: active, id: randomUUID(), seconds: 0, tick: Date.now(), saved: 0, started: Date.now() };
    if (active && this.play) this.play.session = active;
    if (active?.status !== 'playing') this.comments.tick(active, settings, { ...this.options.context(), safeDesktop: false, callsKnownClear: false });
    this.state = { enabled: settings.musicEnabled, status: !settings.musicEnabled ? 'off' : error ? 'unavailable' : 'ready',
      sessions, activeId: active?.sessionId, error, historyAvailable: Boolean(this.memory()), playerPinned: settings.musicPlayerPinned,
      comment: !changed && this.state.comment?.trackId === active?.trackId ? this.state.comment : undefined };
    this.options.publish(this.state);
    if (active?.status === 'playing' && !this.timer) this.timer = setInterval(() => { void this.tick(); }, 1000);
    else if (active?.status !== 'playing' && this.timer) { clearInterval(this.timer); this.timer = undefined; this.save(false); }
  }
  private save(skipped: boolean) {
    if (!this.play || !this.options.settings().musicHistory) return;
    try {
      this.memory()?.observe(this.play.session, this.play.id, this.play.started, this.play.seconds, skipped);
      this.play.saved = this.play.seconds;
    } catch { this.state = { ...this.state, error: 'No se pudo guardar el historial musical.' }; this.options.publish(this.state); }
  }
  private async tick() {
    if (this.ticking) return;
    this.ticking = true; const epoch = this.epoch;
    try {
      const web = this.browser?.snapshot();
      if (web && web.length !== this.web.length) { this.web = web; this.refresh(); }
      const p = this.play, settings = this.options.settings(), now = Date.now();
      if (!p || p.session.status !== 'playing') return;
      p.seconds += Math.min(2, Math.max(0, now - p.tick) / 1000); p.tick = now;
      if (p.seconds - p.saved >= 15) this.save(false);
      if (!settings.musicComments) return;
      const desktop = await this.adapter.context();
      if (epoch !== this.epoch || this.play !== p) return;
      const context = this.options.context();
      if (this.state.comment && (!desktop.safeDesktop || !desktop.callsClear || !context.present || context.intro || settings.mode !== 'normal')) {
        this.state = { ...this.state, comment: undefined }; this.options.publish(this.state);
      }
      const comment = this.comments.tick(p.session, settings, { ...context, safeDesktop: desktop.safeDesktop === true, callsKnownClear: desktop.callsClear === true });
      if (comment) { this.state = { ...this.state, comment: { ...comment, id: randomUUID() } }; this.options.publish(this.state); }
    } finally { this.ticking = false; }
  }
  async commentAudio(id: string) {
    const notice = this.state.comment, active = chooseMusicSession(this.state.sessions, this.state.activeId);
    const s = this.options.settings(), context = this.options.context();
    if (!notice || notice.id !== id || active?.trackId !== notice.trackId || active.status !== 'playing' || !s.musicComments || !s.voiceEnabled || s.mode !== 'normal' || !context.present || context.voiceBusy || context.conversation || context.intro) return;
    const desktop = await this.adapter.context();
    if (!desktop.safeDesktop || !desktop.callsClear || this.state.comment !== notice) return;
    const cache = new ResourceCache();
    try {
      const version = greetingVoiceVersion(s, s.voiceRoot || process.env.KAREN_PROJECT_ROOT || join(this.options.directory, 'voice'));
      const { audio } = new GreetingLibrary(join(this.options.directory, 'music-comments'), cache, version).choose('awakening', 0, notice.text);
      return audio ? { text: notice.text, trackId: notice.trackId, audio, volume: s.musicCommentVolume } : undefined;
    } catch { return; } finally { cache.clear(); }
  }
  async action(request: MusicRequest) {
    if (!request || typeof request !== 'object') throw new Error('Acción musical inválida.');
    if (request.action === 'clear-history') { this.memory()?.clear(); this.play = undefined; this.refresh(); return; }
    if (request.action === 'select') {
      if (!this.state.sessions.some(s => s.sessionId === request.sessionId)) throw new Error('La sesión ya no está disponible.');
      this.selected = request.sessionId; this.refresh(); return;
    }
    const active = chooseMusicSession(this.state.sessions, request.sessionId ?? this.state.activeId);
    if (!active || (request.sessionId && active.sessionId !== request.sessionId) || (request.trackId && active.trackId !== request.trackId)) throw new Error('La canción o sesión cambió.');
    if (['like','dislike','remember'].includes(request.action)) {
      if (!this.options.settings().musicHistory) throw new Error('Activa el historial musical para guardar preferencias.');
      const memory = this.memory(); if (!memory) throw new Error('Conecta Karen Core para guardar memoria musical.');
      memory.preference(active, request.action === 'dislike' ? -1 : request.action === 'like' ? 1 : undefined, request.action === 'remember'); return;
    }
    if (!active.controls.includes(request.action as never)) throw new Error('Esta sesión no admite ese control.');
    if (request.action === 'seek' && (typeof request.value !== 'number' || !Number.isFinite(request.value) || request.value < 0 || active.duration === undefined || request.value > active.duration)) throw new Error('Posición inválida.');
    if (request.action === 'volume') {
      if (typeof request.value !== 'number' || !Number.isFinite(request.value) || Math.abs(request.value) > 1 || active.volume === undefined) throw new Error('Volumen no disponible.');
      request = { ...request, value: Math.min(1, Math.max(0, (request.relative ? active.volume : 0) + request.value)) };
    }
    if (request.action === 'shuffle' && typeof request.value !== 'boolean') throw new Error('Aleatorio inválido.');
    if (request.action === 'repeat' && !['none','track','list'].includes(String(request.value))) throw new Error('Repetición inválida.');
    const skipped = request.action === 'next' && this.play?.session.trackId === active.trackId ? { ...this.play } : undefined;
    const ok = active.evidence === 'browser' ? await this.browser?.command(active.sessionId, active.trackId, request) : await this.adapter.command({ ...request, sessionId: active.sessionId });
    if (!ok) throw new Error('La aplicación no confirmó el control multimedia.');
    if (skipped && this.options.settings().musicHistory && skipped.seconds >= 10 && active.duration && skipped.seconds < active.duration - 15) {
      this.memory()?.observe(skipped.session, skipped.id, skipped.started, skipped.seconds, true);
    }
  }
  history() { return this.memory()?.history() ?? []; }
  summary() { return this.memory()?.summary() ?? '# Música\n\nMemoria musical no disponible.'; }
  stop() {
    ++this.epoch; this.save(false); this.adapter.stop(); this.browser?.stop(); this.browser = undefined;
    clearInterval(this.timer); this.timer = undefined; this.native = []; this.web = []; this.play = undefined;
    this.state = { enabled: false, status: 'off', sessions: [] }; this.options.publish(this.state);
  }
}
