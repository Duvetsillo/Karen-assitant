import { afterEach, describe, expect, it, vi } from 'vitest';
import { defaults } from '../shared/settings';
import type { MediaSession } from '../shared/music';
const mock = vi.hoisted(() => ({ publish: undefined as ((s: MediaSession[]) => void) | undefined, command: vi.fn(async () => true), stop: vi.fn() }));
vi.mock('../electron/music-adapter.js', () => ({ WindowsMediaAdapter: class {
  constructor(_path: string, publish: (s: MediaSession[]) => void) { mock.publish = publish; }
  start() {} stop = mock.stop; command = mock.command; control = mock.command; context = async () => ({ safeDesktop: false, callsClear: false });
} }));
import { MusicPresence } from '../electron/music-presence';
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });
describe('music presence transitions and history permission', () => {
  it('records a confirmed skip even if the track event arrives before the control acknowledgement', async () => {
    vi.useFakeTimers(); vi.setSystemTime(10 * 3600000);
    const settings = { ...defaults, musicEnabled: true, musicHistory: true };
    const observe = vi.fn();
    const service = new MusicPresence({ executable: 'fixture', directory: 'fixture', settings: () => settings, token: () => undefined,
      memory: () => ({ observe } as never), publish: () => {},
      context: () => ({ now: Date.now(), present: true, conversation: false, voiceBusy: false, intro: false }) });
    const session: MediaSession = { sessionId:'s',trackId:'old',source:'Spotify.exe',title:'QA',artist:'QA Artist',album:'QA Album',mediaType:'music',evidence:'native',status:'playing',controls:['next'],duration:180,updatedAt:Date.now() };
    service.configure(); mock.publish!([session]); await vi.advanceTimersByTimeAsync(12000);
    mock.command.mockImplementationOnce(async () => { mock.publish!([{ ...session, trackId:'new' }]); return true; });
    await service.action({ action:'next',sessionId:'s',trackId:'old' });
    expect(observe).toHaveBeenCalledWith(expect.objectContaining({trackId:'old'}), expect.any(String), expect.any(Number), 12, true);
    settings.musicHistory = false; observe.mockClear();
    await vi.advanceTimersByTimeAsync(20000); expect(observe).not.toHaveBeenCalled();
    await expect(service.action({action:'like'})).rejects.toThrow('Activa el historial');
    await expect(service.action({action:'pause'})).rejects.toThrow('no admite');
    await expect(service.action({action:'next',trackId:'old'})).rejects.toThrow('cambió');
    service.stop(); expect(mock.stop).toHaveBeenCalled(); expect(service.snapshot().sessions).toEqual([]);
  });
});
