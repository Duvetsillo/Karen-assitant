import type { ConnectionState } from './types.js';
import { introCommand } from './startup-intros.js';
import { musicCommand } from './music.js';

export function isCoreCommand(text: string): boolean {
  return /^\/(?:memoria|historial|core|tareas|planes|automatizaciones|desarrollo)(?:\s|$)/i.test(text.trim());
}

export function canSendMessage(text: string, connection: ConnectionState): boolean {
  text = text.trim();
  if (!text) return false;
  if (introCommand(text)) return true;
  if (musicCommand(text)) return true;
  if (connection === 'connected') return true;
  if (!isCoreCommand(text)) return false;
  // Explicit transfers deliver private context to a provider and need a connection.
  return !/^\/(?:memoria|historial)\s+enviar(?:\s|$)/i.test(text);
}
