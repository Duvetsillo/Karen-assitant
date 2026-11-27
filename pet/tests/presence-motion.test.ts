import { describe, expect, it } from 'vitest';
import { PresenceMotion, PresenceSpring, PRESENCE_PRESETS } from '../src/pet/presence-motion';
import type { PetState } from '../shared/types';

describe('physical pet presence', () => {
  it('keeps spring timing independent of render frequency', () => {
    const at = (fps: number) => { const spring = new PresenceSpring(); for (let i = 0; i < fps; i++) spring.update(10, 1 / fps); return spring.value; };
    expect(at(24)).toBeCloseTo(at(60), 9);
    expect(at(60)).toBeCloseTo(10, 1);
  });

  it('retargets a moving spring without teleporting', () => {
    const spring = new PresenceSpring();
    spring.update(10, .1);
    const before = spring.value;
    expect(spring.update(-10, 0)).toBe(before);
    expect(Number.isFinite(spring.update(-10, 1 / 60))).toBe(true);
    expect(Math.abs(spring.value - before)).toBeLessThan(2);
  });

  it('does not replay a greeting when a hidden surface is shown again', () => {
    const motion = new PresenceMotion();
    motion.update('IDLE', .016, true, .6);
    motion.update('HAPPY', .016, true, .6);
    for (let i = 0; i < 20; i++) motion.update('HAPPY', .016, true, .6);
    motion.reset();
    expect(motion.update('HAPPY', .016, true, .6).greeting).toBe(0);
  });

  it('finishes its greeting instead of bouncing forever in a happy state', () => {
    const motion = new PresenceMotion();
    motion.update('IDLE', .016, true, .6);
    let maximum = 0, last = motion.update('HAPPY', .016, true, .6);
    for (let i = 0; i < 300; i++) {
      last = motion.update('HAPPY', 1 / 60, true, .6);
      maximum = Math.max(maximum, last.greeting);
    }
    expect(maximum).toBeGreaterThan(.1);
    expect(Math.abs(last.greeting)).toBeLessThan(.001);
    expect(Math.abs(last.lift)).toBeLessThan(.001);
  });

  it('removes decorative motion immediately when animations are disabled', () => {
    const motion = new PresenceMotion();
    motion.update('IDLE', .016, true, 1);
    for (let i = 0; i < 30; i++) motion.update('HAPPY', .016, true, 1);
    expect(motion.update('HAPPY', .016, false, 1)).toEqual({bob: 0, greeting: 0, lift: 0, breath: 0, glance: 0});
  });

  it('bounds stale frame times and invalid intensity across every state', () => {
    const motion = new PresenceMotion();
    const states: PetState[] = ['IDLE', 'HAPPY', 'THINKING', 'SPEAKING', 'SLEEPING', 'DRAGGING', 'ERROR'];
    for (const state of states) for (const dt of [NaN, -1, 100, .016]) for (const activity of [NaN, -1, 100, .6]) {
      const frame = motion.update(state, dt, true, activity);
      expect(Object.values(frame).every(Number.isFinite)).toBe(true);
      expect(Math.abs(frame.bob)).toBeLessThanOrEqual(5.5);
    }
  });

  it('uses existing persisted activity settings for its five activity levels', () => {
    expect(PRESENCE_PRESETS.map(preset => preset.activity)).toEqual([0, .25, .6, .9, 1]);
  });
});
