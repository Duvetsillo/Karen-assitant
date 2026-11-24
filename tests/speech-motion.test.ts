import { describe, expect, it } from 'vitest';
import { SpeechMotion } from '../src/pet/speech-motion';

describe('gestos guiados por la voz', () => {
  it('reacciona al inicio de una palabra, decae y alterna los brazos', () => {
    const motion = new SpeechMotion();
    const first = motion.update(0.7, 0.04, true, true);
    expect(first.envelope).toBeGreaterThan(0);
    expect(first.gesture).toBe(1);
    for (let i = 0; i < 13; i++) motion.update(0.7, 0.04, true, true);
    const held = motion.update(0.7, 0.04, true, true);
    expect(held.gesture).toBeLessThan(0.1);
    motion.update(0, 0.04, true, true);
    const second = motion.update(0.8, 0.04, true, true);
    expect(second.gesture).toBe(1);
    expect(second.side).not.toBe(first.side);
  });

  it('deja de mover el cuerpo al callarse o activar movimiento reducido', () => {
    const motion = new SpeechMotion();
    motion.update(1, 0.04, true, true);
    expect(motion.update(1, 0.04, true, false)).toMatchObject({ envelope: 0, gesture: 0 });
    expect(motion.update(1, 0.04, false, true)).toMatchObject({ envelope: 0, gesture: 0 });
    expect(motion.update(Number.NaN, 0.04, true, true).envelope).toBe(0);
  });
});
