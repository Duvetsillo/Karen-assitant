import type { CaptureStatus, DesktopEvent, PetState, WakeStatus } from './types.js';

export type ActivityState = 'IDLE' | 'LISTENING' | 'TRANSCRIBING' | 'THINKING' | 'SPEAKING' | 'ERROR';

/** Physical capture wins over decorative expressions and late Gateway events. */
export class CoreActivityState {
  private capture: CaptureStatus = { kind: 'microphone', phase: 'idle' };
  private wake: WakeStatus = 'off';
  private pet: PetState = 'IDLE';

  update(event: DesktopEvent): ActivityState {
    if (event.type === 'capture') this.capture = event.status;
    if (event.type === 'wake-status') this.wake = event.status;
    if (event.type === 'pet') this.pet = event.state;
    if (this.capture.phase !== 'idle') return ({
      recording: 'LISTENING', transcribing: 'TRANSCRIBING', preparing: 'THINKING', speaking: 'SPEAKING',
    } as const)[this.capture.phase];
    if (this.pet === 'THINKING') return 'THINKING';
    if (this.wake === 'processing') return 'TRANSCRIBING';
    if (this.wake === 'listening' || this.pet === 'LISTENING') return 'LISTENING';
    if (this.wake === 'error' || this.pet === 'ERROR') return 'ERROR';
    // SPEAKING without a playback event is an expression, not physical audio.
    return 'IDLE';
  }
}
