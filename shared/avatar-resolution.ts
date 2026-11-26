import type { IntroId } from './startup-intros.js';

export interface AvatarResolution { body: number; face: number; details: number }
export const DESKTOP_RESOLUTION: AvatarResolution = { body: 1, face: 1, details: 1 };
export const INTRO_TEXTURE_BUDGET = 48 * 1024 * 1024;
/** RGBA source pixels, excluding driver copies and mip levels. A budget, not a RAM measurement. */
export function avatarSourceBytes(r: AvatarResolution) {
  const body = 512 * 512 * r.body ** 2;
  const face = (100 * 120 + 80 * 96) * r.face ** 2;
  const details = (150 * 260 + 140 * 130 + 90 * 95 + 90 * 140) * r.details ** 2;
  return (body + face + details + 128 * 128 + 256 * 96 + 32 * 32) * 4;
}
/** Rasterize the existing paths at their actual display size, once per intro. */
export function introAvatarResolution(width: number, height: number, dpr: number, id: IntroId): AvatarResolution {
  const density = Math.max(1, Math.min(2, Number.isFinite(dpr) ? dpr : 1));
  const scale = Math.max(.5, Math.min(width / 480, height / 420) * .9);
  const resolution = {
    body: Math.min(6, Math.max(1, Math.ceil(scale * density * 1.3))),
    face: Math.min(16, Math.max(1, Math.ceil(scale * .7 * density * (id === 'awakening' ? 4.8 : 1.25)))),
    details: Math.min(4, Math.max(1, Math.ceil(scale * density))),
  };
  while (avatarSourceBytes(resolution) > INTRO_TEXTURE_BUDGET && resolution.body > 1) resolution.body--;
  while (avatarSourceBytes(resolution) > INTRO_TEXTURE_BUDGET && resolution.details > 1) resolution.details--;
  while (avatarSourceBytes(resolution) > INTRO_TEXTURE_BUDGET && resolution.face > 1) resolution.face--;
  return resolution;
}
