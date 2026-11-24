import type { Settings } from '../shared/types.js';
import type { CoreStore } from './core-store.js';

/** Apply a shared style without writing the observed value back to Core. */
export function applyCoreVoiceStyle(
  core: Pick<CoreStore, 'getVoiceStyle'>,
  current: Settings,
  save: (patch: Partial<Settings>) => Settings,
  notify: (settings: Settings) => void,
): boolean {
  const style = core.getVoiceStyle();
  if (!style || style === current.voiceStyle) return false;
  notify(save({ voiceStyle: style }));
  return true;
}

/** Apply a shared mode without echoing an observed change back to Core. */
export function applyCoreMode(
  core: Pick<CoreStore, 'getMode'>,
  current: Settings,
  save: (patch: Partial<Settings>) => Settings,
  notify: (settings: Settings) => void,
): boolean {
  const mode = core.getMode();
  if (!mode || mode === current.mode) return false;
  notify(save({ mode }));
  return true;
}
