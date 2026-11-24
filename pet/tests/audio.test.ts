import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("../src/native", () => ({ bridge: { captureStatus: vi.fn(), energy: vi.fn(), send: vi.fn() } }));
vi.mock('../src/voice/pcm', () => ({ pcm16: async () => new ArrayBuffer(120) }));
import { bridge } from "../src/native";
import { AudioDirector } from "../src/voice/audio";
import { signals, useStore } from "../src/state/store";
import { defaults } from "../shared/settings";

class TestAudio {
  static instances: TestAudio[] = [];
  onended?: () => void;
  onerror?: () => void;
  volume = 1;
  play = vi.fn(async () => {});
  pause = vi.fn();
  constructor() { TestAudio.instances.push(this); }
}
class TestContext {
  destination = {};
  resume = vi.fn(async () => {});
  close = vi.fn(async () => {});
  createAnalyser() { return { fftSize: 512, connect: vi.fn(), getFloatTimeDomainData: vi.fn() }; }
  createMediaElementSource() { return { connect: vi.fn() }; }
}
beforeEach(() => {
  TestAudio.instances = [];
  vi.stubGlobal("AudioContext", TestContext);
  vi.stubGlobal("Audio", TestAudio);
  vi.stubGlobal("requestAnimationFrame", () => 1);
  vi.stubGlobal("cancelAnimationFrame", () => {});
  useStore.setState({ settings: { ...defaults, voiceEnabled: true }, capture: { kind: "microphone", phase: "idle" }, error: "" });
});
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

describe("ciclo real de reproducción", () => {
  it('No molestar suprime TTS automático sin alterar la preferencia de voz', async () => {
    useStore.setState({settings: {...defaults, mode:'do_not_disturb', voiceEnabled:true}});
    const synthesize = vi.fn(async () => new ArrayBuffer(12));
    const director = new AudioDirector({synthesize});
    await director.speak('Hola, soy Karen.');
    expect(synthesize).not.toHaveBeenCalled();
    expect(TestAudio.instances).toHaveLength(0);
    expect(useStore.getState().settings.voiceEnabled).toBe(true);
  });
  it("sintetiza y reproduce una respuesta normal como una sola pieza", async () => {
    const synthesize = vi.fn(async () => new ArrayBuffer(12));
    const director = new AudioDirector({ synthesize });
    const first = "Esta primera frase ya puede empezar a sonar.";
    const second = "La segunda frase también conserva su identidad original.";
    const completed = director.speak(`${first} ${second}`);
    expect(useStore.getState().capture.phase).toBe("preparing");
    await vi.waitFor(() => expect(useStore.getState().capture.phase).toBe("speaking"));
    expect(synthesize).toHaveBeenCalledExactlyOnceWith(`${first} ${second}`, expect.any(AbortSignal));
    expect(TestAudio.instances).toHaveLength(1);
    useStore.getState().event({ type: "pet", state: "HAPPY", reason: "Respuesta completada" });
    expect(useStore.getState().state).toBe("SPEAKING");
    TestAudio.instances[0].onended?.();
    await completed;
    expect(useStore.getState().capture.phase).toBe("idle");
    expect(useStore.getState().state).toBe("HAPPY");
    expect(signals.energy).toBe(0);
    director.dispose();
  });
  it("cancelar durante la generación impide reproducir audio tardío", async () => {
    let finish!: (audio: ArrayBuffer) => void;
    const synthesize = vi.fn((_text: string, _signal: AbortSignal) => new Promise<ArrayBuffer>(resolve => { finish = resolve; }));
    const director = new AudioDirector({ synthesize });
    const pending = director.speak("Hola, soy Karen.");
    await vi.waitFor(() => expect(synthesize).toHaveBeenCalledTimes(1));
    const signal = synthesize.mock.calls[0]?.[1] as AbortSignal | undefined;
    director.cancel();
    finish(new ArrayBuffer(12));
    await pending;
    expect(signal?.aborted).toBe(true);
    expect(TestAudio.instances).toHaveLength(0);
    expect(useStore.getState().capture.phase).toBe("idle");
    expect(bridge.captureStatus).toHaveBeenCalledWith({ kind: "voice", phase: "idle", startedAt: undefined });
  });
  it("cancelar durante la reproducción resuelve la cola y cierra el audio", async () => {
    const director = new AudioDirector({ synthesize: async () => new ArrayBuffer(12) });
    const pending = director.speak("Hola, soy Karen.");
    await vi.waitFor(() => expect(useStore.getState().capture.phase).toBe("speaking"));
    director.cancel();
    await pending;
    expect(TestAudio.instances[0].pause).toHaveBeenCalled();
    expect(useStore.getState().capture.phase).toBe("idle");
  });
  it("conserva la preferencia Edge guardada pero reproduce voz local WAV en Core 2", async () => {
    useStore.setState({ settings: { ...defaults, voiceEnabled: true, ttsEngine: 'edge' } });
    let mediaType = '';
    const createObjectURL = URL.createObjectURL;
    URL.createObjectURL = (blob) => { mediaType = blob instanceof Blob ? blob.type : ''; return createObjectURL(blob); };
    try {
      const director = new AudioDirector({ synthesize: async () => new ArrayBuffer(12) });
      const pending = director.speak('Hola. Soy Karen.');
      await vi.waitFor(() => expect(useStore.getState().capture.phase).toBe('speaking'));
      expect(mediaType).toBe('audio/wav');
      expect(useStore.getState().settings.ttsEngine).toBe('edge');
      TestAudio.instances[0].onended?.();
      await pending;
      director.dispose();
    } finally { URL.createObjectURL = createObjectURL; }
  });
});

