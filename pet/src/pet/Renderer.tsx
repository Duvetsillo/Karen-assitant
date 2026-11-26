import { useEffect, useRef } from "react";
import { Application, Container, Graphics, Sprite } from "pixi.js";
import "pixi.js/unsafe-eval";
import { createPetTextures } from "./textures";
import { petStyles } from '../../shared/pet-styles';
import { gazeTarget } from "./gaze";
import { SpeechMotion } from "./speech-motion";
import { machine, signals, useStore } from "../state/store";
import { effectiveSettings } from '../../shared/settings';
import { IdleActivities } from './idle-activities';
import { PresenceMotion, PresenceSpring } from './presence-motion';
import type { IntroRenderer } from '../intros/IntroRenderer';
import { chooseMusicSession } from '../../shared/music';
import { DESKTOP_RESOLUTION, introAvatarResolution, avatarSourceBytes } from '../../shared/avatar-resolution';
import { bridge } from '../native';
import { DepartureTimeline } from '../../shared/departure';

function damp(value: number, target: number, dt: number, rate = 9) {
  return value + (target - value) * (1 - Math.exp(-rate * dt));
}
function dampTint(current: number, target: number, dt: number, rate: number) {
  const channel = (shift: number) => Math.round(damp((current >> shift) & 255, (target >> shift) & 255, dt, rate));
  return (channel(16) << 16) | (channel(8) << 8) | channel(0);
}
export function PetRenderer({
  className = "",
  preview = false,
  intro,
}: {
  className?: string;
  preview?: boolean;
  intro?: IntroRenderer;
}) {
  const host = useRef<HTMLDivElement>(null);
  const ready = useStore(s=>s.ready);
  const petStyle = useStore((s) => s.settings.petStyle);
  const showArms = useStore((s) => s.settings.showArms);
  const showLegs = useStore((s) => s.settings.showLegs);
  useEffect(() => {
    if(!ready)return;
    let disposed = false;
    let initialized = false;
    let app: Application | undefined;
    let observer: ResizeObserver | undefined;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    const initialize = async () => {
      app = new Application();
      await app.init({
        width: 380,
        height: 440,
        backgroundAlpha: 0,
        antialias: true,
        resolution: Math.min(devicePixelRatio, 2),
        autoDensity: true,
        powerPreference: "low-power",
        preference: "webgl",
      });
      initialized = true;
      if (disposed) {
        cleanup();
        return;
      }
      host.current!.appendChild(app.canvas);
      app.canvas.setAttribute("aria-hidden", "true");
      const textureResolution = intro ? introAvatarResolution(innerWidth, innerHeight, Math.min(devicePixelRatio, 2), intro.payload.id) : DESKTOP_RESOLUTION;
      app.canvas.dataset.textureResolution = JSON.stringify(textureResolution);
      app.canvas.dataset.textureSourceBytes = String(avatarSourceBytes(textureResolution));
      let tex = createPetTextures(useStore.getState().settings.accent, useStore.getState().settings.petStyle, textureResolution);
      const scene = new Container();
      app.stage.addChild(scene);
      const make = (
        texture: typeof tex.body,
        parent: Container,
        anchor = 0.5,
      ) => {
        const s = new Sprite(texture);
        s.anchor.set(anchor);
        parent.addChild(s);
        return s;
      };
      const shadow = make(tex.shadow, scene);
      shadow.y = 142;
      shadow.scale.set(0.9);
      const halo = make(tex.glow, scene);
      halo.scale.set(2.7);
      halo.y = 3;
      halo.alpha = 0.35;
      const root = new Container();
      scene.addChild(root);
      const finL = make(tex.fin, root);
      finL.anchor.set(0.51, 0.9);
      finL.position.set(-72, -62);
      finL.scale.set(0.74, 0.74);
      finL.rotation = -0.35;
      const finR = make(tex.fin, root);
      finR.anchor.set(0.51, 0.9);
      finR.position.set(72, -62);
      finR.scale.set(-0.74, 0.74);
      finR.rotation = 0.35;
      const legL = make(tex.leg, root);
      legL.position.set(-47, 139);
      legL.scale.set(0.64);
      const legR = make(tex.leg, root);
      legR.position.set(47, 139);
      legR.scale.set(-0.64, 0.64);
      const armL = new Container();
      root.addChild(armL);
      armL.position.set(-126, 45);
      const armLSprite = make(tex.arm, armL);
      armLSprite.scale.set(0.65);
      const handL = make(tex.hand, armL);
      handL.position.set(-43, 7);
      handL.scale.set(0.42);
      armL.rotation = -0.25;
      const armR = new Container();
      root.addChild(armR);
      armR.position.set(126, 45);
      const armRSprite = make(tex.arm, armR);
      armRSprite.scale.set(-0.65, 0.65);
      const handR = make(tex.hand, armR);
      handR.position.set(43, 7);
      handR.scale.set(-0.42, 0.42);
      armR.rotation = 0.25;
      const body = make(tex.body, root);
      body.scale.set(0.94);
      const heart = make(tex.heart, root);
      heart.position.set(0, 83);
      heart.scale.set(.72);
      const maskSprites = [body, finL, finR, armLSprite, armRSprite, handL, handR, legL, legR];
      const readMasks = () => maskSprites.map((sprite) => {
          const canvas = sprite.texture.source.resource as HTMLCanvasElement;
          return {
            sprite,
            width: canvas.width,
            height: canvas.height,
            data: canvas
              .getContext("2d")!
              .getImageData(0, 0, canvas.width, canvas.height).data,
          };
        });
      const interactive = !preview && !intro;
      let masks = interactive ? readMasks() : [];
      if (interactive) {
        signals.hitTest = (x, y) =>
          masks.some((m) => {
            if (!m.sprite.visible || !m.sprite.parent?.visible) return false;
            const p = m.sprite.toLocal({ x, y });
            const px = Math.floor(p.x + m.sprite.anchor.x * m.width),
              py = Math.floor(p.y + m.sprite.anchor.y * m.height);
            return (
              px >= 0 &&
              py >= 0 &&
              px < m.width &&
              py < m.height &&
              m.data[(py * m.width + px) * 4 + 3] > 90
            );
          });
      }
      const eyes = new Container();
      root.addChild(eyes);
      eyes.y = -7;
      const eyeL = new Container();
      eyes.addChild(eyeL);
      eyeL.x = -44;
      eyeL.scale.set(0.7, 0.7);
      make(tex.eye, eyeL);
      const irisL = make(tex.iris, eyeL);
      const eyeR = new Container();
      eyes.addChild(eyeR);
      eyeR.x = 44;
      eyeR.scale.set(-0.7, 0.7);
      make(tex.eye, eyeR);
      const irisR = make(tex.iris, eyeR);
      const facial = new Graphics();
      root.addChild(facial);
      const pastime = new Graphics();
      root.addChild(pastime);
      const sparkles = Array.from({ length: 22 }, (_, i) => {
        const s = make(tex.particle, scene);
        s.scale.set(0.14 + Math.random() * 0.18);
        return {
          sprite: s,
          angle: i * 2.3999,
          radius: 130 + Math.random() * 65,
          speed: 0.12 + Math.random() * 0.25,
          phase: Math.random() * 6.28,
        };
      });
      // One WebGL context for the lifetime of this surface. Replacing an app
      // during saved-settings hydration can invalidate Pixi's shared batch pool.
      const offStyle=useStore.subscribe((next,previous)=>{
        if(next.settings.accent===previous.settings.accent && next.settings.petStyle===previous.settings.petStyle)return;
        const old=tex;
        tex=createPetTextures(next.settings.accent,next.settings.petStyle,textureResolution);
        body.texture=tex.body;heart.texture=tex.heart;shadow.texture=tex.shadow;halo.texture=tex.glow;
        finL.texture=finR.texture=tex.fin;legL.texture=legR.texture=tex.leg;
        armLSprite.texture=armRSprite.texture=tex.arm;handL.texture=handR.texture=tex.hand;
        eyeL.children[0] && ((eyeL.children[0] as Sprite).texture=tex.eye);
        eyeR.children[0] && ((eyeR.children[0] as Sprite).texture=tex.eye);
        irisL.texture=irisR.texture=tex.iris;
        sparkles.forEach(p=>p.sprite.texture=tex.particle);
        masks=interactive?readMasks():[];
        Object.values(old).forEach(t=>t.destroy(true));
      });
      const resize = () => {
        if (!app || !host.current) return;
        const { width, height } = host.current.getBoundingClientRect();
        app.renderer.resize(width, height);
        scene.position.set(width / 2, height * 0.54);
        scene.scale.set(Math.min(width / 380, height / 440) * (preview ? 0.72 : 0.8));
        // Resizing clears WebGL even while Windows has paused the hidden ticker.
        // Draw this frame immediately; no background animation loop is needed.
        app.render();
      };
      observer = new ResizeObserver(resize);
      observer.observe(host.current!);
      resize();
      let t = 0,
        blink = 0,
        nextBlink = 2 + Math.random() * 4,
        eyeOpen = 1,
        rightOpen = 1,
        tilt = 0,
        mouth = 0,
        float = 0,
        eyeX = 0,
        eyeY = 0,
        brow = 0,
        frames = 0,
        frameTime = 0,
        quality = 1,
        bodyTint = 0xffffff,
        haloTint = 0xffffff;
      const speechMotion = new SpeechMotion();
      const presenceMotion = new PresenceMotion();
      const headSpring = new PresenceSpring();
      const idleActivities = new IdleActivities();
      const avatar = { scene, root, eyes, eyeL, eyeR, irisL, irisR, finL, finR, facial, shadow, halo, bodyParts: [...maskSprites,heart] };
      intro?.attach(app);
      let lastIdleKind = '';
      let landingSent = '';
      let departureToken = '', departureStart = 0, departureDone = false;
      const departureTimeline = new DepartureTimeline(reduced.matches || !useStore.getState().settings.animations || useStore.getState().settings.introReducedMotion);
      const visibility = () => {
        presenceMotion.reset();
        headSpring.reset();
        idleActivities.suspend(Date.now(), useStore.getState().settings.idleAfter);
        pastime.clear();
        if (host.current) host.current.dataset.idleActivity = 'none';
        lastIdleKind = 'none';
        if (document.hidden || !useStore.getState().surfaceVisible) app?.stop();
        else { app?.render();app?.start(); }
      };
      document.addEventListener("visibilitychange", visibility);
      const offVisibility = useStore.subscribe((next,previous) => {
        if (next.surfaceVisible !== previous.surfaceVisible) visibility();
      });
      visibility();
      app.ticker.add((ticker) => {
        const dt = Math.min(ticker.deltaMS / 1000, 0.06);
        t += dt;
        const { settings, state, expression: spokenExpression, capture, coreActivity, wakeStatus, messages, surfaceVisible, music, introLanding, departure } = useStore.getState();
        const song = music && chooseMusicSession(music.sessions, music.activeId);
        const musicMotion = !intro && !introLanding && settings.musicAnimations && song?.status === 'playing' && state === 'IDLE' && capture.phase === 'idle' &&
          (settings.mode === 'normal' || (settings.mode === 'gaming' && settings.musicGamingReactions)) && !reduced.matches;
        const s = effectiveSettings(settings);
        const sleeping = state === "SLEEPING";
        app!.ticker.maxFPS = s.lowPower || sleeping || !s.animations || reduced.matches ? 12 : state === 'IDLE' ? 24 : preview ? 30 : 60;
        frames++;
        frameTime += ticker.deltaMS / 1000;
        if (frameTime > 3) {
          signals.fps = Math.round(frames / frameTime);
          host.current!.dataset.renderFps = String(signals.fps);
          if (signals.fps < 24 && !s.lowPower && !sleeping) quality = 0.5;
          frames = 0;
          frameTime = 0;
        }
        const motion = s.animations && !reduced.matches;
        armL.visible = armR.visible = s.showArms;
        legL.visible = legR.visible = s.showLegs;
        if (host.current!.dataset.arms !== String(s.showArms)) host.current!.dataset.arms = String(s.showArms);
        if (host.current!.dataset.legs !== String(s.showLegs)) host.current!.dataset.legs = String(s.showLegs);
        const idle = idleActivities.update({ settings: s, state, lastActivity: machine.snapshot.lastActivity,
          blocked: Boolean(musicMotion) || document.hidden || !surfaceVisible || capture.phase !== 'idle' || signals.pointingSide !== 0 ||
            wakeStatus === 'processing' || wakeStatus === 'recovering' || Boolean(messages.at(-1)?.pending) ||
            coreActivity.some(client => client.state !== 'IDLE'),
          reducedMotion: reduced.matches });
        if (lastIdleKind !== idle.kind) {
          host.current!.dataset.idleActivity = lastIdleKind = idle.kind;
        }
        const idleEnvelope = Math.sin(Math.PI * idle.progress) ** 2;
        const play = idle.kind === 'play' ? idleEnvelope : 0;
        const stretch = idle.kind === 'stretch' ? idleEnvelope : 0;
        const stargaze = idle.kind === 'stargaze' ? idleEnvelope : 0;
        pastime.clear();
        if (play > 0) {
          const ballX = Math.sin(idle.progress * Math.PI * 6) * 112;
          const ballY = 154 - Math.abs(Math.sin(idle.progress * Math.PI * 6)) * 37;
          pastime.circle(ballX, ballY, 9).fill({ color: 0xc9f4ff, alpha: idleEnvelope * .9 });
          pastime.circle(ballX - 2, ballY - 3, 2).fill({ color: 0xffffff, alpha: idleEnvelope });
        } else if (stargaze > 0) {
          for (let i = 0; i < 5; i++) {
            const x = -69 + i * 33, y = -180 - Math.sin(i * 1.8) * 15;
            pastime.moveTo(x - 4, y).lineTo(x + 4, y).moveTo(x, y - 4).lineTo(x, y + 4)
              .stroke({ color: 0xdcf9ff, width: 1.5, alpha: stargaze * (.55 + .35 * Math.sin(idle.progress * 5 + i)) });
          }
        }
        const speaking = state === "SPEAKING";
        const preparingVoice = capture.kind === "voice" && capture.phase === "preparing";
        const expression = speaking || preparingVoice ? spokenExpression : state;
        const laughing = expression === 'LAUGHING';
        const angry = expression === 'ANGRY';
        const sad = expression === 'SAD';
        const surprised = expression === 'SURPRISED';
        const proud = expression === 'PROUD';
        const curious = expression === 'CURIOUS';
        const expressiveAge = Math.max(0, (Date.now() - machine.snapshot.since) / 1000);
        const entrance = motion ? Math.max(0, 1 - expressiveAge / 0.7) : 0;
        const voiceEnergy = speaking ? Math.sqrt(Math.max(0, Math.min(1, signals.energy))) : 0;
        const speech = speechMotion.update(voiceEnergy, dt, speaking, motion);
        const presence = presenceMotion.update(expression, dt, motion, s.activity);
        if (!preview && !intro && !introLanding && !departure) {
          const docked = useStore.getState().petDock;
          const fit = Math.min(app!.screen.width / 380, app!.screen.height / 440);
          scene.scale.set(damp(scene.scale.x, fit * (docked ? .66 : .8), dt, 11));
          scene.y = damp(scene.y, app!.screen.height * (docked ? .43 : .54), dt, 11);
        }
        if (preview) scene.scale.set(Math.min(app!.screen.width / 380, app!.screen.height / 440) * 0.72 * Math.sqrt(s.scale));
        const activity = motion ? s.activity : 0;
        let targetTilt =
          state === "CONFUSED"
            ? -0.19
            : state === "THINKING"
              ? 0.1
              : state === "DRAGGING"
                ? 0.16
                : curious ? -0.13
                : angry ? -0.08
                : sad ? 0.13
                : surprised ? 0.06
                : 0;
        const gaze = gazeTarget(signals.cursor, s.cursorTracking && !sleeping);
        if (motion) targetTilt += Math.sin(t * 0.6) * 0.022 + gaze.x * 0.002 + Math.sin(t * 2.8) * speech.envelope * 0.045 + speech.side * speech.gesture * 0.055 + Math.sin(idle.progress * Math.PI * 6) * play * .06 - stargaze * .12;
        if (!motion) headSpring.reset();
        tilt = headSpring.update(motion ? targetTilt : 0, dt);
        root.rotation = tilt;
        root.x = damp(root.x, motion ? Math.sin(t * 2.8) * speech.envelope * 6 + speech.side * speech.gesture * 4 : 0, dt, 8);
        const bob = presence.bob;
        const happy = presence.lift;
        const laughBounce = laughing && motion ? Math.sin(t * 6) * -3 * speech.envelope : 0;
        const proudLift = proud && motion ? -7 : 0;
        const surpriseLift = surprised && motion ? -12 * entrance : 0;
        float = damp(
          float,
          bob +
            happy +
            laughBounce + proudLift + surpriseLift - speech.envelope * 8 - speech.gesture * 5 +
            (motion && state === "LISTENING" ? -5 : 0) +
            (motion && state === "DRAGGING" ? -12 : 0),
          dt,
          9,
        );
        root.y = float;
        const breathe =
          1 + presence.breath;
        const voicePulse = motion ? speech.envelope * 0.028 : 0;
        root.scale.set(breathe - voicePulse - stretch * .035, 2 - breathe + voicePulse + stretch * .055);
        root.alpha = damp(
          root.alpha,
          (sleeping ? 0.57 : 1) * (s.nightMode ? 0.7 : 1) * s.opacity,
          dt,
          3,
        );
        bodyTint = dampTint(bodyTint, state === "ERROR" ? 0xffceb3 : angry ? 0xffd5ce : sad ? 0xdce7ff : 0xffffff, dt, reduced.matches ? 28 : 10);
        body.tint = bodyTint;
        heart.scale.set(.72 * (1 + (motion ? presence.breath * 5 + speech.envelope * .09 : 0)));
        heart.alpha = sleeping ? .5 : .8 + (motion ? Math.abs(presence.breath) * 10 : 0);
        heart.tint = haloTint;
        halo.alpha =
          (sleeping ? 0.08 : 0.22 + speech.envelope * 0.13) * s.brightness * (s.nightMode ? 0.6 : 1);
        haloTint = dampTint(haloTint, state === "ERROR" ? 0xffb473 : angry ? 0xff8b7a : sad ? 0x96adff : proud ? 0xffd78c : 0xffffff, dt, reduced.matches ? 28 : 10);
        halo.tint = haloTint;
        shadow.scale.set(0.85 - float * 0.002, 0.85 - float * 0.002);
        shadow.alpha = 0.65 - float * 0.009;
        finL.rotation = damp(
          finL.rotation,
          -0.35 +
            (state === "LISTENING"
              ? 0.25
              : sleeping
                ? -0.25
                : state === "CONFUSED"
                  ? -0.3
                  : angry ? -0.42
                  : sad ? -0.35
                  : surprised ? 0.32
                  : 0) +
            Math.sin(t * 1.7) * 0.04 * activity - tilt * .25 - speech.envelope * 0.17 - speech.gesture * 0.1,
          dt,
          7,
        );
        finR.rotation = damp(
          finR.rotation,
          0.35 +
            (state === "LISTENING"
              ? -0.25
              : sleeping
                ? 0.25
                : state === "CONFUSED"
                  ? -0.13
                  : angry ? 0.42
                  : sad ? 0.35
                  : surprised ? -0.32
                  : 0) -
            Math.sin(t * 1.7 + 0.6) * 0.04 * activity - tilt * .25 + speech.envelope * 0.17 + speech.gesture * 0.1,
          dt,
          7,
        );
        armL.rotation = damp(armL.rotation,
          (signals.pointingSide === -1 ? 0.85 : -0.25) - stretch * .8 + play * Math.sin(idle.progress * Math.PI * 6) * .2 +
          Math.sin(t * 2 + 0.3) * 0.07 * activity +
          (motion ? laughing ? -0.42 : proud ? -0.36 : angry ? 0.2 : sad ? 0.12 : expression === "HAPPY" ? -0.25 : 0 : 0) -
          (signals.pointingSide === -1 ? 0 : -speech.envelope * 0.13 - (speech.side < 0 ? speech.gesture * 0.4 : speech.gesture * 0.08)), dt, motion ? 10 : 60);
        armR.rotation = damp(armR.rotation,
          (signals.pointingSide === 1 ? -0.85 : 0.25) - (signals.pointingSide === 1 ? 0 : presence.greeting * 1.05) + stretch * .8 + play * Math.sin(idle.progress * Math.PI * 6) * .2 -
          Math.sin(t * 2) * 0.07 * activity +
          (motion ? laughing ? 0.42 : proud ? 0.36 : angry ? -0.2 : sad ? -0.12 : expression === "HAPPY" ? 0.25 : 0 : 0) +
          (signals.pointingSide === 1 ? 0 : -speech.envelope * 0.13 + (speech.side > 0 ? speech.gesture * 0.4 : speech.gesture * 0.08)), dt, motion ? 10 : 60);
        legL.rotation = damp(legL.rotation, motion ? -0.04 + Math.sin(t * 1.65) * activity * 0.04 - speech.gesture * 0.04 : 0, dt, 8);
        legR.rotation = damp(legR.rotation, motion ? 0.04 - Math.sin(t * 1.65 + 0.5) * activity * 0.04 + speech.gesture * 0.04 : 0, dt, 8);
        if (t > nextBlink && !sleeping) {
          blink = 0.16;
          nextBlink = t + 2.5 + Math.random() * 5.5;
        }
        blink = Math.max(0, blink - dt);
        const targetOpen = sleeping
          ? 0.04
          : blink > 0
            ? Math.max(0.04, Math.abs(blink - 0.08) / 0.08)
            : laughing ? 0.37
              : angry ? 0.58
              : sad ? 0.65
              : surprised ? 1.28
              : curious ? 1.12
              : expression === "HAPPY"
              ? 0.68
              : state === "LISTENING"
                ? 1.13
                : state === "ERROR" ? 0.85 : 1;
        const asymmetry = !sleeping && blink === 0 && (state === "CONFUSED" || state === "THINKING" || curious);
        eyeOpen = damp(eyeOpen, targetOpen * (asymmetry ? 0.73 : 1), dt, blink > 0 ? 60 : 12);
        rightOpen = damp(rightOpen, targetOpen * (asymmetry ? 1.08 : 1), dt, blink > 0 ? 60 : 12);
        // Pursuit is damped, not restarted by each cursor event. Reduced motion
        // keeps a legible gaze but removes face translation and head sway.
        eyeX = damp(eyeX, play ? Math.sin(idle.progress * Math.PI * 6) * play * 12 : gaze.x + (s.cursorTracking ? 0 : presence.glance), dt, reduced.matches ? 18 : 12);
        eyeY = damp(eyeY, play ? play * 5 : stargaze ? -stargaze * 8 : gaze.y, dt, reduced.matches ? 18 : 12);
        eyes.position.set(motion ? eyeX * 0.2 : 0, -7 + (motion ? eyeY * 0.16 : 0));
        irisL.position.set(3 + eyeX, 6 + eyeY);
        irisR.position.set(3 - eyeX, 6 + eyeY);
        eyeL.scale.y = 0.7 * eyeOpen;
        eyeR.scale.y = 0.7 * rightOpen;
        eyeL.rotation = damp(eyeL.rotation, laughing || expression === "HAPPY" ? -0.1 : angry ? 0.13 : state === "CONFUSED" ? -0.08 : 0, dt, 12);
        eyeR.rotation = damp(eyeR.rotation, laughing || expression === "HAPPY" ? 0.1 : angry ? -0.13 : 0, dt, 12);
        mouth = damp(mouth, voiceEnergy * (motion ? 1 : 0.35), dt, voiceEnergy > mouth ? 22 : 12);
        facial.clear();
        if (sleeping) {
          for (const x of [-44, 44])
            facial
              .moveTo(x - 18, -4)
              .quadraticCurveTo(x, 6, x + 18, -4)
              .stroke({ color: 0x9cecf6, width: 3, cap: "round" });
        }
        if (mouth > 0.045) {
          facial.ellipse(0, 41, 7 + mouth * 8, 3 + mouth * 17).fill(0x14223f);
          facial
            .ellipse(0, 47 + mouth * 7, 4 + mouth * 4, 2 + mouth * 4)
            .fill({ color: 0xb9bcf8, alpha: 0.8 });
        } else if (laughing) {
          facial.ellipse(0, 43, 13, 9).fill(0x14223f);
          facial.moveTo(-8, 46).quadraticCurveTo(0, 51, 8, 46).stroke({ color: 0xcdfaff, width: 2, cap: 'round' });
        } else if (surprised) {
          facial.ellipse(0, 43, 6, 10).fill(0x14223f);
        } else if (angry) {
          facial.moveTo(-11, 48).quadraticCurveTo(0, 39, 11, 48).stroke({ color: 0xcdfaff, width: 3, cap: 'round' });
        } else if (sad || state === "ERROR" || state === "CONFUSED") {
          facial
            .moveTo(-9, 44)
            .quadraticCurveTo(0, 35, 9, 44)
            .stroke({ color: 0xcdfaff, width: 3, cap: "round" });
        } else {
          facial
            .moveTo(-12, 36)
            .quadraticCurveTo(0, proud ? 53 : expression === "HAPPY" ? 54 : 46, 12, 36)
            .stroke({ color: 0xcdfaff, width: 3, cap: "round" });
        }
        brow = damp(brow, state === "LISTENING" ? -6 : surprised ? -9 : angry ? 6 : sad || state === "ERROR" ? 4 : 0, dt, 12);
        if (!sleeping) {
          const questioning = state === "CONFUSED" || state === "THINKING" || curious;
          const worried = state === "ERROR" || sad;
          facial.moveTo(-61, -45 + brow)
            .quadraticCurveTo(-46, -51 + brow - (questioning ? 7 : 0) + (angry ? 10 : 0), -30, -45 + brow - (worried ? 8 : 0) + (angry ? 12 : 0))
            .stroke({ color: 0xe4fcff, alpha: 0.8, width: 2.5, cap: "round" });
          facial.moveTo(30, -45 + brow - (worried ? 8 : 0))
            .quadraticCurveTo(46, -51 + brow + (questioning ? 7 : 0) + (angry ? 10 : 0), 61, -45 + brow + (questioning ? 4 : 0) - (angry ? 12 : 0))
            .stroke({ color: 0xe4fcff, alpha: 0.8, width: 2.5, cap: "round" });
        }
        if (state === "THINKING")
          for (let i = 0; i < 3; i++)
            facial
              .circle(-12 + i * 12, -85, 2.5)
              .fill({
                color: 0xf3ffff,
                alpha: 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * 4 - i)),
              });
        if (expression === "HAPPY" || laughing || proud)
          for (const x of [-76, 76])
            facial.ellipse(x, 25, 10, 4).fill({ color: 0xe3bbf9, alpha: 0.5 });
        if (sad) facial.ellipse(63, 4, 3, 7).fill({ color: 0x9fe9ff, alpha: 0.75 });
        if (surprised) for (const x of [-44, 44]) facial.circle(x, -9, 3).fill({ color: 0xf3ffff, alpha: 0.75 });
        const count =
          s.particles && motion && !s.lowPower
            ? Math.round((sleeping ? 5 : 18) * quality)
            : 0;
        sparkles.forEach((p, i) => {
          p.sprite.visible = i < count;
          if (!p.sprite.visible) return;
          const angle = p.angle + t * p.speed * (state === "THINKING" ? 2 : 1);
          p.sprite.position.set(
            Math.cos(angle) * p.radius,
            Math.sin(angle * 0.8) * 110 - 20,
          );
          p.sprite.alpha =
            (0.18 + 0.5 * (0.5 + 0.5 * Math.sin(t * 1.4 + p.phase))) *
            s.brightness;
        });
        if (musicMotion) {
          // A quiet listening gesture, not a guessed beat or emotional classification.
          const sway = Math.sin(t * 1.8);
          root.rotation += sway * .035;
          root.y += Math.sin(t * 3.6) * 2;
          finL.rotation += sway * .08; finR.rotation -= sway * .08;
          if (t % 12 < 3) for (let i = 0; i < 2; i++) {
            const x = 115 + i * 21, y = -70 - (t % 12) * 16 - i * 16;
            pastime.ellipse(x,y,4,2.5).fill({ color: 0xc9f4ff, alpha: .45 });
            pastime.moveTo(x+3,y).lineTo(x+3,y-13).stroke({ color: 0xc9f4ff, alpha: .45, width: 1.5 });
          }
          if (t % 15 < 2) {
            facial.moveTo(-12,36).quadraticCurveTo(0,53,12,36).stroke({color:0xcdfaff,width:3,cap:'round'});
          }
        }
        if (intro) {
          app!.ticker.maxFPS = s.introFPS;
          intro.update(app!, avatar);
        }
        if (!intro && introLanding) {
          app!.ticker.maxFPS = 60;
          root.position.set(0,0); root.rotation = 0; root.scale.set(1);
          root.alpha = s.opacity * (s.nightMode ? .7 : 1); body.tint = 0xffffff;
          finL.rotation = -.35; finR.rotation = .35;
          eyes.position.set(0,-7); eyeL.scale.y = eyeR.scale.y = .7;
          irisL.position.set(3,6); irisR.position.set(3,6);
          shadow.scale.set(.85); shadow.alpha = .65;
          if (landingSent !== introLanding) {
            landingSent = introLanding;
            const token = introLanding;
            requestAnimationFrame(() => requestAnimationFrame(() => {
              if (!disposed && useStore.getState().introLanding === token) void bridge.introPetRendered?.(token).catch(() => {});
            }));
          }
        } else landingSent = '';
        if (!intro && departure) {
          if (departureToken !== departure) { departureToken = departure; departureStart = performance.now(); }
          const exit = departureTimeline.sample((performance.now() - departureStart) / 1000);
          app!.ticker.maxFPS = s.lowPower ? 30 : 60;
          scene.alpha = exit.alpha; root.y += exit.y; root.rotation += exit.tilt; root.scale.set(exit.scale);
          armR.rotation -= exit.wave; finR.rotation += exit.wave * .3; eyeR.scale.y *= exit.wink;
          if (exit.done && !departureDone) { departureDone = true; void bridge.departureComplete?.(departure).catch(() => {}); }
        }
      });
      const oldCleanup = cleanup;
      const pointer = (event: PointerEvent) => {
        if (event.pointerType === "touch" || (!preview && useStore.getState().native)) return;
        const bounds = host.current?.getBoundingClientRect();
        if (bounds) signals.cursor = { x: (event.clientX - bounds.left) / bounds.width, y: (event.clientY - bounds.top) / bounds.height };
      };
      document.addEventListener("pointermove", pointer, { passive: true });
      cleanup = () => {
        offStyle();
        document.removeEventListener("pointermove", pointer);
        document.removeEventListener("visibilitychange", visibility);
        offVisibility();
        oldCleanup();
        Object.values(tex).forEach((t) => t.destroy(true));
      };
    };
    let cleanup = () => {
      if (!preview) signals.hitTest = undefined;
      observer?.disconnect();
      // A saved accent can replace this effect while Pixi is still awaiting
      // its renderer. Application plugins cannot be destroyed before init.
      // In that case the completed initializer owns deferred cleanup.
      if (app && initialized) {
        app.stop();
        app.destroy(true, { children: true });
        app = undefined;
        initialized = false;
      }
    };
    void initialize().catch((error) => {
      if (intro) void window.karenIntro?.finish().catch(() => {});
      if (!disposed)
        useStore.setState({
          error: `No se pudo iniciar el renderizador: ${String(error)}`,
        });
    });
    return () => {
      disposed = true;
      cleanup();
    };
  }, [ready, preview, intro]);
  return (
    <div
      ref={host}
      className={`pet-renderer ${className}`}
      role="img"
      aria-label={`Karen, estilo ${petStyles[petStyle].name}, ${showArms ? 'con' : 'sin'} brazos y ${showLegs ? 'con' : 'sin'} piernas`}
    />
  );
}
