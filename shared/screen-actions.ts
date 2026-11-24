export type ScreenActionIntent =
  | { kind: 'click'; target: string }
  | { kind: 'type'; target: string; text: string };

/** Natural language is only routed to this path for explicit, bounded actions. */
export function screenActionIntent(value: string): ScreenActionIntent | null {
  const text = value.trim().replace(/^(?:oye|hola|hey|ok|okay)[,\s]+/i, '').replace(/^(?:karen|caren)[,.:\s]+/i, '');
  const typing = text.match(/^(?:escribe|teclea|escribir)\s+["“]([^"”\r\n]{1,500})["”]\s+(?:en|dentro de|donde dice)\s+(.+)$/i);
  if (typing) {
    const target = cleanTarget(typing[2]);
    return target ? { kind: 'type', target, text: typing[1] } : null;
  }
  const click = text.match(/^(?:(?:haz|haga)\s+(?:un\s+)?|puedes\s+(?:hacer\s+)?|por favor\s+)?(?:clic|click|pulsa|presiona)\s+(?:en|sobre)\s+(.+)$/i);
  const target = click ? cleanTarget(click[1]) : '';
  return target ? { kind: 'click', target } : null;
}

function cleanTarget(value: string) {
  return value.replace(/[.!?]+$/, '').trim().slice(0, 180);
}

export function parseScreenActionPoint(value: string): { x: number; y: number; text: string } | null {
  const point = value.match(/^\s*\[\[KAREN_ACTION:\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*,\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*\]\]\s*/i);
  if (!point) return null;
  return { x: Number(point[1]), y: Number(point[2]), text: value.slice(point[0].length).trim() };
}
