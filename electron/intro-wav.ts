/** Offline PCM envelope extraction. No codec, phoneme model or runtime inference. */
export function analyzeGreetingWav(bytes: Uint8Array): { duration: number; envelope: number[]; envelopeStep: number } {
  const data = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const tag = (offset: number) => String.fromCharCode(...bytes.subarray(offset, offset + 4));
  if (bytes.length < 44 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw new Error('Se necesita audio WAV PCM.');
  let channels = 0, rate = 0, bits = 0, format = 0, start = 0, size = 0;
  for (let offset = 12; offset + 8 <= bytes.length;) {
    const length = data.getUint32(offset + 4, true), body = offset + 8;
    if (body + length > bytes.length) throw new Error('WAV truncado.');
    if (tag(offset) === 'fmt ' && length >= 16) {
      format = data.getUint16(body, true); channels = data.getUint16(body + 2, true);
      rate = data.getUint32(body + 4, true); bits = data.getUint16(body + 14, true);
    }
    if (tag(offset) === 'data') { start = body; size = length; }
    offset = body + length + (length % 2);
  }
  if (![1, 3].includes(format) || ![16, 32].includes(bits) || (format === 3 && bits !== 32) ||
    channels < 1 || channels > 2 || rate < 8000 || rate > 192000 || !start || !size) throw new Error('Formato WAV no compatible.');
  const frameSize = channels * bits / 8, frames = Math.floor(size / frameSize), duration = frames / rate;
  if (duration <= 0 || duration > 15) throw new Error('El saludo debe durar entre 0 y 15 segundos.');
  const envelopeStep = .02, envelope: number[] = [];
  for (let window = 0; window < Math.ceil(duration / envelopeStep); window++) {
    let energy = 0, count = 0;
    for (let i = Math.floor(window * envelopeStep * rate); i < Math.min(frames, Math.floor((window + 1) * envelopeStep * rate)); i++) {
      for (let ch = 0; ch < channels; ch++) {
        const offset = start + i * frameSize + ch * bits / 8;
        const sample = format === 3 ? data.getFloat32(offset, true) : bits === 16 ? data.getInt16(offset, true) / 32768 : data.getInt32(offset, true) / 2147483648;
        if (!Number.isFinite(sample)) throw new Error('Muestra WAV inválida.');
        energy += sample * sample; count++;
      }
    }
    envelope.push(Math.sqrt(energy / Math.max(1, count)));
  }
  const peak = Math.max(.01, ...envelope);
  return { duration, envelopeStep, envelope: envelope.map(value => Math.round(Math.min(1, value / peak) * 1000) / 1000) };
}
