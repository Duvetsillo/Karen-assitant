export async function pcm16(blob: Blob): Promise<ArrayBuffer> {
  const decoder = new AudioContext();
  let decoded: AudioBuffer;
  try { decoded = await decoder.decodeAudioData(await blob.arrayBuffer()); }
  finally { await decoder.close(); }
  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * 16000), 16000);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const rendered = await offline.startRendering();
  const floats = rendered.getChannelData(0);
  const pcm = new Int16Array(floats.length);
  for (let i = 0; i < floats.length; i++) pcm[i] = Math.max(-1, Math.min(1, floats[i])) * 32767;
  return pcm.buffer;
}
