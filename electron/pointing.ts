export function pointCoordinates(bounds: { x: number; y: number; width: number; height: number }, x: number, y: number) {
  if (![x, y].every(value => Number.isFinite(value) && value >= 0 && value <= 1))
    throw new Error('Punto de pantalla inválido.');
  return { x: Math.round(bounds.x + x * bounds.width), y: Math.round(bounds.y + y * bounds.height) };
}

export function parsePointDirective(text: string) {
  const point = text.match(/^\s*\[\[POINT:\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*,\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*\]\]\s*/i);
  if (point) return { x: Number(point[1]), y: Number(point[2]), text: text.slice(point[0].length).trim() };
  return { text: text.replace(/^\s*\[\[(?:NO_POINT|POINT:[^\]]*)\]\]\s*/i, '').trim() };
}

export function stripPointPrefix(text: string) {
  return text.replace(/^\s*\[\[(?:POINT|NO_POINT|KAREN_(?:NO_)?ACTION)(?::[^\]]*)?(?:\]\])?\s*/i, '').trim();
}

export function screenPointIntent(text: string): string | null {
  const spoken = text.trim().replace(/^(?:karen|caren)[,.:\s]+/i, '');
  const direct = spoken.match(/^(?:señala|senala|apunta a|pon(?:le)? (?:el|tu) dedo (?:sobre|encima de|encima a))\s+(.+)$/i);
  const show = /\b(?:pantalla|escritorio)\b/i.test(spoken) ? spoken.match(/^(?:muéstrame|muestrame|indica)\s+(.+)$/i) : null;
  const target = (direct || show)?.[1]?.replace(/\s+(?:en|de)\s+(?:mi|la|el)\s+(?:pantalla|escritorio)[.!?]*$/i, '').replace(/[.!?]+$/, '').trim();
  return target && target.length <= 300 ? target : null;
}

/** A temporary, click-through visual cue. Values are numeric and validated before interpolation. */
export function pointingMarkup(width: number, height: number, x: number, y: number, origin?: { x: number; y: number }) {
  const beam = origin ? `<path d="M ${origin.x} ${origin.y} Q ${(origin.x + x) / 2} ${Math.min(origin.y, y) - 42} ${x} ${y}" fill="none" stroke="#8be4f3" stroke-width="4" stroke-linecap="round" opacity=".85"/>` : '';
  const start = origin ?? { x: x - 72, y: y + 72 };
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><style>
    html,body{width:100%;height:100%;margin:0;background:transparent;overflow:hidden;pointer-events:none}
    .beam{position:absolute;inset:0;filter:drop-shadow(0 0 7px #56dcf5)}
    .target{position:absolute;left:${x}px;top:${y}px;transform:translate(-50%,-50%);width:42px;height:42px;border:3px solid #d8fbff;border-radius:50%;box-shadow:0 0 0 7px #4ddbf444,0 0 18px #67ecff;background:#3ad7ee22;animation:pulse 1.1s ease-in-out infinite alternate}
    .finger{position:absolute;left:${x}px;top:${y}px;width:54px;height:67px;transform:translate(-20%,-105%);filter:drop-shadow(0 0 7px #193647);animation:reach .45s cubic-bezier(.23,1,.32,1) both}
    .label{position:absolute;left:${x}px;top:${y}px;transform:translate(24px,25px);font:600 13px 'Segoe UI',sans-serif;color:#eaffff;background:#162935e8;border:1px solid #7fe3f3;border-radius:9px;padding:6px 9px;white-space:nowrap}
    @keyframes pulse{to{box-shadow:0 0 0 13px #4ddbf411,0 0 25px #67ecff}}
    @keyframes reach{from{opacity:0;transform:translate(calc(-20% + ${start.x - x}px),calc(-105% + ${start.y - y}px)) scale(.9)}to{opacity:1;transform:translate(-20%,-105%) scale(1)}}
    @media (prefers-reduced-motion:reduce){.target,.finger{animation:none}}
  </style></head><body><svg class="beam" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">${beam}</svg><div class="target"></div><svg class="finger" viewBox="0 0 54 67" aria-hidden="true"><path d="M12 59C6 53 5 43 5 36c0-6 7-8 10-2l6 9V11c0-8 10-8 10 0v25c2-6 10-7 12-1 6-1 10 4 10 10 0 7-3 14-8 18H19Z" fill="#b8eafb" stroke="#f2ffff" stroke-width="2.5" stroke-linejoin="round"/><path d="M24 14v28m8-6v8m8-8v8" fill="none" stroke="#6ebad8" stroke-width="2" stroke-linecap="round"/></svg><div class="label">Karen señala aquí</div></body></html>`;
}
