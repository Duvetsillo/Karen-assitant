/** One phrase ahead: synthesis overlaps playback without an unbounded audio queue. */
export async function* speechAudio<T>(
  phrases: readonly string[],
  synthesize: (text: string, signal: AbortSignal) => Promise<T>,
  signal: AbortSignal,
): AsyncGenerator<T> {
  if (!phrases.length || signal.aborted) return;
  const controller = new AbortController();
  const linked = AbortSignal.any([signal, controller.signal]);
  const prepare = (text: string) => Promise.resolve().then(() => {
    linked.throwIfAborted();
    return synthesize(text, linked);
  }).then(value => ({ ok: true as const, value }), error => ({ ok: false as const, error }));
  let next = prepare(phrases[0]);
  try {
    for (let index = 0; index < phrases.length; index++) {
      const result = await next;
      if (linked.aborted) return;
      if (!result.ok) throw result.error;
      if (index + 1 < phrases.length) next = prepare(phrases[index + 1]);
      yield result.value;
    }
  } finally {
    controller.abort();
  }
}
