import { describe, expect, it } from 'vitest';
import { wakeCommand } from '../shared/wake-word';
import { defaults, validateSettings } from '../shared/settings';

describe('activación explícita Karen/Caren', () => {
  it.each([
    ['Karen, dime la hora.', 'dime la hora.'], ['Caren abre ajustes', 'abre ajustes'],
    ['¡KAREN!', ''], ['Hola, Caren. ¿Seguimos?', 'Seguimos?'], ['oye Karen', ''],
    ['karenina abre ajustes', null], ['El video de Karen está listo', null], ['', null],
  ])('interpreta %s con límites de palabra', (text, command) => expect(wakeCommand(text)).toBe(command));
  it('la escucha exige configuración explícita y valida el estilo', () => {
    expect(defaults.wakeWordEnabled).toBe(false);
    expect(validateSettings({wakeWordEnabled:true,voiceStyle:'serious'})).toMatchObject({wakeWordEnabled:true,voiceStyle:'serious'});
    expect(() => validateSettings({voiceStyle:'child' as never})).toThrow('Estilo');
  });
});
