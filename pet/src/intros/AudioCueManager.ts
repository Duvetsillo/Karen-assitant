import { mouthAt, type Greeting } from '../../shared/startup-intros';

/** Decodes one local WAV before playback; never calls the speech pipeline. */
export class AudioCueManager {
  private context?: AudioContext;
  private buffer?: AudioBuffer;
  private source?: AudioBufferSourceNode;
  private nodes: OscillatorNode[] = [];
  private greetingStart?: number;
  private fired = new Set<string>();
  private resuming?: Promise<void>;
  constructor(private volume: number, private greeting?: Greeting, private outputDevice = '') {}
  get hasGreeting() { return Boolean(this.buffer && this.volume > 0); }
  get greetingElapsed() { return this.greetingStart === undefined || !this.context ? undefined : Math.max(0, this.context.currentTime - this.greetingStart); }
  async prepare(bytes?: Uint8Array) {
    if (this.volume === 0) return;
    try {
      this.context = new AudioContext();
      if (this.outputDevice) {
        const output = this.context as AudioContext & { setSinkId?: (id: string) => Promise<void> };
        if (!output.setSinkId) throw new Error('Salida de audio no disponible.');
        await output.setSinkId(this.outputDevice);
      }
      if (bytes) this.buffer = await this.context.decodeAudioData(new Uint8Array(bytes).buffer);
      await this.context.resume();
    } catch { this.buffer = undefined; }
  }
  greetingCue() {
    if (this.fired.has('greeting')) return;
    if (!this.context || !this.buffer) { this.fired.add('greeting'); return; }
    if (this.context.state !== 'running') {
      if (!this.resuming) this.resuming = this.context.resume().then(() => {
        this.resuming = undefined;
        if (this.context?.state === 'running') this.greetingCue();
      }).catch(() => { this.resuming = undefined; this.buffer = undefined; });
      return;
    }
    this.fired.add('greeting');
    const gain = this.context.createGain(); gain.gain.value = this.volume;
    this.source = this.context.createBufferSource(); this.source.buffer = this.buffer;
    this.source.connect(gain).connect(this.context.destination);
    this.greetingStart = this.context.currentTime;
    this.source.start();
  }
  soundCue() {
    if (this.fired.has('effect') || !this.context || this.context.state !== 'running') return;
    this.fired.add('effect');
    const oscillator = this.context.createOscillator(), gain = this.context.createGain();
    const now = this.context.currentTime;
    oscillator.type = 'sine'; oscillator.frequency.setValueAtTime(170, now);
    oscillator.frequency.exponentialRampToValueAtTime(480, now + .18);
    gain.gain.setValueAtTime(0, now); gain.gain.linearRampToValueAtTime(this.volume * .1, now + .02);
    gain.gain.exponentialRampToValueAtTime(.0001, now + .25);
    oscillator.connect(gain).connect(this.context.destination);
    oscillator.start(now); oscillator.stop(now + .26); this.nodes.push(oscillator);
  }
  mouth() {
    return this.greetingStart === undefined || !this.context ? 0 : mouthAt(this.greeting, this.context.currentTime - this.greetingStart);
  }
  dispose() {
    try { this.source?.stop(); } catch { /* Already ended. */ }
    for (const node of this.nodes) { try { node.stop(); } catch { /* Already ended. */ } node.disconnect(); }
    this.source?.disconnect(); this.source = undefined; this.nodes = [];
    void this.context?.close().catch(() => {}); this.context = undefined; this.buffer = undefined;
  }
}
