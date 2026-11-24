import type { Settings } from './types.js';
import type { InitiativeKind, InitiativeNotice, InitiativeSnapshot } from './initiative.js';

export interface InitiativeJournal {
  version: 1;
  day: string;
  count: number;
  lastAt: number;
  snoozedUntil: number;
  greetingDay: string;
  sequence: number;
  seenTasks: string[];
  notices: InitiativeNotice[];
}
export interface InitiativeContext {
  now: number;
  hour: number;
  day: string;
  present: boolean;
  visible: boolean;
  busy: boolean;
  lastInteraction: number;
  disconnectedSince: number;
  taskChanges: { key: string; status: string; id: string }[];
}
export function freshInitiativeJournal(): InitiativeJournal {
  return {version:1,day:'',count:0,lastAt:0,snoozedUntil:0,greetingDay:'',sequence:0,seenTasks:[],notices:[]};
}
export function localDay(now: number): string {
  const d = new Date(now);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
export function quietHour(hour: number, start: number, end: number): boolean {
  if (start === end) return false;
  return start < end ? hour >= start && hour < end : hour >= start || hour < end;
}
export function initiativeSnapshot(j: InitiativeJournal, now: number): InitiativeSnapshot {
  return {version:1,notices:j.notices.map(n=>({...n})),snoozedUntil:j.snoozedUntil,lastAt:j.lastAt,todayCount:j.day===localDay(now)?j.count:0};
}

/** Only local suggestions. Never invokes a model, tool, microphone or permission flow. */
export function proposeInitiative(s: Settings, j: InitiativeJournal, c: InitiativeContext, explicit = false):
  {kind: InitiativeKind; text: string; reason: string; command?: string; taskKey?: string} | null {
  if (!s.initiativeEnabled || s.mode !== 'normal' || !c.present || !c.visible || c.busy) return null;
  if (!explicit && (quietHour(c.hour,s.initiativeQuietStart,s.initiativeQuietEnd) ||
    c.now < j.snoozedUntil || c.now < j.lastAt ||
    (j.day === c.day && j.count >= s.initiativeDailyLimit) ||
    (j.lastAt > 0 && c.now - j.lastAt < s.initiativeInterval * 60000) ||
    c.now - c.lastInteraction < 90000 ||
    j.notices.some(n=>!n.dismissed && c.now-n.at < 120000))) return null;
  const task = c.taskChanges.find(t=>t.key.length<=160 && !j.seenTasks.includes(t.key) && /^[0-9a-f]{32}$/.test(t.id) &&
    ['completed','failed','awaiting_approval','canceled','uncertain','interrupted'].includes(t.status));
  if (task) {
    const text = task.status === 'completed' ? 'Una tarea terminó. ¿Quieres revisar su resultado?' :
      task.status === 'failed' ? 'Una tarea encontró un problema. ¿Revisamos qué ocurrió?' :
      task.status === 'awaiting_approval' ? 'Hay una tarea esperando tu aprobación. Puedes revisarla antes de decidir.' :
      ['uncertain','interrupted'].includes(task.status) ? 'Una tarea se interrumpió. Su resultado necesita revisión antes de continuar.' :
      'Una tarea se canceló. Puedo mostrarte su último estado.';
    return {kind:'task',text,reason:'Cambio de estado registrado en Karen Core',command:`/tareas estado ${task.id}`,taskKey:task.key};
  }
  if (j.greetingDay !== c.day) return {
    kind:'greeting', text:c.hour<12?'Buenos días. ¿Cómo quieres empezar hoy?':c.hour<20?'Hola. ¿Seguimos con algo pendiente o empezamos algo nuevo?':'Buenas noches. ¿Quieres que organicemos lo que queda para mañana?',
    reason:'Primer saludo del día, con el equipo en uso',
  };
  if (c.disconnectedSince > 0 && c.now-c.disconnectedSince >= 120000 &&
    !j.notices.some(n=>n.kind==='connection' && localDay(n.at)===c.day)) return {
    kind:'connection', text:'La conexión con OpenClaw sigue interrumpida. Puedes revisar el diagnóstico; las consultas Core siguen disponibles.',
    reason:'Desconexión observada durante al menos dos minutos',
  };
  const choices = [
    '¿Cómo vas con lo que estás haciendo? Si quieres, podemos ordenar el siguiente paso.',
    '¿Hay algo que quieras dejar anotado para retomarlo después?',
    'Podemos revisar tus tareas pendientes cuando te venga bien.',
    '¿Quieres conversar un rato o prefieres que siga en silencio?',
  ];
  return {kind:'check-in',text:choices[j.sequence%choices.length],reason:'Intervalo de compañía, con el equipo en uso'};
}
