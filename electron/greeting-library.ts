import { readFileSync, realpathSync, statSync } from 'node:fs';
import { join, resolve, sep } from 'node:path';
import { INTRO_IDS, greetingCategory, type Greeting, type IntroId } from '../shared/startup-intros.js';
import type { Settings } from '../shared/types.js';

export function greetingVoiceVersion(settings: Settings, root: string): string {
  let identity = `system-speech:${process.platform}`;
  if (settings.ttsEngine === 'edge') throw new Error('Los saludos requieren un proveedor local.');
  if (settings.ttsEngine === 'local') {
    const profile = JSON.parse(readFileSync(join(root, 'voice-models/active-voice.json'), 'utf8'));
    if (!/^[a-z0-9-]{1,64}$/.test(profile.id) || !/^[a-f0-9]{64}$/.test(profile.reference_sha256)) throw new Error('Perfil de voz inválido.');
    identity = `${profile.id}:${profile.reference_sha256}`;
  } else if (settings.ttsEngine === 'fast') identity = 'kokoro-configured';
  return `${settings.ttsEngine}:${identity}:${settings.voiceStyle}:v1`;
}

/** Per-playback cache, bounded and discarded when the window closes. No synthesis path. */
export class ResourceCache {
  private audio?: Uint8Array;
  load(root: string, file: string) {
    if (!/^[a-z0-9-]{1,64}\.wav$/.test(file)) throw new Error('Archivo de saludo inválido.');
    const base = realpathSync(root), path = realpathSync(resolve(base, file));
    if (!path.startsWith(base + sep) || statSync(path).size > 4_000_000) throw new Error('Audio fuera de límites.');
    const data = readFileSync(path);
    if (data.length > 4_000_000) throw new Error('Audio fuera de límites.');
    if (data.subarray(0, 4).toString() !== 'RIFF' || data.subarray(8, 12).toString() !== 'WAVE') throw new Error('Se necesita WAV.');
    this.audio = new Uint8Array(data);
    return this.audio;
  }
  clear() { this.audio = undefined; }
}
export class GreetingLibrary {
  constructor(private root: string, private cache: ResourceCache, private voiceVersion?: string) {}
  choose(id: IntroId, hour: number, text?: string): { greeting?: Greeting; audio?: Uint8Array } {
    try {
      const path = join(this.root, 'manifest.json');
      if (statSync(path).size > 500_000) return {};
      const manifest = JSON.parse(readFileSync(path, 'utf8'));
      if (manifest.schema !== 1 || !Array.isArray(manifest.greetings)) return {};
      const valid = manifest.greetings.slice(0, 100).filter((g: Greeting) =>
        g && typeof g.id === 'string' && typeof g.text === 'string' && g.text.length < 500 &&
        typeof g.file === 'string' && typeof g.voiceVersion === 'string' &&
        (this.voiceVersion === undefined || g.voiceVersion === this.voiceVersion) &&
        (text === undefined || g.text === text) &&
        Array.isArray(g.intros) && g.intros.includes(id) && g.intros.every(i => INTRO_IDS.includes(i)) &&
        Number.isFinite(g.duration) && g.duration > 0 && g.duration <= 15 &&
        Number.isFinite(g.envelopeStep) && g.envelopeStep >= .01 && g.envelopeStep <= .1 &&
        Array.isArray(g.envelope) && g.envelope.length <= 1501 && g.envelope.length >= Math.floor(g.duration / g.envelopeStep) &&
        g.envelope.every(n => Number.isFinite(n) && n >= 0 && n <= 1));
      const category = id === 'surprise' ? 'humor' : greetingCategory(hour);
      let choices = valid.filter((g: Greeting) => g.category === category);
      if (!choices.length) choices = valid.filter((g: Greeting) => g.category === 'general');
      if (!choices.length) return {};
      const greeting: Greeting = choices[Math.floor(Math.random() * choices.length)];
      return { greeting, audio: this.cache.load(this.root, greeting.file) };
    } catch { return {}; }
  }
}
