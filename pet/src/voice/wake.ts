import { wakeCommand } from '../../shared/wake-word';
import type { WakeStatus } from '../../shared/types';
import { pcm16 } from './pcm';
import { openMicrophone } from './microphone';
import { inputError } from './input-error';

/** Offline transcription gates addressed commands. Quiet audio never reaches STT. */
export class TranscriptionWakeDetector {
  private wanted = false;
  private stopped = false;
  private generation = 0;
  private stream?: MediaStream;
  private context?: AudioContext;
  private recorder?: MediaRecorder;
  private interval?: ReturnType<typeof setInterval>;
  private opening = false;
  private processing = false;
  private failures = 0;
  private inputFailures = 0;
  private recoveryTimer?: ReturnType<typeof setTimeout>;
  private onWake?: (command: string) => void;
  constructor(
    private transcribe: (pcm: ArrayBuffer) => Promise<string>,
    private device: string,
    private sensitivity: number,
    private status: (status: WakeStatus) => void,
    private fail: (error: unknown) => void,
  ) {}
  async start(onWake: (command: string) => void) { this.onWake = onWake; this.resume(); }
  private closeInput() {
    clearInterval(this.interval);
    this.interval = undefined;
    const recorder = this.recorder;
    this.recorder = undefined;
    if (recorder?.state === 'recording') recorder.stop();
    this.stream?.getTracks().forEach(track => track.stop());
    this.stream = undefined;
    if (this.context) void this.context.close().catch(() => {});
    this.context = undefined;
  }
  pause() {
    this.wanted = false;
    this.generation++;
    this.failures = 0;
    this.inputFailures = 0;
    clearTimeout(this.recoveryTimer);
    this.closeInput();
    this.status(this.stopped ? 'off' : 'paused');
  }
  resume() {
    if (this.stopped) return;
    this.wanted = true;
    if (!this.opening && !this.processing && !this.stream) void this.capture();
  }
  stop() { this.stopped = true; this.pause(); }
  private recoverInput(error: unknown) {
    const name = error instanceof Error ? error.name : '';
    const transient = ['AbortError', 'NotReadableError', 'NotFoundError', 'MicrophoneBusyError'].includes(name);
    if (transient && ++this.inputFailures < 3) {
      this.status('recovering');
      this.recoveryTimer = setTimeout(() => void this.capture(), this.inputFailures * 1000);
    } else {
      this.wanted = false;
      this.status('error');
      this.fail(error);
    }
  }
  private async capture() {
    if (!this.wanted || this.stopped || this.opening || this.processing || this.stream) return;
    this.opening = true;
    const generation = this.generation;
    try {
      const stream = await openMicrophone({audio: {
        deviceId: this.device ? {exact: this.device} : undefined,
        echoCancellation: true, noiseSuppression: true, autoGainControl: true,
      },video:false});
      if (generation !== this.generation || !this.wanted) { stream.getTracks().forEach(t=>t.stop()); return; }
      this.stream = stream;
      this.context = new AudioContext();
      await this.context.resume();
      if (generation !== this.generation || !this.wanted) { this.closeInput(); return; }
      for (const track of stream.getAudioTracks()) {
        track.onended = () => {
          if (generation !== this.generation || !this.wanted) return;
          this.generation++;
          this.closeInput();
          const error = new Error('El micrófono se desconectó durante la escucha.');
          error.name = 'NotReadableError';
          this.recoverInput(error);
        };
      }
      const analyser = this.context.createAnalyser();
      analyser.fftSize = 1024;
      this.context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      const record = () => {
        if (!this.wanted || generation !== this.generation || !this.stream) return;
        const recorder = new MediaRecorder(new MediaStream(stream.getAudioTracks()));
        this.recorder = recorder;
        const chunks: BlobPart[] = [];
        let heard = false, lastVoice = 0;
        const started = performance.now();
        recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
        recorder.onstop = () => {
          if (!this.wanted || generation !== this.generation) return;
          clearInterval(this.interval);
          if (!heard) { this.inputFailures = 0; record(); return; }
          this.recorder = undefined;
          this.processing = true;
          this.closeInput();
          this.status('processing');
          void (async () => {
            try {
              const pcm = await pcm16(new Blob(chunks,{type:recorder.mimeType}));
              if (!this.wanted || generation !== this.generation) return;
              const text = await this.transcribe(pcm);
              if (!this.wanted || generation !== this.generation) return;
              this.failures = 0;
              this.inputFailures = 0;
              const command = wakeCommand(text);
              if (command !== null) {
                this.wanted = false;
                this.status('paused');
                this.onWake?.(command);
              }
            } catch (error) {
              if (this.wanted && generation === this.generation) {
                this.failures++;
                const message = error instanceof Error ? error.message : '';
                const permanent = /Faltan dependencias|No se pudo cargar el modelo|incompleto en|petición inválida/.test(message);
                if (permanent || this.failures >= 3) {
                  this.wanted = false; this.status('error'); this.fail(error);
                } else this.status('recovering');
              }
            } finally {
              this.processing = false;
              if (this.wanted && !this.stopped) {
                if (this.failures) this.recoveryTimer = setTimeout(() => void this.capture(), this.failures * 1000);
                else void this.capture();
              }
            }
          })();
        };
        recorder.onerror = (event) => {
          if (generation !== this.generation || !this.wanted) return;
          // Invalidate onstop before closing: failed audio must never reach STT.
          this.generation++;
          this.closeInput();
          const cause = (event as Event & {error?: DOMException}).error;
          const error = new Error(cause?.message || 'Windows interrumpió la grabación.');
          error.name = cause?.name || 'NotReadableError';
          this.recoverInput(inputError(error, Boolean(this.device)));
        };
        recorder.start();
        this.interval = setInterval(() => {
          analyser.getFloatTimeDomainData(samples);
          let sum = 0;
          for (const sample of samples) sum += sample * sample;
          const now = performance.now();
          if (Math.sqrt(sum / samples.length) > 0.012 / this.sensitivity) { heard = true; lastVoice = now; }
          if ((heard && now - lastVoice > 850) || now - started > (heard ? 12000 : 4000)) {
            clearInterval(this.interval);
            if (recorder.state === 'recording') recorder.stop();
          }
        }, 50);
      };
      record();
      this.status('listening');
    } catch (error) {
      if (generation === this.generation && this.wanted) {
        this.closeInput();
        this.recoverInput(error);
      }
    } finally {
      this.opening = false;
      if (this.wanted && generation !== this.generation && !this.stream && !this.processing) void this.capture();
    }
  }
}
