import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('../src/native', () => ({ bridge: {} }));
import { TranscriptionWakeDetector } from '../src/voice/wake';

vi.mock('../src/voice/pcm', () => ({ pcm16: async () => new Int16Array(16000).buffer }));

describe('recuperación de escucha local', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('reabre el micrófono tras un fallo transitorio y conserva el estado real', async () => {
    const stop = vi.fn();
    const stream = { getTracks: () => [{ stop }], getAudioTracks: () => [{ stop }] };
    const transient = new Error('Dispositivo ocupado');
    transient.name = 'NotReadableError';
    const getUserMedia = vi.fn().mockRejectedValueOnce(transient).mockResolvedValue(stream);
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    vi.stubGlobal('AudioContext', class {
      async resume() {}
      async close() {}
      createAnalyser() { return { fftSize: 1024, getFloatTimeDomainData: (samples: Float32Array) => samples.fill(0) }; }
      createMediaStreamSource() { return { connect: () => {} }; }
    });
    vi.stubGlobal('MediaStream', class { constructor(_tracks: unknown[]) {} });
    vi.stubGlobal('MediaRecorder', class {
      state = 'inactive';
      start() { this.state = 'recording'; }
      stop() { this.state = 'inactive'; }
    });
    const statuses: string[] = [];
    const fail = vi.fn();
    const detector = new TranscriptionWakeDetector(async () => '', '', 1, s => statuses.push(s), fail);
    try {
      await detector.start(() => {});
      await vi.waitFor(() => expect(statuses.at(-1)).toBe('listening'), { timeout: 2500 });
      expect(getUserMedia).toHaveBeenCalledTimes(2);
      expect(statuses).toContain('recovering');
      expect(fail).not.toHaveBeenCalled();
    } finally { detector.stop(); }
  }, 4000);

  it('no reintenta permiso denegado y muestra error', async () => {
    const denied = new Error('Permiso denegado');
    denied.name = 'NotAllowedError';
    const getUserMedia = vi.fn().mockRejectedValue(denied);
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    const statuses: string[] = [];
    const fail = vi.fn();
    const detector = new TranscriptionWakeDetector(async () => '', '', 1, s => statuses.push(s), fail);
    await detector.start(() => {});
    await vi.waitFor(() => expect(statuses.at(-1)).toBe('error'));
    expect(getUserMedia).toHaveBeenCalledTimes(1);
    expect(fail).toHaveBeenCalledWith(denied);
    detector.stop();
  });

  it('no anuncia escucha si se pausa durante la apertura del dispositivo', async () => {
    const stop = vi.fn();
    let completeResume!: () => void;
    const resumed = new Promise<void>(resolve => { completeResume = resolve; });
    let enteredResume!: () => void;
    const opening = new Promise<void>(resolve => { enteredResume = resolve; });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: async () => ({
      getTracks: () => [{ stop }], getAudioTracks: () => [{ stop }],
    }) } });
    vi.stubGlobal('AudioContext', class {
      resume() { enteredResume(); return resumed; }
      async close() {}
    });
    const statuses: string[] = [];
    const detector = new TranscriptionWakeDetector(async () => '', '', 1, s => statuses.push(s), vi.fn());
    await detector.start(() => {});
    await opening;
    detector.pause();
    completeResume();
    await vi.waitFor(() => expect(stop).toHaveBeenCalled());
    expect(statuses.at(-1)).toBe('paused');
    expect(statuses).not.toContain('listening');
    detector.stop();
  });

  it('recupera la escucha al desconectarse una pista activa', async () => {
    const tracks = [{ stop: vi.fn(), onended: null as null | (() => void) },
      { stop: vi.fn(), onended: null as null | (() => void) }];
    const stoppedFirst = tracks[0].stop;
    let next = 0;
    const getUserMedia = vi.fn(async () => {
      const track = tracks[next++];
      return { getTracks: () => [track], getAudioTracks: () => [track] };
    });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    vi.stubGlobal('AudioContext', class {
      async resume() {}
      async close() {}
      createAnalyser() { return { fftSize: 1024, getFloatTimeDomainData: (samples: Float32Array) => samples.fill(0) }; }
      createMediaStreamSource() { return { connect: () => {} }; }
    });
    vi.stubGlobal('MediaStream', class { constructor(_tracks: unknown[]) {} });
    vi.stubGlobal('MediaRecorder', class {
      state = 'inactive';
      start() { this.state = 'recording'; }
      stop() { this.state = 'inactive'; }
    });
    const statuses: string[] = [];
    const fail = vi.fn();
    const detector = new TranscriptionWakeDetector(async () => '', '', 1, s => statuses.push(s), fail);
    try {
      await detector.start(() => {});
      await vi.waitFor(() => expect(statuses.at(-1)).toBe('listening'));
      tracks[0].onended?.();
      expect(statuses.at(-1)).toBe('recovering');
      await vi.waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(2), { timeout: 2500 });
      await vi.waitFor(() => expect(statuses.at(-1)).toBe('listening'));
      expect(stoppedFirst).toHaveBeenCalled();
      expect(fail).not.toHaveBeenCalled();
    } finally { detector.stop(); }
  }, 4000);

  it('vuelve a escuchar tras dos fallos transitorios de transcripción', async () => {
    const tracks = [{ stop: vi.fn() }];
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: async () => ({
      getTracks: () => tracks, getAudioTracks: () => tracks,
    }) } });
    vi.stubGlobal('AudioContext', class {
      async resume() {}
      async close() {}
      createAnalyser() {
        const started = performance.now();
        return { fftSize: 1024, getFloatTimeDomainData: (samples: Float32Array) =>
          samples.fill(performance.now() - started < 100 ? 0.2 : 0) };
      }
      createMediaStreamSource() { return { connect: () => {} }; }
    });
    vi.stubGlobal('MediaStream', class { constructor(_tracks: unknown[]) {} });
    vi.stubGlobal('MediaRecorder', class {
      state = 'inactive';
      mimeType = 'audio/webm';
      ondataavailable?: (event: { data: Blob }) => void;
      onstop?: () => void;
      start() { this.state = 'recording'; }
      stop() {
        this.state = 'inactive';
        this.ondataavailable?.({ data: new Blob(['audio']) });
        this.onstop?.();
      }
    });
    const statuses: string[] = [];
    const fail = vi.fn();
    const transcribe = vi.fn()
      .mockRejectedValueOnce(new Error('fallo temporal'))
      .mockRejectedValueOnce(new Error('fallo temporal'))
      .mockResolvedValue('Otra frase');
    const detector = new TranscriptionWakeDetector(transcribe, '', 1,
      status => statuses.push(status), fail);
    try {
      await detector.start(() => {});
      await vi.waitFor(() => expect(transcribe).toHaveBeenCalledTimes(3), { timeout: 12000, interval: 100 });
      await vi.waitFor(() => expect(statuses.at(-1)).toBe('listening'), { timeout: 2000 });
      expect(statuses.filter(status => status === 'recovering')).toHaveLength(2);
      expect(fail).not.toHaveBeenCalled();
    } finally { detector.stop(); }
  }, 15000);
});
