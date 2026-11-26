import { Graphics, type Application, type Container, type Sprite } from 'pixi.js';
import { clamp01, IntroTimeline, type IntroPayload } from '../../shared/startup-intros';
import { AudioCueManager } from './AudioCueManager';

/** Adapter to the existing layered avatar. No new character art or style definitions. */
export interface AvatarAdapter {
  scene: Container; root: Container; eyes: Container;
  eyeL: Container; eyeR: Container; irisL: Sprite; irisR: Sprite;
  finL: Sprite; finR: Sprite; facial: Graphics; shadow: Sprite; halo: Sprite;
  bodyParts: Sprite[];
}
export class IntroRenderer {
  readonly timeline: IntroTimeline;
  readonly audio: AudioCueManager;
  private back = new Graphics();
  private front = new Graphics();
  private start?: number;
  private requested = false;
  private ended = false;
  private landingRequested = false;
  private landingPrepared = false;
  // Geometry created once, bounded independently of screen resolution.
  private particles = Array.from({ length: 64 }, (_, i) => ({ angle: i * 2.399963, radius: .5 + (i % 11) / 20, size: 1 + i % 3 }));
  private cracks = Array.from({ length: 12 }, (_, i) => ({ angle: i * Math.PI / 6, length: .6 + (i % 4) / 10 }));
  constructor(readonly payload: IntroPayload, reduced: boolean, private ready: () => Promise<boolean>, private finish: () => void,
    private prepareLanding: () => Promise<boolean> = async () => true) {
    this.timeline = new IntroTimeline(payload.id, reduced, payload.greeting?.duration);
    this.audio = new AudioCueManager(payload.settings.introVolume, payload.greeting, payload.settings.outputDevice);
  }
  attach(app: Application) {
    app.stage.addChildAt(this.back, 0); app.stage.addChild(this.front);
    app.ticker.maxFPS = this.payload.settings.introFPS;
  }
  update(app: Application, avatar: AvatarAdapter) {
    if (this.ended) return;
    if (!this.requested) {
      this.requested = true;
      void this.ready().then(allowed => {
        if (this.ended) return;
        if (allowed) this.start = performance.now(); else this.complete();
      }).catch(() => this.complete());
    }
    const elapsed = this.start === undefined ? 0 : (performance.now() - this.start) / 1000;
    if (this.start !== undefined && elapsed >= this.timeline.greetingAt) this.audio.greetingCue();
    // Let the prerecorded voice clock finish the greeting before the departure.
    // Suspended or delayed output cannot silently lose the one-shot cue.
    const voiceClock = this.audio.greetingElapsed;
    const t = this.audio.hasGreeting && elapsed >= this.timeline.greetingAt
      ? Math.min(elapsed, this.timeline.greetingAt + (voiceClock ?? 0)) : elapsed;
    const { width: w, height: h } = app.screen;
    const p = this.timeline.sample(Math.min(t, this.timeline.duration), w, h, this.payload.target);
    const { scene, root, eyes, eyeL, eyeR, irisL, irisR, finL, finR, facial, shadow, halo } = avatar;
    scene.position.set(p.x, p.y); scene.scale.set(p.scale); scene.alpha = p.alpha;
    root.position.set(0, 0); root.rotation = p.tilt;
    root.scale.set(p.breathe, 2 - p.breathe); root.alpha = this.payload.settings.opacity * (this.payload.settings.nightMode ? .7 : 1);
    for (const part of avatar.bodyParts) part.alpha = p.bodyAlpha;
    eyes.position.set(0, -7); eyeL.scale.y = .7 * p.eye; eyeR.scale.y = .7 * p.eye * p.wink;
    irisL.position.set(3 + p.gazeX, 6 + p.gazeY); irisR.position.set(3 - p.gazeX, 6 + p.gazeY);
    finL.rotation = -.35 + p.ear; finR.rotation = .35 - p.ear;
    shadow.alpha = (.3 + p.exit * .35) * p.bodyAlpha; shadow.scale.set(.85);
    const homeHalo = .22 * this.payload.settings.brightness * (this.payload.settings.nightMode ? .6 : 1);
    halo.alpha = (.18 + (homeHalo - .18) * p.exit) * p.bodyAlpha;
    if (this.start !== undefined && t >= .4 && this.payload.settings.introSounds && !this.timeline.reduced) this.audio.soundCue();
    const mouth = Math.max(p.mouth, this.audio.mouth());
    facial.alpha = p.bodyAlpha;
    facial.clear();
    if (mouth > .04) facial.ellipse(0, 42, 6 + mouth * 8, 3 + mouth * 17).fill(0x14223f);
    else facial.moveTo(-12, 36).quadraticCurveTo(0, 53 - 7 * p.exit, 12, 36).stroke({ color: 0xcdfaff, width: 3, cap: 'round' });
    if (p.exit > 0) {
      facial.moveTo(-61,-45).quadraticCurveTo(-46,-51,-30,-45).stroke({ color:0xe4fcff,alpha:.8*p.exit,width:2.5,cap:'round' });
      facial.moveTo(30,-45).quadraticCurveTo(46,-51,61,-45).stroke({ color:0xe4fcff,alpha:.8*p.exit,width:2.5,cap:'round' });
    }
    this.back.clear(); this.front.clear();
    if (p.dark > 0) this.back.rect(0, 0, w, h).fill({ color: 0x030811, alpha: p.dark });
    if (!this.timeline.reduced) this.effects(t, w, h, p.effect, p.exit);
    if (t >= this.timeline.leaveAt && !this.landingRequested) {
      this.landingRequested = true;
      void this.prepareLanding().catch(() => false).then(() => { this.landingPrepared = true; });
    }
    if (p.done && this.landingPrepared) this.complete();
  }
  private effects(t: number, w: number, h: number, progress: number, exit: number) {
    const color = Number.parseInt(this.payload.settings.accent.slice(1), 16);
    const x = w / 2, y = h / 2, unit = Math.min(w, h);
    switch (this.payload.id) {
      case 'breakthrough': {
        // Transparent displacement bands simulate a digital tear without reading the desktop.
        const power = Math.max(0, 1 - t / 1.8);
        for (let i = 0; i < 14 && power > 0; i++) {
          const offset = Math.sin(t * 29 + i * 8) * w * .06 * power;
          this.front.rect(offset, h * i / 14, w, (2 + i % 4) * power)
            .fill({ color, alpha: power * .27 });
        }
        if (t < 2) this.front.circle(x, y, unit * (.1 + progress * .55)).stroke({ color, width: 2, alpha: power });
        break;
      }
      case 'glass': {
        const split = Math.sin(Math.PI * clamp01((t - .5) / (this.timeline.leaveAt - .5)));
        const alpha = (1 - exit) * Math.min(1, t * 4);
        for (const crack of this.cracks) {
          const a = crack.angle, b = a + Math.PI / 6;
          const dx = Math.cos(a) * split * unit * .35, dy = Math.sin(a) * split * unit * .35;
          const reach = unit * crack.length;
          this.front.moveTo(x + dx, y + dy)
            .lineTo(x + Math.cos(a) * reach + dx, y + Math.sin(a) * reach + dy)
            .lineTo(x + Math.cos(b) * reach + dx, y + Math.sin(b) * reach + dy).closePath()
            .fill({ color: 0xc0e7f2, alpha: alpha * .06 })
            .stroke({ color: 0xd3f4ff, width: 1.2, alpha: alpha * .7 });
        }
        break;
      }
      case 'materialization':
        for (const particle of this.particles) {
          const r = (1 - progress) * unit * particle.radius;
          this.front.circle(x + Math.cos(particle.angle + t * .5) * r, y + Math.sin(particle.angle + t * .5) * r, particle.size)
            .fill({ color, alpha: (1 - progress) * (1 - exit) });
        }
        if (t < 2.1) this.front.rect(x - unit * .25, h * progress, unit * .5, 2).fill({ color, alpha: 1 - progress });
        break;
      case 'sleepy':
        if (t < 1.8) for (let i = 0; i < 3; i++) this.front.circle(x + unit * (.14 + i * .025), y - unit * (.15 + i * .05) - t * 8, 2 + i * 2)
          .stroke({ color, width: 1, alpha: (1 - t / 1.8) * .45 });
        break;
      case 'surprise':
        if (t > 2.35 && t < 3.1) {
          const p = (t - 2.35) / .75;
          this.back.ellipse(x, h * .8, unit * .3 * p, unit * .05 * p).stroke({ color, width: 2, alpha: 1 - p });
        }
        break;
      case 'awakening': break; // The giant layered eyes are the effect.
    }
  }
  private complete() {
    if (this.ended) return;
    this.ended = true; this.audio.dispose(); this.finish();
  }
  dispose() {
    this.ended = true; this.audio.dispose();
    this.back.destroy(); this.front.destroy(); this.particles = []; this.cracks = [];
  }
}
