import { describe, expect, it } from 'vitest';
import { report, useStore } from '../src/state/store';

describe('error visible para Karen', () => {
  it('muestra la causa sin el prefijo interno de Electron', () => {
    report(new Error("Error invoking remote method 'transcribe': Error: El modelo no pudo cargarse."));
    expect(useStore.getState().error).toBe('El modelo no pudo cargarse.');
  });
});
