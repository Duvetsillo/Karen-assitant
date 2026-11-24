import { bridge } from "../native";
import { openMicrophone } from './microphone';
import { useStore, signals, report } from "../state/store";
import { speechPhrases } from "./replies";
import type { CaptureStatus } from "../../shared/types";
import { TranscriptionWakeDetector } from './wake';
import { pcm16 } from './pcm';
import { speechAudio } from './pipeline';
import { expressionForReply } from '../../shared/expression';
import { effectiveSettings } from '../../shared/settings';

export interface TtsEngine {
  synthesize(text: string, signal: AbortSignal): Promise<ArrayBuffer>;
}
export interface SttEngine {
  transcribe(pcm16: ArrayBuffer, signal: AbortSignal): Promise<string>;
}
export interface WakeWordDetector {
  start(onWake: (command: string) => void): Promise<void>;
  pause(): void;
  resume(): void;
  stop(): void;
}
// A detector owns microphone permission; wake is always an explicit setting.
export class AudioDirector {
  private context?: AudioContext;
  private analyser?: AnalyserNode;
  private frame = 0;
  private audio?: HTMLAudioElement;
  private speechController?: AbortController;
  private finishPlayback?: () => void;
  private url?: string;
  private stream?: MediaStream;
  private recorder?: MediaRecorder;
  private generation = 0;
  private limit?: ReturnType<typeof setTimeout>;
  private detector?: WakeWordDetector;
  private recording = false;
  private processing = false;
  private stopRecording = false;
  private speechSeen = false;
  private silenceAt = 0;
  private active = false;
  private kind: "microphone" | "system" | "voice" = "microphone";
  private status(phase: CaptureStatus["phase"]) {
    if (phase === "idle" && !this.active) return;
    this.active = phase !== "idle";
    const status = { kind: this.kind, phase, startedAt: phase === "idle" ? undefined : Date.now() };
    useStore.getState().event({ type: "capture", status });
    bridge.captureStatus(status);
  }
  constructor(
    private tts: TtsEngine = {
      synthesize: async (text, signal) => {
        const cancel = () => { void bridge.cancelSynthesis?.().catch(() => {}); };
        signal.throwIfAborted();
        signal.addEventListener('abort', cancel, {once:true});
        try { return await bridge.synthesize(text); }
        finally { signal.removeEventListener('abort', cancel); }
      },
    },
    private stt: SttEngine = {
      transcribe: async (pcm) => bridge.transcribe(pcm),
    },
  ) {}
  async attachWakeWordDetector(detector: WakeWordDetector) {
    this.detector?.stop();
    this.detector = detector;
    await detector.start((command) => {
      if (!this.audio && !this.recording && !this.processing) {
        this.detector?.pause();
        useStore.getState().transition("HAPPY", "Palabra clave detectada");
        void bridge.prepareVoice?.().catch(() => {});
        if (command) void bridge.send(command).catch(report).finally(() => this.resumeWake());
        else void this.toggleListening(10000);
      } else {
        this.resumeWake();
      }
    });
  }
  async configureWake(enabled: boolean, inputDevice: string, sensitivity: number) {
    this.detector?.stop(); this.detector = undefined;
    if (!enabled) { useStore.setState({wakeStatus:'off',wakeError:''}); bridge.wakeStatus?.('off'); return; }
    const detector = new TranscriptionWakeDetector(
      pcm => this.stt.transcribe(pcm, new AbortController().signal), inputDevice, sensitivity,
      status => { useStore.getState().event({type:'wake-status',status}); bridge.wakeStatus?.(status); },
      error => {
        report(error);
        const message = useStore.getState().error;
        useStore.setState({wakeError:message});
        bridge.wakeStatus?.('error', message);
      },
    );
    await this.attachWakeWordDetector(detector);
    if (this.processing || this.audio || this.recording) detector.pause();
  }
  private resumeWake() {
    const capture = useStore.getState().capture;
    if (!this.processing && !this.audio && !this.recording && !(capture.kind === 'system' && capture.phase !== 'idle')) this.detector?.resume();
  }
  suspendWake(suspended: boolean) { if (suspended) this.detector?.pause(); else this.resumeWake(); }
  private meter() {
    if (!this.analyser) return;
    const data = new Float32Array(this.analyser.fftSize);
    let last = 0;
    const tick = (now: number) => {
      if (!this.analyser) return;
      if (now - last > 32) {
        last = now;
        this.analyser.getFloatTimeDomainData(data);
        let sum = 0;
        for (const x of data) sum += x * x;
        const raw = Math.sqrt(sum / data.length);
        signals.energy = Math.min(
          1,
          raw * 7 * useStore.getState().settings.sensitivity,
        );
        bridge.energy(signals.energy);
        if (this.recording) {
          if (raw > (this.kind === "system" ? 0.004 : 0.008)) {
            this.speechSeen = true;
            this.silenceAt = now;
          } else if (this.kind === "microphone" && this.speechSeen && now - this.silenceAt > 1200)
            this.recorder?.stop();
        }
      }
      this.frame = requestAnimationFrame(tick);
    };
    this.frame = requestAnimationFrame(tick);
  }
  private cleanup(finish = true) {
    cancelAnimationFrame(this.frame);
    clearTimeout(this.limit);
    this.analyser = undefined;
    signals.energy = 0;
    bridge.energy(0);
    this.audio?.pause();
    this.finishPlayback?.();
    this.finishPlayback = undefined;
    this.audio = undefined;
    if (this.url) URL.revokeObjectURL(this.url);
    this.url = undefined;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = undefined;
    if (this.context) void this.context.close().catch(() => {});
    this.context = undefined;
    if (finish) this.status("idle");
  }
  cancel(resumeListening = true) {
    // Invalidate an in-flight wake transcription before its cancellation rejects.
    // resumeWake rearms it; a stale rejection cannot turn off the new listener.
    this.detector?.pause();
    this.generation++;
    this.speechController?.abort();
    this.speechController = undefined;
    this.stopRecording = true;
    this.processing = false;
    if (this.recorder?.state === "recording") this.recorder.stop();
    this.recorder = undefined;
    this.recording = false;
    this.cleanup();
    if (resumeListening) this.resumeWake();
    useStore.getState().transition("IDLE");
  }
  async speak(text: string) {
    this.cancel(false);
    const generation = this.generation;
    const settings = effectiveSettings(useStore.getState().settings);
    if (!settings.voiceEnabled) { this.resumeWake(); return; }
    // Local cloning has a substantial per-clip cost. Use complete sentences and
    // the existing one-clip prefetch, instead of buffering a whole long reply.
    const phrases = settings.ttsEngine === 'local' ? speechPhrases(text, 240, 70, 40) : speechPhrases(text);
    if (!phrases.length) { this.resumeWake(); return; }
    useStore.setState({ expression: expressionForReply(text) });
    this.kind = "voice";
    this.processing = true;
    const controller = new AbortController();
    this.speechController = controller;
    this.detector?.pause();
    try {
      useStore.getState().transition("THINKING", settings.ttsEngine==='local'?"Preparando voz original":"Preparando voz");
      this.status("preparing");
      for await (const bytes of speechAudio(phrases, (phrase, signal) => this.tts.synthesize(phrase, signal), controller.signal)) {
        if (generation !== this.generation) return;
        this.context = new AudioContext();
        const outputContext = this.context as AudioContext & { setSinkId?: (id: string) => Promise<void> };
        if (settings.outputDevice) {
          if (!outputContext.setSinkId) throw new Error("Este motor no permite elegir la salida de audio.");
          await outputContext.setSinkId(settings.outputDevice);
        }
        if (generation !== this.generation) return;
        this.analyser = this.context.createAnalyser();
        this.analyser.fftSize = 512;
        this.url = URL.createObjectURL(new Blob([bytes], { type: settings.ttsEngine === 'edge' ? "audio/mpeg" : "audio/wav" }));
        this.audio = new Audio(this.url);
        this.audio.volume = settings.volume;
        const output = this.audio as HTMLAudioElement & {
          setSinkId?: (id: string) => Promise<void>;
        };
        if (settings.outputDevice && output.setSinkId)
          await output.setSinkId(settings.outputDevice);
        if (generation !== this.generation) return;
        const source = this.context.createMediaElementSource(this.audio);
        source.connect(this.analyser);
        this.analyser.connect(this.context.destination);
        const playback = new Promise<void>((resolve, reject) => {
          this.finishPlayback = resolve;
          this.audio!.onended = () => { this.finishPlayback = undefined; resolve(); };
          this.audio!.onerror = () => { this.finishPlayback = undefined; reject(new Error("No se pudo reproducir la voz. Revisa el dispositivo de salida.")); };
        });
        // The error handler can reject while play() itself is still pending.
        void playback.catch(() => {});
        await this.context.resume();
        if (generation !== this.generation) return;
        await this.audio.play();
        if (generation !== this.generation) return;
        useStore.getState().transition("SPEAKING");
        this.status("speaking");
        this.meter();
        await playback;
        if (generation !== this.generation) return;
        // Keep ownership between phrases so another reply cannot overtake us.
        this.cleanup(false);
        useStore.getState().transition("THINKING", "Preparando voz original");
        this.status("preparing");
      }
      if (generation === this.generation) {
        this.processing = false;
        this.cleanup();
        this.resumeWake();
        useStore.getState().transition(useStore.getState().expression, "Voz completada");
      }
    } catch (e) {
      if (generation === this.generation) {
        this.processing = false;
        this.cleanup();
        this.resumeWake();
        report(e);
        useStore.getState().transition("ERROR", "Motor de voz no disponible");
      }
    } finally {
      if (this.speechController === controller) this.speechController = undefined;
    }
  }
  async toggleListening(limitMs = 60000) {
    if (this.recording) {
      if (this.recorder?.state === "recording") this.recorder.stop();
      return;
    }
    this.cancel(false);
    this.kind = "microphone";
    const generation = this.generation;
    this.stopRecording = false;
    if (!useStore.getState().settings.sttEnabled) {
      report(new Error("Activa el reconocimiento local en Voz."));
      this.resumeWake();
      return;
    }
    this.detector?.pause();
    try {
      await bridge.cancelTranscription?.();
      void bridge.prepareVoice?.().catch(() => {});
      const settings = useStore.getState().settings;
      const stream = await openMicrophone({
        audio: {
          deviceId: settings.inputDevice
            ? { exact: settings.inputDevice }
            : undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      if (!stream.getAudioTracks().length) { stream.getTracks().forEach(track => track.stop()); throw new Error("Windows no entregó audio del sistema."); }
      if (generation !== this.generation) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      this.stream = stream;
      this.context = new AudioContext();
      this.analyser = this.context.createAnalyser();
      this.analyser.fftSize = 512;
      this.context.createMediaStreamSource(stream).connect(this.analyser);
      const chunks: Blob[] = [];
      this.speechSeen = false;
      this.silenceAt = performance.now();
      this.recorder = new MediaRecorder(new MediaStream(stream.getAudioTracks()));
      const recorder = this.recorder;
      this.recording = true;
      this.recorder.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      this.recorder.onstop = () => {
        void this.finishCapture(generation, new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
      };
      this.recorder.start();
      useStore.getState().transition("LISTENING");
      this.status("recording");
      stream.getAudioTracks().forEach(track => { track.onended = () => {
        if (generation !== this.generation || !this.recording) return;
        this.cancel(false);
        report(new Error("El micrófono se desconectó durante el dictado."));
        useStore.getState().transition("ERROR");
        this.resumeWake();
      }; });
      this.meter();
      this.limit = setTimeout(() => {
        if (this.recorder?.state === "recording") this.recorder.stop();
      }, limitMs);
    } catch (e) {
      if (generation !== this.generation) return;
      this.cleanup();
      this.resumeWake();
      report(e);
      useStore.getState().transition("ERROR");
    }
  }
  private async finishCapture(generation: number, blob: Blob) {
    if (this.stopRecording || generation !== this.generation) return;
    this.recording = false;
    this.cleanup();
    if (blob.size < 100) { useStore.getState().transition("CONFUSED", "No se detectó audio con voz"); this.resumeWake(); return; }
    this.processing = true;
    this.status("transcribing");
    useStore.getState().transition("THINKING", "Transcribiendo en este equipo");
    try {
      const text = await this.stt.transcribe(
        await pcm16(blob),
        new AbortController().signal,
      );
      if (generation !== this.generation) return;
      if (!text) {
        useStore.getState().transition("CONFUSED", "No se detectó voz");
        return;
      }
      await bridge.send(text);
    } catch (e) {
      if (generation === this.generation) {
        report(e);
        useStore.getState().transition("ERROR");
      }
    } finally {
      if (generation === this.generation) {
        this.processing = false;
        this.status("idle");
        this.resumeWake();
      }
    }
  }
  dispose() {
    this.detector?.stop();
    this.detector = undefined;
    this.cancel();
  }
}
