/** Public task metadata only. Arguments, hashes, outputs and audit payloads stay local. */
export interface CoreTaskSummary {
  id: string;
  status: string;
  cursor: number;
  created_at: string;
  updated_at: string;
}
export interface CoreTaskDetail extends CoreTaskSummary {
  cancel_requested: boolean;
  steps: { ordinal: number; tool: string; permission: 'read' | 'reversible' | 'sensitive' | 'destructive'; status: string }[];
}
export interface CorePlanSummary { id: string; goal: string; status: string; created_at: string; updated_at: string }
export interface CorePlanDetail extends CorePlanSummary {
  steps: {step_id: string; ordinal: number; tool: string; agent: string; permission: string; status: string; attempts: number}[];
}
export interface CoreScheduleSummary {
  id: string; name: string; next_run: string; interval_seconds: number | null;
  retries: number; enabled: number; last_status: string | null;
  event_topic?: string | null;
}
export interface CoreHandoffSummary {
  id: string; project: string; status: string; priority: string; updated_at: string;
}
/** Labels are user data; payloads and credentials never belong in metadata replies. */
export function publicCoreLabel(value: string): string {
  if (/PRIVATE KEY/i.test(value)) return '[redactado]';
  return value.replace(/\b(password|passwd|contrase[nñ]a|api[_ -]?key|(?:access|refresh)[_ -]?token|token|secret|authorization|cookie)\s*[:=]\s*(?:bearer\s+)?\S+/gi, '$1=[redactado]')
    .replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer [redactado]');
}
