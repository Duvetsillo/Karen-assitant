export type InitiativeKind = 'greeting' | 'check-in' | 'connection' | 'task';
export interface InitiativeNotice {
  id: string;
  at: number;
  kind: InitiativeKind;
  text: string;
  reason: string;
  command?: string;
  dismissed: boolean;
}
export interface InitiativeSnapshot {
  version: 1;
  notices: InitiativeNotice[];
  snoozedUntil: number;
  lastAt: number;
  todayCount: number;
}
export type InitiativeAction = 'now' | 'dismiss' | 'snooze' | 'resume';
