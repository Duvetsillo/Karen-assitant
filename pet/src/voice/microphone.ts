import { bridge } from '../native';
import { inputError } from './input-error';

/** Claim before opening hardware; release after every track has actually stopped. */
export async function openMicrophone(constraints: MediaStreamConstraints): Promise<MediaStream> {
  let token: string | undefined;
  try { token = await bridge.claimMicrophone?.(); }
  catch (error) { throw inputError(error); }
  let released = false;
  const release = () => {
    if (released) return;
    released = true;
    if (token) void bridge.releaseMicrophone?.(token).catch(() => {});
  };
  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    const tracks = stream.getTracks();
    const remaining = new Set(tracks);
    if (!tracks.length) release();
    for (const track of tracks) {
      const ended = () => { remaining.delete(track); if (!remaining.size) release(); };
      track.addEventListener?.('ended', ended, { once: true });
      const stop = track.stop.bind(track);
      track.stop = () => { try { stop(); } finally { ended(); } };
    }
    return stream;
  } catch (error) {
    release();
    const selectedDevice = typeof constraints.audio === 'object' && Boolean(constraints.audio.deviceId);
    throw inputError(error, selectedDevice);
  }
}
