import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('../src/native', () => ({ bridge: { claimMicrophone: vi.fn(), releaseMicrophone: vi.fn(async () => {}) } }));
import { bridge } from '../src/native';
import { openMicrophone } from '../src/voice/microphone';

afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

describe('microphone hardware authorization boundary', () => {
  it('does not open hardware when Core denies ownership', async () => {
    vi.mocked(bridge.claimMicrophone!).mockRejectedValueOnce(new Error('Busy'));
    const open = vi.fn();
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: open } });
    await expect(openMicrophone({ audio: true })).rejects.toThrow('Busy');
    expect(open).not.toHaveBeenCalled();
  });

  it('releases ownership after an opening failure', async () => {
    vi.mocked(bridge.claimMicrophone!).mockResolvedValueOnce('ticket');
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(new Error('Unplugged')) } });
    await expect(openMicrophone({ audio: true })).rejects.toThrow('Unplugged');
    expect(bridge.releaseMicrophone).toHaveBeenCalledExactlyOnceWith('ticket');
  });

  it('waits for every track to stop and releases only once', async () => {
    vi.mocked(bridge.claimMicrophone!).mockResolvedValueOnce('ticket');
    const tracks = [{ stop: vi.fn(), addEventListener: vi.fn() }, { stop: vi.fn(), addEventListener: vi.fn() }];
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: async () => ({ getTracks: () => tracks }) } });
    await openMicrophone({ audio: true });
    tracks[0].stop();
    expect(bridge.releaseMicrophone).not.toHaveBeenCalled();
    tracks[1].stop(); tracks[1].stop();
    expect(bridge.releaseMicrophone).toHaveBeenCalledExactlyOnceWith('ticket');
  });
});
