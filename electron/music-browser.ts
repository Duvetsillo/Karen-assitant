import { createServer, type Server, type ServerResponse } from 'node:http';
import { randomUUID, timingSafeEqual } from 'node:crypto';
import { validateMediaSession, type MediaSession, type MusicRequest } from '../shared/music.js';

/** Loopback-only metadata/control channel. Audio and arbitrary URLs are not accepted. */
export class MusicBrowserHub {
  private server?: Server;
  private sessions = new Map<string, { session: MediaSession; client: string; seen: number }>();
  private listeners = new Map<string, { response: ServerResponse; timer: ReturnType<typeof setTimeout> }>();
  private requests = new Map<string, { client: string; resolve: (ok: boolean) => void; timer: ReturnType<typeof setTimeout> }>();
  constructor(private token: string, private publish: (sessions: MediaSession[], error?: string) => void, private port = 18796) {}
  get address() { const address = this.server?.address(); return address && typeof address === 'object' ? `http://127.0.0.1:${address.port}` : undefined; }
  start() {
    if (this.server) return Promise.resolve();
    this.server = createServer(async (req, res) => {
      const origin = req.headers.origin;
      const candidate = Buffer.from(req.headers.authorization?.replace(/^Bearer /, '') ?? '');
      const secret = Buffer.from(this.token);
      if (`http://${req.headers.host}` !== this.address || (origin && !/^chrome-extension:\/\/[a-p]{32}$/.test(origin))) { res.writeHead(403).end(); return; }
      if (origin) res.setHeader('Access-Control-Allow-Origin', origin);
      res.setHeader('Cache-Control', 'no-store');
      if (req.method === 'OPTIONS') { res.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type'); res.setHeader('Access-Control-Allow-Methods', 'POST,GET'); res.writeHead(204).end(); return; }
      if (!req.headers.authorization?.startsWith('Bearer ') || candidate.length !== secret.length || !timingSafeEqual(candidate, secret)) { res.writeHead(401).end(); return; }
      try {
        const url = new URL(req.url ?? '/', this.address);
        const client = url.searchParams.get('client') ?? '';
        if (!/^[\w-]{16,80}$/.test(client)) throw new Error();
        if (req.method === 'GET' && url.pathname === '/commands') {
          const previous = this.listeners.get(client); if (previous) { clearTimeout(previous.timer); previous.response.end('[]'); }
          const timer = setTimeout(() => { this.listeners.delete(client); res.end('[]'); }, 25000);
          this.listeners.set(client, { response: res, timer });
          res.on('close', () => { if (this.listeners.get(client)?.response === res) { clearTimeout(timer); this.listeners.delete(client); } });
          return;
        }
        if (req.method !== 'POST' || url.pathname !== '/events' || !String(req.headers['content-type']).startsWith('application/json')) throw new Error();
        const body: Buffer[] = []; let size = 0;
        for await (const chunk of req) { size += chunk.length; if (size > 64000) throw new Error(); body.push(chunk); }
        const value = JSON.parse(Buffer.concat(body).toString('utf8'));
        if (value.type === 'result') {
          const pending = this.requests.get(value.id);
          if (pending && pending.client === client) { clearTimeout(pending.timer); pending.resolve(value.ok === true); this.requests.delete(value.id); }
        } else {
          if (!Number.isSafeInteger(value.tabId) || value.tabId < 0) throw new Error();
          const key = `browser:${client}:${value.tabId}`;
          if (value.type === 'remove') this.sessions.delete(key);
          else {
            const session = validateMediaSession({ ...value.session, sessionId: key, source: 'browser' }, 'browser');
            if (!session || !['open.spotify.com','music.apple.com','music.youtube.com','www.youtube.com','youtube.com'].includes(session.domain ?? '')) throw new Error();
            if (this.sessions.size >= 32 && !this.sessions.has(key)) throw new Error();
            session.cover = undefined; // No remote fetching, browsing URLs or embedded files.
            this.sessions.set(key, { session, client, seen: Date.now() });
          }
          this.publish(this.snapshot());
        }
        res.end('{}');
      } catch { if (!res.headersSent) res.writeHead(400); res.end(); }
    });
    this.server.maxConnections = 12; this.server.requestTimeout = 10000; this.server.headersTimeout = 5000;
    return new Promise<void>(resolve => {
      this.server!.on('error', () => { this.stop(); this.publish([], 'El puerto local del complemento no está disponible.'); resolve(); });
      this.server!.listen(this.port, '127.0.0.1', () => resolve());
    });
  }
  snapshot() {
    const now = Date.now();
    for (const [key, value] of this.sessions) if (now - value.seen > 45000) this.sessions.delete(key);
    return [...this.sessions.values()].map(v => v.session);
  }
  command(sessionId: string, trackId: string, request: MusicRequest) {
    const target = this.sessions.get(sessionId), listener = target && this.listeners.get(target.client);
    if (!target || !listener || this.requests.size >= 8) return Promise.resolve(false);
    const id = randomUUID(); this.listeners.delete(target.client); clearTimeout(listener.timer);
    return new Promise<boolean>(resolve => {
      const timer = setTimeout(() => { this.requests.delete(id); resolve(false); }, 5000);
      this.requests.set(id, { client: target.client, timer, resolve });
      listener.response.end(JSON.stringify([{ ...request, id, sessionId, trackId }]));
    });
  }
  stop() {
    for (const p of this.listeners.values()) { clearTimeout(p.timer); p.response.end('[]'); } this.listeners.clear();
    for (const p of this.requests.values()) { clearTimeout(p.timer); p.resolve(false); } this.requests.clear();
    this.server?.close(); this.server?.closeAllConnections(); this.server = undefined; this.sessions.clear();
  }
}
