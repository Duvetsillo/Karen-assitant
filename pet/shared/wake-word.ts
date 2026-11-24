/** Only an addressed name wakes Karen; a name inside ordinary speech does not. */
export function wakeCommand(text: string): string | null {
  const clean = text.trim().replace(/^[¿¡\s]+/, '');
  const normalized = clean.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const match = /^(?:(?:oye|hola|hey|ok|okay)[,\s]+)?(?:karen|caren)\b[\s,;:.!?¿¡-]*/i.exec(normalized);
  return match ? clean.slice(match[0].length).trim() : null;
}
