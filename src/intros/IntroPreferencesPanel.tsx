import { useEffect, useState } from 'react';
import { INTRO_IDS, IntroRegistry } from '../../shared/startup-intros';
import type { Settings } from '../../shared/types';
import { bridge } from '../native';

export function IntroPreferencesPanel({ settings: s, patch, report }: {
  settings: Settings; patch: (patch: Partial<Settings>) => Promise<void>; report: (error: unknown) => void;
}) {
  const [monitors, setMonitors] = useState<{ id: string; name: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [greeting, setGreeting] = useState<{ available: boolean; message: string }>();
  useEffect(() => {
    let alive = true;
    void bridge.introGreetingStatus?.().then(result => { if (alive) setGreeting(result); }).catch(report);
    return () => { alive = false; };
  }, [s.voiceStyle,s.ttsEngine,s.voiceRoot,s.introFixed,report]);
  useEffect(() => { void bridge.introMonitors?.().then(setMonitors).catch(report); }, [report]);
  const toggle = (label: string, key: 'introEnabled' | 'introVoice' | 'introSounds' | 'introReducedMotion' | 'introEscape' | 'farewellEnabled') =>
    <label className="intro-option"><span>{label}</span><input type="checkbox" checked={s[key]} onChange={e => void patch({ [key]: e.target.checked })} /></label>;
  return <div className="intro-preferences">
    {toggle('Activar al arrancar la aplicación', 'introEnabled')}
    {toggle('Despedida animada al salir de Karen', 'farewellEnabled')}
    <label>Selección<select value={s.introSelection} onChange={e => void patch({ introSelection: e.target.value as Settings['introSelection'] })}>
      <option value="random">Aleatoria</option><option value="fixed">Fija</option><option value="contextual">Según la hora</option>
    </select></label>
    <label>Introducción / vista previa<select value={s.introFixed} onChange={e => void patch({ introFixed: e.target.value as Settings['introFixed'] })}>
      {INTRO_IDS.map(id => <option key={id} value={id}>{IntroRegistry[id].name}</option>)}
    </select></label>
    <button disabled={!bridge.playIntro || busy} onClick={() => {
      setBusy(true);
      void bridge.playIntro?.(s.introFixed).then(ok => { if (!ok) throw new Error('Introducción omitida: Windows está ocupado o Karen está en modo protegido.'); })
        .catch(report).finally(() => setBusy(false));
    }}>Vista previa</button>
    {toggle('Saludos de voz pregrabados', 'introVoice')}
    {s.introVoice && greeting && <p className="quiet-note" role="status">{greeting.message}</p>}
    {toggle('Efectos sonoros', 'introSounds')}
    <label>Volumen de introducción<input type="range" min="0" max="1" step="0.05" value={s.introVolume} onChange={e => void patch({ introVolume: Number(e.target.value) })} /></label>
    {toggle('Movimiento reducido', 'introReducedMotion')}
    {toggle('Omitir con Escape', 'introEscape')}
    <label>Fotogramas por segundo<select value={s.introFPS} onChange={e => void patch({ introFPS: Number(e.target.value) as 30 | 60 })}><option value="60">60 FPS</option><option value="30">30 FPS</option></select></label>
    <label>Monitor<select value={s.introMonitor} onChange={e => void patch({ introMonitor: e.target.value })}>
      <option value="">Donde aparece Karen</option>{monitors.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
    </select></label>
    <p className="quiet-note">Se reproduce una vez por arranque. Los saludos necesitan la biblioteca de audio local; si falta, la entrada continúa en silencio.</p>
  </div>;
}
