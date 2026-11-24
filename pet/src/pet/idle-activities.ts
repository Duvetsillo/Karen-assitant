import type { PetState, Settings } from '../../shared/types';

export type IdleActivity = 'none' | 'play' | 'stretch' | 'stargaze';
export interface IdleFrame { kind: IdleActivity; progress: number; }
interface Input {
  settings: Settings;
  state: PetState;
  lastActivity: number;
  blocked: boolean;
  reducedMotion: boolean;
}
const durations = { play: 8500, stretch: 6500, stargaze: 10000 } as const;

/** Decorative clips only. Never changes assistant state or produces tool calls. */
export class IdleActivities {
  private kind: IdleActivity = 'none';
  private since = 0;
  private nextAt = 0;
  private sequence = 0;
  private previousTime = 0;
  private previousDelay: number | undefined;
  private wasAllowed: boolean | undefined;
  suspend(now: number, delaySeconds: number) {
    this.kind = 'none';
    this.nextAt = now + delaySeconds * 1000;
  }
  update(input: Input, now = Date.now()): IdleFrame {
    const { settings: s } = input;
    const allowed = s.idleActivities && s.animations && s.activity > 0 && !s.lowPower &&
      !input.reducedMotion && !input.blocked && input.state === 'IDLE';
    const delayChanged=this.previousDelay!==undefined && this.previousDelay!==s.idleAfter;
    if (!allowed || now < this.previousTime || delayChanged || (allowed && this.wasAllowed===false) ||
      (this.kind !== 'none' && input.lastActivity > this.since)) {
      this.kind = 'none';
      this.nextAt = now + s.idleAfter * 1000;
    }
    this.previousTime = now;
    this.previousDelay=s.idleAfter;
    this.wasAllowed=allowed;
    if (!allowed) return { kind: 'none', progress: 0 };
    if (this.kind !== 'none') {
      const progress = (now - this.since) / durations[this.kind];
      if (progress < 1) return { kind: this.kind, progress: Math.max(0, progress) };
      this.kind = 'none';
      this.nextAt = now + (60 + (1 - s.activity) * 40) * 1000;
    }
    if (now >= Math.max(this.nextAt, input.lastActivity + s.idleAfter * 1000)) {
      const choices = ['play', 'stretch', 'stargaze'] as const;
      this.kind = s.idleActivity === 'variety' ? choices[this.sequence++ % choices.length] : s.idleActivity;
      this.since = now;
      return { kind: this.kind, progress: 0 };
    }
    return { kind: 'none', progress: 0 };
  }
}
