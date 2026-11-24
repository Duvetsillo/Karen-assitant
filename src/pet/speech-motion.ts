/** Audio-driven movement. A rise in speech energy starts one short gesture. */
export class SpeechMotion {
  private envelope = 0;
  private gesture = 0;
  private previous = 0;
  private cooldown = 0;
  private side: 1 | -1 = 1;

  update(level: number, dt: number, speaking: boolean, motion: boolean) {
    if (!speaking || !motion) {
      this.envelope = 0;
      this.gesture = 0;
      this.previous = 0;
      this.cooldown = 0;
      return { envelope: 0, gesture: 0, side: this.side };
    }
    const input = Number.isFinite(level) ? Math.max(0, Math.min(1, level)) : 0;
    const seconds = Math.max(0, Math.min(dt, 0.1));
    const rate = input > this.envelope ? 13 : 5;
    this.envelope += (input - this.envelope) * (1 - Math.exp(-rate * seconds));
    this.gesture *= Math.exp(-5.5 * seconds);
    this.cooldown = Math.max(0, this.cooldown - seconds);
    if (input > 0.28 && input - this.previous > 0.12 && this.cooldown === 0) {
      this.side = this.side === 1 ? -1 : 1;
      this.gesture = 1;
      this.cooldown = 0.48;
    }
    this.previous = input;
    return { envelope: this.envelope, gesture: this.gesture, side: this.side };
  }
}
