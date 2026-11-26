import { describe, expect, it } from 'vitest';
import { DESKTOP_RESOLUTION, INTRO_TEXTURE_BUDGET, avatarSourceBytes, introAvatarResolution } from '../shared/avatar-resolution';
import { IntroTimeline } from '../shared/startup-intros';
describe('full-screen avatar rendering', () => {
  it('budgets original procedural textures at display density without scaling desktop assets', () => {
    expect(DESKTOP_RESOLUTION).toEqual({ body: 1, face: 1, details: 1 });
    for (const [width, height] of [[1280,720], [1920,1080], [2560,1440], [3840,2160]]) for (const dpr of [1,1.25,1.5,2]) {
      const r = introAvatarResolution(width, height, dpr, 'awakening');
      expect(avatarSourceBytes(r)).toBeLessThanOrEqual(INTRO_TEXTURE_BUDGET);
      expect(r.body * 512).toBeLessThanOrEqual(4096);
      expect(r.face).toBeGreaterThanOrEqual(r.body);
    }
    expect(introAvatarResolution(1920,1080,1,'awakening').face).toBeGreaterThanOrEqual(8);
    expect(introAvatarResolution(1920,1080,2,'awakening').face).toBeGreaterThan(introAvatarResolution(1920,1080,1,'awakening').face);
  });
  it('reveals just the giant eyes first and lands in a neutral desktop pose', () => {
    const timeline = new IntroTimeline('awakening',false,3), target = { x:100,y:200,width:380,height:440 };
    expect(timeline.sample(.9,1920,1080,target).bodyAlpha).toBe(0);
    expect(timeline.sample(3,1920,1080,target).bodyAlpha).toBe(1);
    const landed = timeline.sample(timeline.duration,1920,1080,target);
    expect(landed).toMatchObject({eye:1,wink:1,breathe:1,mouth:0,tilt:0,done:true});
    expect(Math.abs(landed.gazeX) + Math.abs(landed.gazeY)).toBe(0);
  });
});
