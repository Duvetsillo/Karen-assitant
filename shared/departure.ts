import { clamp01, easeInOut } from './startup-intros.js';

export class DepartureTimeline {
  readonly duration: number;
  constructor(readonly reduced: boolean) { this.duration = reduced ? .18 : .78; }
  sample(seconds: number) {
    const progress = clamp01(seconds / this.duration);
    const leave = this.reduced ? progress : easeInOut((progress - .38) / .62);
    return {
      alpha: 1 - leave, y: this.reduced ? 0 : -28 * leave,
      scale: this.reduced ? 1 : 1 - .16 * leave,
      tilt: this.reduced ? 0 : -.07 * leave,
      wave: this.reduced ? 0 : Math.sin(Math.PI * clamp01(progress / .68)) * .42,
      wink: this.reduced || progress < .12 || progress > .36 ? 1 : .1,
      done: progress >= 1,
    };
  }
}
