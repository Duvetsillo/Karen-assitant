import { useEffect, useState } from 'react';
import { flushSync } from 'react-dom';
import type { IntroPayload } from '../../shared/startup-intros';
import { useStore } from '../state/store';
import { PetRenderer } from '../pet/Renderer';
import { IntroRenderer } from './IntroRenderer';

declare global {
  interface Window {
    karenIntro?: { payload(): Promise<IntroPayload>; ready(): Promise<boolean>; finish(): Promise<void>; prepareLanding?(): Promise<boolean>; revealPet?(): Promise<void> };
  }
}
export function StartupIntro() {
  const [renderer, setRenderer] = useState<IntroRenderer>();
  useEffect(() => {
    let alive = true, controller: IntroRenderer | undefined;
    let finishing = false, finishTimer: ReturnType<typeof setTimeout> | undefined;
    const native = window.karenIntro;
    const finish = () => {
      if (finishing) return;
      finishing = true;
      // Leave the Pixi ticker callback before destroying its renderer. Unmount
      // explicitly so GPU textures/context are released before closing Chromium.
      finishTimer = setTimeout(async () => {
        // Reveal the already-rendered desktop avatar before clearing this canvas.
        await native?.revealPet?.().catch(() => {});
        controller?.dispose();
        if (alive) flushSync(() => setRenderer(undefined));
        void native?.finish().catch(() => {});
      }, 0);
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && controller?.payload.settings.introEscape) finish();
    };
    document.addEventListener('keydown', key);
    const onError = (event: Event) => { console.error('Introducción interrumpida', event instanceof ErrorEvent ? event.message : 'Promesa rechazada'); finish(); };
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onError);
    const pagehide = () => controller?.dispose();
    window.addEventListener('pagehide', pagehide);
    void (async () => {
      if (!native) return;
      const payload = await native.payload();
      if (!alive) return;
      const reduced = payload.settings.introReducedMotion || matchMedia('(prefers-reduced-motion: reduce)').matches || !payload.settings.animations;
      controller = new IntroRenderer(payload, reduced, () => native.ready(), finish,
        () => native.prepareLanding?.().catch(() => false) ?? Promise.resolve(false));
      await controller.audio.prepare(payload.audio);
      payload.audio = undefined;
      if (!alive) { controller.dispose(); return; }
      useStore.setState({ settings: { ...payload.settings, idleActivities: false, cursorTracking: false, particles: false }, ready: true, surfaceVisible: true, native: true });
      setRenderer(controller);
    })().catch(finish);
    return () => {
      alive = false; controller?.dispose();
      clearTimeout(finishTimer);
      document.removeEventListener('keydown', key);
      window.removeEventListener('error', onError); window.removeEventListener('unhandledrejection', onError);
      window.removeEventListener('pagehide', pagehide);
    };
  }, []);
  return renderer ? <PetRenderer intro={renderer} className="intro-canvas" /> : null;
}
