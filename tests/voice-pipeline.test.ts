import { describe, expect, it, vi } from 'vitest';
import { speechAudio } from '../src/voice/pipeline';
import { speechPhrases } from '../src/voice/replies';

describe('voz continua con división solo para textos extensos', () => {
  it('mantiene unida una respuesta normal', () => {
    const text = 'Estoy aquí. Ahora voy a explicarte con calma todos los detalles de tu pregunta sin cambiar de voz.';
    const chunks = speechPhrases(text);
    expect(chunks).toHaveLength(1);
    expect(chunks.join(' ')).toBe(text);
  });
  it('prepara la siguiente durante la reproducción y limita la anticipación', async () => {
    const synthesize = vi.fn(async (text: string) => text);
    const stream = speechAudio(['uno','dos','tres'], synthesize, new AbortController().signal);
    expect((await stream.next()).value).toBe('uno');
    await Promise.resolve();
    expect(synthesize.mock.calls.map(call => call[0])).toEqual(['uno','dos']);
    expect((await stream.next()).value).toBe('dos');
    await Promise.resolve();
    expect(synthesize.mock.calls.map(call => call[0])).toEqual(['uno','dos','tres']);
    expect((await stream.next()).value).toBe('tres');
    expect((await stream.next()).done).toBe(true);
  });
  it('cancelar aborta la frase anticipada y no genera otras', async () => {
    const controller = new AbortController();
    const signals: AbortSignal[] = [];
    const synthesize = vi.fn(async (text: string, signal: AbortSignal) => {signals.push(signal);return text;});
    const stream = speechAudio(['uno','dos','tres'], synthesize, controller.signal);
    await stream.next();
    await Promise.resolve();
    controller.abort();
    expect((await stream.next()).done).toBe(true);
    expect(signals.every(signal => signal.aborted)).toBe(true);
    expect(synthesize).toHaveBeenCalledTimes(2);
  });
  it('conserva el orden y propaga el fallo de la frase anticipada', async () => {
    const synthesize = vi.fn().mockResolvedValueOnce('uno').mockRejectedValueOnce(new Error('Motor no disponible'));
    const stream = speechAudio(['uno','dos'], synthesize, new AbortController().signal);
    expect((await stream.next()).value).toBe('uno');
    await expect(stream.next()).rejects.toThrow('Motor no disponible');
  });
});
