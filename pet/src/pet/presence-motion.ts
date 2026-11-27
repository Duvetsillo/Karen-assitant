import type { PetState } from '../../shared/types';

/** Analytic mass=1, stiffness=100, damping=10 spring. Retargeting keeps velocity. */
export class PresenceSpring {
  value = 0;
  private velocity = 0;

  reset(value = 0) { this.value = value; this.velocity = 0; }

  update(target: number, seconds: number) {
    if (!Number.isFinite(target) || !Number.isFinite(seconds)) return this.value;
    const dt = Math.max(0, Math.min(.1, seconds));
    if (dt === 0) return this.value;
    const frequency = Math.sqrt(75);
    const offset = this.value - target;
    const decay = Math.exp(-5 * dt);
    const sine = Math.sin(frequency * dt), cosine = Math.cos(frequency * dt);
    const next = decay * (offset * cosine + (this.velocity + 5 * offset) / frequency * sine);
    this.velocity = decay * (this.velocity * cosine - (5 * this.velocity + 100 * offset) / frequency * sine);
    this.value = target + next;
    return this.value;
  }
}

export const PRESENCE_PRESETS = [
  { name: 'Desactivado', activity: 0, description: 'Sin movimiento ambiental.' },
  { name: 'Discreto', activity: .25, description: 'Gestos pequeños y pausas amplias.' },
  { name: 'Natural', activity: .6, description: 'Una presencia suave y variada.' },
  { name: 'Expresivo', activity: .9, description: 'Mayor expresividad visual.' },
  { name: 'Muy interactivo', activity: 1, description: 'La mayor intensidad, con cooldowns y límites.' },
] as const;

/** One short response to a state change; never an endless celebration loop. */
export class PresenceMotion {
  private state?: PetState;
  private time = 0;
  private age = 10;
  private lift = new PresenceSpring();
  private hand = new PresenceSpring();

  reset() {
    this.state = undefined;
    this.age = 10;
    this.lift.reset();
    this.hand.reset();
  }

  update(state: PetState, seconds: number, enabled: boolean, activity: number) {
    const dt = Number.isFinite(seconds) ? Math.max(0, Math.min(.1, seconds)) : 0;
    const intensity = Number.isFinite(activity) ? Math.max(0, Math.min(1, activity)) : 0;
    if (!enabled) {
      this.reset();
      this.state = state;
      return { bob: 0, greeting: 0, lift: 0, breath: 0, glance: 0 };
    }
    this.time += dt;
    this.age += dt;
    if (this.state !== state) {
      if (this.state !== undefined) this.age = 0;
      this.state = state;
    }
    const sleeping = state === 'SLEEPING';
    const pulse = this.age < 1.8 ? Math.exp(-3 * this.age) * Math.sin(9 * this.age) : 0;
    const greeting = state === 'HAPPY' && this.age < 1.4
      ? Math.sin(Math.PI * Math.min(1, this.age / 1.4)) ** 2 * (.6 + .4 * Math.sin(this.age * 15)) : 0;
    const lift = (state === 'HAPPY' ? -15 : state === 'SURPRISED' ? -11 : state === 'PROUD' ? -5 : 0) * pulse * intensity;
    return {
      bob: (Math.sin(this.time * (sleeping ? .5 : 1.1)) * 4 + Math.sin(this.time * .43) * 1.5) * intensity,
      greeting: this.hand.update(greeting * intensity, dt),
      lift: this.lift.update(lift, dt),
      breath: Math.sin(this.time * (sleeping ? .65 : 1.1)) * .008 * intensity,
      glance: state === 'IDLE' ? Math.sin(this.time * .32) * 2.5 * intensity : 0,
    };
  }
}
