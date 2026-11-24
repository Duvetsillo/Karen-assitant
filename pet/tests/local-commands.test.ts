import { describe, expect, it } from 'vitest';
import { canSendMessage, isCoreCommand } from '../shared/local-commands';

describe('local Core commands remain usable without a provider', () => {
  it('allows reads in both composers offline', () => {
    for (const command of ['/tareas listar', '/TAREAS estado abc', '/core estado', '/historial', '/memoria listar Prueba']) {
      expect(isCoreCommand(command)).toBe(true);
      expect(canSendMessage(command, 'disconnected')).toBe(true);
    }
  });
  it('requires connection for explicit context transfers and conversation', () => {
    for (const command of ['Hola', '/memoria enviar', '/historial enviar abc']) {
      expect(canSendMessage(command, 'disconnected')).toBe(false);
      expect(canSendMessage(command, 'connected')).toBe(true);
    }
    expect(canSendMessage('  ', 'connected')).toBe(false);
    expect(canSendMessage('/tareasXYZ', 'disconnected')).toBe(false);
  });
});
