import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('../src/native', () => ({ bridge: { captureStatus: vi.fn(), energy: vi.fn(), cancelSynthesis: vi.fn(async () => {}) } }));
import { AudioDirector } from '../src/voice/audio';
import { useStore } from '../src/state/store';
import { defaults } from '../shared/settings';
afterEach(() => vi.unstubAllGlobals());
describe('pregenerated music voice uses the existing playback pipeline', () => {
  it('never calls TTS for a local clip and preserves the normal voice volume', async () => {
    const closes = vi.fn(async () => {}), clips: any[] = [];
    class Context {
      destination = {}; resume = async () => {}; close = closes;
      createAnalyser() { return { fftSize: 512, connect: () => {}, getFloatTimeDomainData: (data: Float32Array) => data.fill(0) }; }
      createMediaElementSource() { return { connect: () => {} }; }
    }
    class Audio {
      volume = 1; onended?: () => void; onerror?: () => void;
      constructor() { clips.push(this); }
      play = async () => { queueMicrotask(() => this.onended?.()); }; pause() {}
    }
    vi.stubGlobal('AudioContext', Context); vi.stubGlobal('Audio', Audio);
    vi.stubGlobal('requestAnimationFrame', () => 1); vi.stubGlobal('cancelAnimationFrame', () => {});
    useStore.setState({ settings: { ...defaults, voiceEnabled: true, volume: .8 }, capture: { kind: 'voice', phase: 'idle' } });
    const synthesize = vi.fn(async () => { throw new Error('No debe sintetizar'); });
    const director = new AudioDirector({ synthesize }, { transcribe: vi.fn(async () => '') });
    await director.speak('Plantilla musical', { bytes: new ArrayBuffer(44), volume: .3 });
    expect(synthesize).not.toHaveBeenCalled(); expect(clips[0].volume).toBe(.3);
    expect(useStore.getState().settings.volume).toBe(.8); expect(closes).toHaveBeenCalled();
    director.dispose();
  });
});
