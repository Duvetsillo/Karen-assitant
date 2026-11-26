import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { existsSync } from 'node:fs';
import { validateMediaSession, type MediaSession, type MusicRequest } from '../shared/music.js';

export class WindowsMediaAdapter {
  private child?: ChildProcessWithoutNullStreams;
  private sequence = 0;
  private pending = new Map<string, { resolve: (value: { ok: boolean; safeDesktop?: boolean; callsClear?: boolean }) => void; timer: ReturnType<typeof setTimeout> }>();
  constructor(private executable: string, private publish: (sessions: MediaSession[], error?: string) => void) {}
  start() {
    if (this.child) return;
    if (process.platform !== 'win32' || !existsSync(this.executable)) { this.publish([], 'Compila el puente multimedia de Windows.'); return; }
    const child = this.child = spawn(this.executable, [], { windowsHide: true, stdio: ['pipe','pipe','pipe'] });
    let buffer = '';
    child.stdout.setEncoding('utf8').on('data', chunk => {
      buffer += chunk;
      if (buffer.length > 16_000_000) { this.stop(); this.publish([], 'El puente devolvió demasiados datos.'); return; }
      let end: number;
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, end); buffer = buffer.slice(end + 1);
        try {
          const value = JSON.parse(line);
          if (value.type === 'sessions' && Array.isArray(value.sessions)) {
            const sessions = value.sessions.slice(0, 32).map((raw: unknown) => validateMediaSession(raw, 'native')).filter((s: MediaSession | undefined): s is MediaSession => Boolean(s));
            this.publish(sessions);
          } else if (value.type === 'result') {
            const request = this.pending.get(value.id);
            if (request) { clearTimeout(request.timer); this.pending.delete(value.id); request.resolve({ ok: value.ok === true, safeDesktop: value.safeDesktop === true, callsClear: value.callsClear === true }); }
          } else if (value.type === 'error') this.publish([], 'GSMTC no está disponible.');
        } catch { this.publish([], 'Respuesta multimedia inválida.'); }
      }
    });
    child.stderr.resume();
    child.once('error', () => { if (this.child === child) { this.stop(); this.publish([], 'No se pudo iniciar el puente GSMTC.'); } });
    child.once('exit', () => { if (this.child === child) { this.stop(); this.publish([], 'El puente GSMTC se cerró.'); } });
  }
  command(request: MusicRequest): Promise<boolean> {
    return this.request(request).then(r => r.ok);
  }
  context() { return this.request({ action: 'context' }); }
  private request(request: MusicRequest | { action: 'context' }): Promise<{ ok: boolean; safeDesktop?: boolean; callsClear?: boolean }> {
    if (!this.child || this.pending.size > 8) return Promise.resolve({ ok: false });
    const id = String(++this.sequence);
    return new Promise(resolve => {
      const timer = setTimeout(() => { this.pending.delete(id); resolve({ ok: false }); }, 6000);
      this.pending.set(id, { resolve, timer });
      this.child!.stdin.write(JSON.stringify({ ...request, id }) + '\n');
    });
  }
  stop() {
    const child = this.child; this.child = undefined;
    for (const p of this.pending.values()) { clearTimeout(p.timer); p.resolve({ ok: false }); } this.pending.clear();
    child?.stdout.removeAllListeners('data'); child?.removeAllListeners('exit');
    // EOF lets the bridge revoke its WinRT subscriptions; a short deadline
    // applies only to this owned helper, never to a media application.
    if (child) { child.stdin.end(); const timer = setTimeout(() => child.kill(), 1500); child.once('exit', () => clearTimeout(timer)); }
  }
}
