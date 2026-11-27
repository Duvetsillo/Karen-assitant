import type { Rectangle } from './pet-layout.js';

export const INTRO_IDS = ['breakthrough', 'glass', 'awakening', 'materialization', 'sleepy', 'surprise'] as const;
export type IntroId = typeof INTRO_IDS[number];
export interface IntroPreferences {
  farewellEnabled: boolean;
  introEnabled: boolean;
  introFrequency: 'startup' | 'daily' | 'after-away' | 'manual';
  introSelection: 'random' | 'fixed' | 'contextual';
  introFixed: IntroId;
  introVoice: boolean;
  introSounds: boolean;
  introVolume: number;
  introReducedMotion: boolean;
  introEscape: boolean;
  introFPS: 30 | 60;
  /** Empty selects the monitor containing the normal pet. */
  introMonitor: string;
}
export const introDefaults: IntroPreferences = {
  farewellEnabled: true,
  introEnabled: true, introFrequency: 'startup', introSelection: 'random', introFixed: 'awakening',
  introVoice: true, introSounds: true, introVolume: .65,
  introReducedMotion: false, introEscape: true, introFPS: 60, introMonitor: '',
};
export const IntroRegistry: Record<IntroId, { name: string; reveal: number; greeting: number }> = {
  breakthrough: { name: 'Breakthrough', reveal: 1.2, greeting: 1.8 },
  glass: { name: 'Glass', reveal: 1.6, greeting: 2.2 },
  awakening: { name: 'Awakening', reveal: 2.4, greeting: 3.1 },
  materialization: { name: 'Materialization', reveal: 2.1, greeting: 2.7 },
  sleepy: { name: 'Sleepy', reveal: 2.8, greeting: 3.5 },
  surprise: { name: 'Surprise', reveal: 2.1, greeting: 2.8 },
};
export function selectIntro(p: IntroPreferences, hour: number, previous?: IntroId, random = Math.random): IntroId {
  if (p.introSelection === 'fixed') return p.introFixed;
  if (p.introSelection === 'contextual') return hour < 6 ? 'sleepy' : hour < 12 ? 'awakening' : hour < 19 ? 'materialization' : 'glass';
  const choices = INTRO_IDS.filter(id => id !== previous);
  return choices[Math.min(choices.length - 1, Math.max(0, Math.floor(random() * choices.length)))];
}
export type IntroCommand = { kind: 'play'; id?: IntroId } | { kind: 'next' | 'random' | 'mute' };
/** Whole utterances only: ordinary conversation never accidentally starts an overlay. */
export function introCommand(text: string): IntroCommand | undefined {
  const s = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
    .replace(/^(?:karen|caren)[,.:!]?\s+/, '').replace(/[.!?]+$/, '');
  if (/^(?:reproduce|muestra) (?:tu |la )?introduccion$/.test(s)) return { kind: 'play' };
  if (/^cambia (?:tu |la )?introduccion$/.test(s)) return { kind: 'next' };
  if (s === 'usa introducciones aleatorias') return { kind: 'random' };
  if (s === 'desactiva los saludos de inicio') return { kind: 'mute' };
  const match = /^(?:reproduce|muestra) (\w+)$/.exec(s);
  if (match && INTRO_IDS.includes(match[1] as IntroId)) return { kind: 'play', id: match[1] as IntroId };
}
export interface Greeting {
  id: string; file: string; text: string; duration: number; category: string;
  intros: IntroId[]; voiceVersion: string;
  envelope: number[]; envelopeStep: number;
}
export function greetingCategory(hour: number): string {
  return hour < 6 ? 'madrugada' : hour < 12 ? 'morning' : hour < 20 ? 'afternoon' : 'night';
}
export function mouthAt(g: Greeting | undefined, seconds: number): number {
  if (!g || seconds < 0 || seconds >= g.duration) return 0;
  const index = seconds / g.envelopeStep;
  const a = g.envelope[Math.floor(index)] ?? 0, b = g.envelope[Math.ceil(index)] ?? a;
  return a + (b - a) * (index % 1);
}
export const clamp01 = (n: number) => Math.max(0, Math.min(1, n));
export const easeOut = (n: number) => 1 - (1 - clamp01(n)) ** 3;
export const easeInOut = (n: number) => { const p = clamp01(n); return p * p * (3 - 2 * p); };
const mix = (a: number, b: number, p: number) => a + (b - a) * p;
export interface IntroPose {
  bodyAlpha: number;
  x: number; y: number; scale: number; alpha: number; dark: number;
  eye: number; wink: number; gazeX: number; gazeY: number;
  ear: number; tilt: number; breathe: number; mouth: number;
  effect: number; exit: number; done: boolean;
}
/** Pure elapsed-time choreography, independent of frame rate and gateway events. */
export class IntroTimeline {
  readonly greetingAt: number;
  readonly leaveAt: number;
  readonly duration: number;
  constructor(readonly id: IntroId, readonly reduced: boolean, greetingSeconds = 0) {
    this.greetingAt = reduced ? .2 : IntroRegistry[id].greeting;
    this.leaveAt = this.greetingAt + Math.max(1.7, greetingSeconds + .25);
    this.duration = this.leaveAt + (reduced ? .3 : 1.15);
  }
  sample(t: number, width: number, height: number, target: Rectangle): IntroPose {
    const exit = easeInOut((t - this.leaveAt) / (this.duration - this.leaveAt));
    const large = Math.min(width / 480, height / 420) * .9;
    const normal = Math.min(target.width / 380, target.height / 440) * .8;
    let x = width / 2, y = height * .52, scale = large, alpha = 1, dark = .18;
    let eye = 1, wink = 1, ear = 0, tilt = 0, breathe = 1, mouth = 0, effect = 0;
    if (this.reduced) {
      x = target.x + target.width / 2; y = target.y + target.height * .54;
      scale = normal; alpha = easeOut(t / .25); dark = 0;
    } else {
      const reveal = IntroRegistry[this.id].reveal;
      effect = clamp01(t / reveal);
      switch (this.id) {
        case 'breakthrough': {
          const impact = Math.max(0, 1 - Math.abs(t - .85) / .65);
          scale *= .55 + .45 * easeOut(t / .8) + Math.sin(t * 17) * impact * .12;
          x += Math.sin(t * 36) * impact * width * .012;
          y += Math.cos(t * 28) * impact * height * .012;
          alpha = easeOut(t / .65); eye = t < 1.2 ? .45 : 1;
          tilt = Math.sin(t * 12) * impact * .12; ear = impact * .3; break;
        }
        case 'glass':
          alpha = easeOut((t - .5) / 1); eye = t < 1.4 ? 1.25 : 1;
          scale *= .85 + .15 * easeOut(t / 1.6); dark = .5 * (1 - exit); break;
        case 'awakening':
          dark = 1 - easeOut((t - 1.4) / 1.8);
          scale *= mix(4.8, 1, easeInOut((t - 1.1) / 1.8));
          y = height * .5 + 7 * scale; eye = easeInOut((t - .3) / 1.2); break;
        case 'materialization':
          alpha = easeInOut((t - .5) / 1.7); eye = easeOut((t - 1.6) / .45);
          y += (1 - easeOut(t / 2.1)) * height * .15; ear = Math.sin(t * 7) * .12; break;
        case 'sleepy':
          eye = easeInOut((t - 1.8) / 1.3); dark = .35;
          breathe = 1 + Math.sin(t * 2) * .025;
          tilt = -.09 * (1 - easeOut(t / 3)); ear = -.2 + .18 * easeOut(t / 3);
          mouth = Math.sin(Math.PI * clamp01((t - .9) / 1.3)) * .9; break;
        case 'surprise':
          if (t < .65) { x = mix(-large * 35, large * 75, easeOut(t / .65)); y = height * .63; tilt = .25; }
          else if (t < 1.1) { x = mix(large * 75, -large * 180, easeInOut((t - .65) / .45)); }
          else if (t < 1.65) { x = mix(width + large * 180, width - large * 75, easeOut((t - 1.1) / .55)); tilt = -.25; }
          else if (t < 2.5) { const jump = easeInOut((t - 1.65) / .85); x = mix(width - large * 75, width / 2, jump); y -= Math.sin(jump * Math.PI) * height * .22; }
          wink = t > 2.5 && t < 2.85 ? .04 : 1; break;
      }
      if (t > 2 && t % 3.1 < .14) eye *= Math.max(.05, Math.abs(t % 3.1 - .07) / .07);
      ear += Math.sin(t * 2.2) * .045;
    }
    const targetX = target.x + target.width / 2, targetY = target.y + target.height * .54;
    const bodyAlpha = this.id === 'awakening' && !this.reduced ? easeInOut((t - 2.05) / .85) : 1;
    return { x: mix(x, targetX, exit), y: mix(y, targetY, exit) - (this.reduced ? 0 : Math.sin(exit * Math.PI) * height * .08),
      scale: mix(scale, normal, exit), alpha, bodyAlpha, dark: dark * (1 - exit), eye: mix(eye, 1, exit), wink: mix(wink, 1, exit),
      gazeX: this.reduced ? 0 : Math.sin(t * 1.4) * 7 * (1 - exit), gazeY: this.reduced ? 0 : Math.cos(t) * 3 * (1 - exit),
      ear: ear * (1 - exit), tilt: tilt * (1 - exit), breathe: mix(breathe, 1, exit), mouth: mouth * (1 - exit), effect, exit, done: t >= this.duration };
  }
}
export interface IntroPayload {
  id: IntroId; settings: import('./types.js').Settings; target: Rectangle;
  greeting?: Greeting; audio?: Uint8Array;
}


export function shouldPlayIntro(preferences: IntroPreferences, trigger: 'startup'|'return', now: number, lastPlayed: number) {
  if (!preferences.introEnabled || preferences.introFrequency === 'manual') return false;
  if (preferences.introFrequency === 'after-away') return trigger === 'return';
  if (preferences.introFrequency === 'startup') return trigger === 'startup';
  return !lastPlayed || new Date(now).toDateString() !== new Date(lastPlayed).toDateString();
}
