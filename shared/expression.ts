import type { PetState } from './types.js';

/** Visual delivery cues from Karen's own reply. Never infer the user's feelings. */
export function expressionForReply(text: string): PetState {
  const reply = text.replace(/```[\s\S]*?(?:```|$)/g, ' ')
    .replace(/^\s*>.*$/gm, ' ')
    .replace(/`[^`]*`/g, ' ')
    .slice(0, 1200)
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (/\b(?:(?:ja){2,}|(?:je){2,}|me (?:hizo|hace) gracia|que risa|me rio)\b/.test(reply)) return 'LAUGHING';
  if (/\b(?:me (?:molesta|enfada|indigna)|que rabia|esto (?:me irrita|es indignante)|estoy harta)\b/.test(reply)) return 'ANGRY';
  if (/\b(?:lo siento|lamento (?:mucho|esto|que)|que tristeza|me entristece)\b/.test(reply)) return 'SAD';
  if (/\b(?:no me lo esperaba|que sorpresa|vaya sorpresa|increible|sorprendente)\b/.test(reply)) return 'SURPRISED';
  if (/\b(?:lo logramos|lo conseguimos|bien hecho|me enorgullece|buen trabajo)\b/.test(reply)) return 'PROUD';
  if (/\b(?:me intriga|tengo curiosidad|me pregunto|interesante pregunta)\b/.test(reply)) return 'CURIOUS';
  return 'HAPPY';
}