describe('dictado manual', () => {
  it('la transcripción cancelada no reactiva escucha durante una respuesta nueva', async () => {
    let finishTranscription!: (text: string) => void;
    let finishVoice!: (audio: ArrayBuffer) => void;
    const transcribe = vi.fn(() => new Promise<string>(resolve => { finishTranscription = resolve; }));
    const synthesize = vi.fn(() => new Promise<ArrayBuffer>(resolve => { finishVoice = resolve; }));
    const director = new AudioDirector({ synthesize }, { transcribe });
    const detector = { start: vi.fn(async () => {}), pause: vi.fn(), resume: vi.fn(), stop: vi.fn() };
    director['detector'] = detector;
    const old = director['finishCapture'](0, new Blob([new Uint8Array(120)]));
    await vi.waitFor(() => expect(transcribe).toHaveBeenCalledTimes(1));
    director.cancel(false);
    const current = director.speak('Karen prepara una respuesta nueva.');
    await vi.waitFor(() => expect(synthesize).toHaveBeenCalledTimes(1));
    finishTranscription('orden antigua');
    await old;
    expect(director['processing']).toBe(true);
    expect(useStore.getState().capture.phase).toBe('preparing');
    expect(detector.resume).not.toHaveBeenCalled();
    expect(bridge.send).not.toHaveBeenCalled();
    director.cancel(false);
    finishVoice(new ArrayBuffer(12));
    await current;
    director.dispose();
  });

  it('descarta el audio parcial si el micrófono se desconecta', async () => {
    const track = { stop: vi.fn(), onended: null as null | (() => void) };
    const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: async () => stream } });
    vi.stubGlobal('MediaStream', class { constructor(_tracks: unknown[]) {} });
    vi.stubGlobal('AudioContext', class {
      async close() {}
      createAnalyser() { return { fftSize: 512, getFloatTimeDomainData: vi.fn() }; }
      createMediaStreamSource() { return { connect: vi.fn() }; }
    });
    vi.stubGlobal('MediaRecorder', class {
      state = 'inactive';
      mimeType = 'audio/webm';
      onstop?: () => void;
      start() { this.state = 'recording'; }
      stop() { this.state = 'inactive'; this.onstop?.(); }
    });
    useStore.setState({ settings: { ...defaults, sttEnabled: true } });
    const director = new AudioDirector();
    try {
      await director.toggleListening();
      expect(useStore.getState().capture.phase).toBe('recording');
      track.onended?.();
      expect(useStore.getState().capture.phase).toBe('idle');
      expect(useStore.getState().state).toBe('ERROR');
      expect(useStore.getState().error).toContain('desconectó');
      expect(bridge.send).not.toHaveBeenCalled();
    } finally { director.dispose(); }
  });
});
