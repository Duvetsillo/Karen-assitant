import { describe, expect, it } from 'vitest';
import { CoreActivityState } from '../shared/core-activity';

describe('shared activity is operation state, not pet expression', () => {
  it('clears thinking after the final reply expression', () => {
    const state = new CoreActivityState();
    expect(state.update({ type: 'pet', state: 'THINKING' })).toBe('THINKING');
    expect(state.update({ type: 'pet', state: 'HAPPY' })).toBe('IDLE');
    expect(state.update({ type: 'pet', state: 'SPEAKING' })).toBe('IDLE');
  });
  it('keeps real playback visible despite late completion and tool events', () => {
    const state = new CoreActivityState();
    expect(state.update({ type: 'capture', status: { kind: 'voice', phase: 'speaking' } })).toBe('SPEAKING');
    expect(state.update({ type: 'pet', state: 'HAPPY' })).toBe('SPEAKING');
    expect(state.update({ type: 'capture', status: { kind: 'voice', phase: 'idle' } })).toBe('IDLE');
  });
  it('reports actual wake capture and transcription', () => {
    const state = new CoreActivityState();
    expect(state.update({ type: 'wake-status', status: 'listening' })).toBe('LISTENING');
    expect(state.update({ type: 'wake-status', status: 'processing' })).toBe('TRANSCRIBING');
    expect(state.update({ type: 'wake-status', status: 'off' })).toBe('IDLE');
  });
});
