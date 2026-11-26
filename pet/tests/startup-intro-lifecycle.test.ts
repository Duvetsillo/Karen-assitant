import { EventEmitter } from 'node:events';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defaults } from '../shared/settings';

const mocks = vi.hoisted(() => ({
  handlers: new Map<string, (...args: any[]) => any>(),
  safe: vi.fn(async () => true), stop: vi.fn(), windows: [] as any[],
}));
vi.mock('../electron/intro-guard.js', () => ({ IntroGuard: class {
  start = mocks.safe; stop = mocks.stop; expectOverlay() {}
} }));
vi.mock('electron', () => ({
  ipcMain: { handle: (key: string, fn: (...args: any[]) => any) => mocks.handlers.set(key, fn), removeHandler: (key: string) => mocks.handlers.delete(key) },
  screen: {
    getDisplayMatching: () => ({ id: 1, bounds: { x: -1920, y: 0, width: 1920, height: 1080 } }),
    getAllDisplays: () => [{ id: 1, bounds: { x: -1920, y: 0, width: 1920, height: 1080 } }],
  },
  BrowserWindow: class extends EventEmitter {
    webContents = Object.assign(new EventEmitter(), { id: 40, mainFrame: {} });
    dead = false;
    showInactive = vi.fn(); hide = vi.fn(); setIgnoreMouseEvents = vi.fn(); setMenuBarVisibility = vi.fn();
    constructor(public options: unknown) { super(); mocks.windows.push(this); }
    isDestroyed() { return this.dead; }
    destroy() { this.dead = true; this.emit('closed'); }
  },
}));
import { StartupIntroManager } from '../electron/startup-intros';

describe('intro window lifecycle, races and fallback', () => {
  beforeEach(() => { vi.clearAllMocks(); mocks.handlers.clear(); mocks.windows.length = 0; mocks.safe.mockResolvedValue(true); });
  const setup = (overrides = {}) => {
    const settings = { ...defaults, introVoice: false, ...overrides };
    const pet = {
      getBounds: () => ({ x: -500, y: 500, width: 380, height: 440 }),
      isVisible: () => true, isDestroyed: () => false,
      hide: vi.fn(), showInactive: vi.fn(), setOpacity: vi.fn(), setIgnoreMouseEvents: vi.fn(),
      webContents: { id: 10, mainFrame: {}, send: vi.fn(), setBackgroundThrottling: vi.fn() },
    };
    const manager = new StartupIntroManager({ pet: pet as never, settings: () => settings, directory: '/temporary-test-only',
      prefs: () => ({}), load: async () => {}, protect: () => {}, blocked: () => false, log: () => {} });
    return { manager, pet, settings };
  };
  const event = () => ({ sender: mocks.windows[0].webContents, senderFrame: mocks.windows[0].webContents.mainFrame });
  it('prepares separately, waits for rendering, then closes and restores without stealing focus', async () => {
    const { manager, pet } = setup();
    expect(await manager.play('glass', true)).toBe(true);
    expect(pet.hide).not.toHaveBeenCalled();
    const payload = mocks.handlers.get('intro-payload')!(event());
    expect(payload.target.x).toBe(1420); // Negative-coordinate home monitor converted to DIP-local space.
    expect(mocks.windows[0].options.focusable).toBe(false);
    expect(mocks.windows[0].setIgnoreMouseEvents).toHaveBeenCalledWith(true);
    expect(mocks.handlers.get('intro-ready')!(event())).toBe(true);
    expect(pet.hide).toHaveBeenCalledOnce();
    mocks.handlers.get('intro-finished')!(event());
    expect(manager.active).toBe(false); expect(pet.showInactive).toHaveBeenCalledOnce();
    expect(mocks.windows[0].dead).toBe(true); expect(mocks.stop).toHaveBeenCalledOnce();
    manager.dispose(); expect(mocks.handlers.size).toBe(0);
  });
  it('falls back if Windows is busy and never creates an invisible interception window', async () => {
    mocks.safe.mockResolvedValue(false);
    const { manager, pet } = setup();
    expect(await manager.play('glass', true)).toBe(false);
    expect(mocks.windows).toHaveLength(0); expect(pet.showInactive).toHaveBeenCalledOnce();
    manager.dispose();
  });
  it('pre-renders a click-through desktop pet before revealing it and clearing the overlay', async () => {
    const { manager, pet } = setup();
    await manager.play('awakening'); mocks.handlers.get('intro-ready')!(event());
    const prepared = mocks.handlers.get('intro-prepare-landing')!(event());
    expect(pet.setOpacity).toHaveBeenCalledWith(0); expect(pet.setIgnoreMouseEvents).toHaveBeenCalledWith(true);
    expect(manager.coveringPet).toBe(true);
    const token = pet.webContents.send.mock.calls.find(call => call[1].token)?.[1].token;
    expect(token).toBeTruthy();
    await mocks.handlers.get('intro-pet-rendered')!({ sender: pet.webContents, senderFrame: pet.webContents.mainFrame }, token);
    expect(await prepared).toBe(true);
    mocks.handlers.get('intro-reveal-pet')!(event());
    expect(pet.setOpacity).toHaveBeenLastCalledWith(1); expect(mocks.windows[0].hide).toHaveBeenCalledOnce();
    expect(manager.coveringPet).toBe(false);
    mocks.handlers.get('intro-finished')!(event());
    expect(pet.webContents.setBackgroundThrottling).toHaveBeenLastCalledWith(true);
    manager.dispose();
  });
  it('cancels an in-flight guard and ignores its stale completion', async () => {
    let settle!: (safe: boolean) => void;
    mocks.safe.mockImplementationOnce(() => new Promise(resolve => { settle = resolve; }));
    const { manager } = setup();
    const pending = manager.play('glass'); manager.cancel(); settle(true);
    expect(await pending).toBe(false); expect(mocks.windows).toHaveLength(0);
    manager.dispose();
  });
  it('prevents overlapping playback, handles a renderer crash, and rejects foreign IPC', async () => {
    const { manager, pet } = setup();
    await manager.play('glass'); expect(await manager.play('sleepy')).toBe(false);
    expect(() => mocks.handlers.get('intro-payload')!({ sender: { id: 99 } })).toThrow('no autorizado');
    mocks.windows[0].webContents.emit('render-process-gone');
    expect(manager.active).toBe(false); expect(pet.showInactive).toHaveBeenCalledOnce(); manager.dispose();
  });
  it('supports explicit preview while disabled, but skips automatic startup and gaming', async () => {
    const { manager, settings } = setup({ introEnabled: false });
    expect(await manager.play('glass', true)).toBe(false);
    expect(await manager.play('glass')).toBe(true); manager.cancel();
    settings.mode = 'gaming'; expect(await manager.play('glass')).toBe(false);
    await expect(manager.play('invalid' as never)).rejects.toThrow(); manager.dispose();
  });
});
