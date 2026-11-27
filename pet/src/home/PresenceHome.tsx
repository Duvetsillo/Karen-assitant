import { useEffect } from 'react';
import { bridge } from '../native';
import { ArrowUpRight, AudioLines, MessageCircle, Music2, Settings2 } from 'lucide-react';
import { PetRenderer } from '../pet/Renderer';
import { useStore } from '../state/store';
import { chooseMusicSession } from '../../shared/music';
import type { PetState } from '../../shared/types';
import { isLocalInferenceModel } from '../../shared/local-inference';

export function PresenceHome({ stateLabel }: { stateLabel: (state: PetState) => string }) {
  const state = useStore(s => s.state), settings = useStore(s => s.settings), capture = useStore(s => s.capture),
    wake = useStore(s => s.wakeStatus), connection = useStore(s => s.connection), models = useStore(s => s.models), music = useStore(s => s.music);
  useEffect(() => {
    let alive=true;
    if(connection.state==='connected')void bridge.models().then(models=>{if(alive)useStore.setState({models});}).catch(()=>{});
    return ()=>{alive=false;};
  },[connection.state]);
  const song = music && chooseMusicSession(music.sessions, music.activeId);
  const local = models?.effective && isLocalInferenceModel(models.effective);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Buenos días.' : hour < 20 ? 'Buenas tardes.' : 'Buenas noches.';
  const open = (tab: string) => useStore.setState({ tab });
  return <section className="presence-home" aria-label="Presencia de Karen">
    <div className="presence-introduction"><span className="eyebrow">TU COMPAÑERA DE ESCRITORIO</span><h2>{greeting}<br/><span>Estoy aquí.</span></h2><p>Una idea, una tarea o un momento para pensar.</p></div>
    <div className="presence-stage" data-state={state}>
      <div className="presence-stage-orbit" aria-hidden="true"/>
      <PetRenderer preview className="presence-avatar"/>
      <span className="presence-state"><i/>{stateLabel(state)}</span>
    </div>
    <div className="presence-footer">
      <div className="presence-signals" aria-label="Estado real de Karen">
        <button onClick={() => open('OpenClaw')}><span className={`signal-dot ${connection.state}`}/>{connection.state === 'connected' ? local ? 'Modelo local' : 'Revisar modelo' : 'Revisar conexión'}<ArrowUpRight size={12}/></button>
        <button onClick={() => open('Voz')}><AudioLines size={14}/>{capture.phase === 'recording' ? 'Escuchando' : capture.phase === 'speaking' ? 'Hablando' : wake === 'listening' ? 'Activación disponible' : 'Activación pausada'}</button>
        {settings.musicEnabled && song?.status === 'playing' && <button className="presence-song" onClick={() => open('Música')}><Music2 size={14}/><span>{song.title}</span></button>}
      </div>
      <div className="presence-actions"><button className="presence-talk" onClick={() => open('Conversación')}><MessageCircle size={17}/>Hablemos<ArrowUpRight size={16}/></button><button className="presence-adjust" onClick={() => open('Centro de control')}><Settings2 size={17}/>A tu manera</button></div>
      <p>La percepción y la iniciativa se activan solo cuando tú decides.</p>
    </div>
  </section>;
}
