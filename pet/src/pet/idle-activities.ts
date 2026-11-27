import type { PetState, Settings } from '../../shared/types';
import { IDLE_CLIPS,type IdleClip } from '../../shared/idle-clips';

export type IdleActivity = 'none' | IdleClip;
export interface IdleFrame { kind: IdleActivity; progress: number; }
interface Input {
  settings: Settings;
  state: PetState;
  lastActivity: number;
  blocked: boolean;
  reducedMotion: boolean;
}

/** Decorative clips only. Never changes assistant state or produces tool calls. */
export class IdleActivities {
  private kind: IdleActivity = 'none';
  private since = 0;
  private nextAt = 0;
  private previous?: IdleActivity;
  private remaining:IdleClip[]=[];
  constructor(private random: () => number = Math.random) {}
  private roll() { const value=this.random(); return Number.isFinite(value) ? Math.max(0,Math.min(.999999,value)) : .5; }
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
      const progress = (now - this.since) / IDLE_CLIPS[this.kind].duration;
      if (progress < 1) return { kind: this.kind, progress: Math.max(0, progress) };
      this.kind = 'none';
      this.nextAt = now + (18 + (1 - s.activity) * 72) * ( .85 + this.roll() * .3) * 1000;
    }
    if (now >= Math.max(this.nextAt, input.lastActivity + s.idleAfter * 1000)) {
      if(!this.remaining.length)this.remaining=(Object.keys(IDLE_CLIPS) as IdleClip[]).filter(kind=>kind!==this.previous);
      this.kind = s.idleActivity === 'variety' ? this.remaining.splice(Math.floor(this.roll()*this.remaining.length),1)[0] : s.idleActivity;
      this.previous = this.kind;
      this.since = now;
      return { kind: this.kind, progress: 0 };
    }
    return { kind: 'none', progress: 0 };
  }
}
