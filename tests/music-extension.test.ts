import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { classifyMusic, validateMediaSession } from '../shared/music';
afterEach(() => vi.useRealTimers());
describe('restricted browser extension with synthetic Media Session', () => {
  it('reports musical category without capturing audio and rejects controls for a changed track', async () => {
    vi.useFakeTimers();
    const callbacks: Record<string, Function> = {}, published: any[] = [];
    let control!: Function;
    const media = { paused: false, currentTime: 12, duration: 180, volume: .5, pause: vi.fn(), play: vi.fn(async () => {}) };
    const sandbox = {
      location: new URL('https://www.youtube.com/watch?v=abcdefghijk'), URL,
      navigator: { mediaSession: { metadata: { title: 'Synthetic videoclip', artist: 'QA Artist', album: 'QA' } } },
      document: { documentElement: {}, querySelectorAll: () => [media], querySelector: (selector: string) => selector.includes('meta[itemprop="genre"]') ? { content: 'Music' } : selector === 'audio,video' ? media : undefined,
        addEventListener: (name: string, callback: Function) => { callbacks[name] = callback; } },
      MutationObserver: class { observe() {} disconnect() {} },
      window: { addEventListener: () => {} },
      chrome: { runtime: { sendMessage: vi.fn(async (value: unknown) => { published.push(value); }), onMessage: { addListener: (callback: Function) => { control = callback; } } } },
      setTimeout, clearTimeout, setInterval, clearInterval, Date, console,
    };
    vm.runInNewContext(readFileSync(new URL('../extensions/music-presence/content.js', import.meta.url), 'utf8'), sandbox);
    await vi.advanceTimersByTimeAsync(300);
    const session = published[0].session;
    expect(session.category).toBe('Music');
    expect(classifyMusic(validateMediaSession(session, 'browser')!)).toBe('youtube');
    const responses: any[] = [];
    control({ type: 'control', request: { action: 'pause', trackId: 'changed' } }, {}, (r: unknown) => responses.push(r));
    await Promise.resolve(); await Promise.resolve();
    expect(media.pause).not.toHaveBeenCalled(); expect(responses[0].ok).toBe(false);
    control({ type: 'control', request: { action: 'pause', trackId: session.trackId } }, {}, (r: unknown) => responses.push(r));
    await Promise.resolve(); await Promise.resolve(); expect(media.pause).toHaveBeenCalledOnce();
    const manifest = JSON.parse(readFileSync(new URL('../extensions/music-presence/manifest.json', import.meta.url), 'utf8'));
    expect(manifest.permissions).toEqual(['storage']); expect(manifest.content_scripts[0].matches).not.toContain('<all_urls>');
  });
});
