import { AVATAR_STATES } from '../../shared/avatar-states';
import type { PetState } from "../../shared/types";
export interface MachineSnapshot {
  state: PetState;
  since: number;
  lastActivity: number;
  expires: number;
}
export class PetMachine {
  snapshot: MachineSnapshot;
  constructor(now = Date.now()) {
    this.snapshot = {
      state: "IDLE",
      since: now,
      lastActivity: now,
      expires: 0,
    };
  }
  transition(state: PetState, now = Date.now()): MachineSnapshot {
    if (
      state === this.snapshot.state &&
      AVATAR_STATES[state].duration === 0
    )
      return this.snapshot;
    this.snapshot = {
      state,
      since: now,
      lastActivity: state === "SLEEPING" ? this.snapshot.lastActivity : now,
      expires: AVATAR_STATES[state].duration ? now + AVATAR_STATES[state].duration : 0,
    };
    return this.snapshot;
  }
  wake(now = Date.now()) {
    return this.transition("HAPPY", now);
  }
  touch(now = Date.now()) {
    this.snapshot = { ...this.snapshot, lastActivity: now };
  }
  tick(sleepAfter: number, now = Date.now()) {
    if (this.snapshot.expires && now >= this.snapshot.expires)
      this.transition("IDLE", now);
    if (
      this.snapshot.state === "IDLE" &&
      now - this.snapshot.lastActivity >= sleepAfter * 1000
    )
      this.transition("SLEEPING", now);
    return this.snapshot;
  }
}
