import { AVATAR_STATES } from '../../shared/avatar-states';
import type { CaptureStatus, PetState } from '../../shared/types';
import { PresenceSpring } from './presence-motion';

export interface VisualContext { capture: CaptureStatus; music: boolean; focused?: boolean; }

/** Priority selection plus interruptible pose blending, independent of the LLM. */
export class AvatarController {
  private tilt = new PresenceSpring();
  private eyes = new PresenceSpring();
  private gaze = new PresenceSpring();
  private lift = new PresenceSpring();
  private time = 0;
  constructor() { this.eyes.reset(1); }
  resolve(base: PetState, context: VisualContext): PetState {
    const candidates: PetState[] = [base];
    if (context.capture.phase === 'recording') candidates.push('LISTENING');
    if (context.capture.phase === 'speaking') candidates.push('SPEAKING');
    if (context.capture.phase === 'preparing') candidates.push('THINKING');
    if (context.music) candidates.push('MUSIC_LISTENING');
    if (context.focused) candidates.push('FOCUSED');
    return candidates.reduce((current,next) => AVATAR_STATES[next].priority > AVATAR_STATES[current].priority ? next : current);
  }
  update(state: PetState, seconds: number, enabled: boolean, activity: number) {
    const dt = Number.isFinite(seconds) ? Math.max(0,Math.min(.1,seconds)) : 0;
    const amount = Math.max(0,Math.min(1,Number.isFinite(activity) ? activity : 0));
    const profile = AVATAR_STATES[state];
    if (!enabled) {
      this.tilt.reset(); this.gaze.reset(); this.lift.reset(); this.eyes.reset(profile.eyes);
      return { tilt:0,eyes:profile.eyes,gaze:0,lift:0 };
    }
    this.time += dt;
    return {
      tilt: this.tilt.update((profile.tilt + Math.sin(this.time * 1.8) * profile.wave) * amount,dt),
      eyes: this.eyes.update(profile.eyes,dt),
      gaze: this.gaze.update(Math.sin(this.time * (state === 'READING' ? 1.1 : .7)) * profile.scan * amount,dt),
      lift: this.lift.update(profile.lift * amount,dt),
    };
  }
}
