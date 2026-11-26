import { afterEach, describe, expect, it } from 'vitest';
import { MusicBrowserHub } from '../electron/music-browser';
const token = 'synthetic-local-pairing-token-for-tests-only-xx';
const client = 'synthetic-browser-client';
let hub: MusicBrowserHub | undefined;
afterEach(() => hub?.stop());
function request(body: object, authorization = `Bearer ${token}`, id = client, origin?: string) {
  return fetch(`${hub!.address}/events?client=${id}`, { method: 'POST', headers: { Authorization: authorization, 'Content-Type': 'application/json', ...(origin ? { Origin: origin } : {}) }, body: JSON.stringify(body) });
}
describe('authenticated browser metadata transport', () => {
  it('rejects missing authentication and ordinary websites, validates domains and isolates control replies', async () => {
    hub = new MusicBrowserHub(token, () => {}, 0); await hub.start();
    expect((await request({}, 'Bearer invalid')).status).toBe(401);
    expect((await request({}, `Bearer ${token}`, client, 'https://evil.invalid')).status).toBe(403);
    const session = { sessionId: 'spoof', trackId: 'qa-track', source: 'spoof', title: 'QA', domain: 'www.youtube.com', videoId: 'abcdefghijk', category: 'Music', status: 'playing', controls: ['play','pause'] };
    expect((await request({ type: 'session', tabId: 3, session: { ...session, domain: 'evil.invalid' } })).status).toBe(400);
    expect((await request({ type: 'session', tabId: 3, session })).status).toBe(200);
    const actual = hub.snapshot()[0]; expect(actual.sessionId).toBe(`browser:${client}:3`); expect(actual.source).toBe('browser');
    const waiting = fetch(`${hub.address}/commands?client=${client}`, { headers: { Authorization: `Bearer ${token}` } });
    await new Promise(resolve => setTimeout(resolve, 30));
    let completed = false;
    const controlled = hub.command(actual.sessionId, actual.trackId, { action: 'pause' }).then(ok => { completed = true; return ok; });
    const commands = await (await waiting).json();
    expect(commands[0].trackId).toBe('qa-track');
    await request({ type: 'result', id: commands[0].id, ok: true }, `Bearer ${token}`, 'different-browser-client');
    expect(completed).toBe(false);
    await request({ type: 'result', id: commands[0].id, ok: true }); expect(await controlled).toBe(true);
    await request({ type: 'remove', tabId: 3 }); expect(hub.snapshot()).toEqual([]);
  });
});
