import {BellOff,MessageCircle,Sparkles,X,ArrowUpRight,Clock3} from 'lucide-react';
import {useStore,report} from './state/store';
import {bridge} from './native';
import type {Settings} from '../shared/types';
import type {InitiativeAction,InitiativeNotice} from '../shared/initiative';
import {useState} from 'react';

async function act(action:InitiativeAction,id?:string){
  try{
    if(!bridge.initiative)throw new Error('La iniciativa necesita la aplicación actualizada de Windows.');
    useStore.setState({initiative:await bridge.initiative(action,id)});
  }catch(e){report(e);}
}
export function Notice({notice,compact=false}:{notice:InitiativeNotice;compact?:boolean}){
  return <section className={`initiative-notice${compact?' compact':''}`} aria-label="Sugerencia de Karen">
    <div className="initiative-notice-heading"><span><Sparkles size={14}/> Karen toma la iniciativa</span>
      <button aria-label="Descartar sugerencia" title="Descartar" onClick={()=>void act('dismiss',notice.id)}><X size={15}/></button></div>
    <p>{notice.text}</p>
    {!compact && <small>{notice.reason}</small>}
    <div className="initiative-notice-actions">
      <button onClick={()=>{
        useStore.setState({tab:'Conversación',conversationDraft:notice.command||'Quiero conversar contigo.'});
        void act('dismiss',notice.id);
        void bridge.openSettings().catch(report);
      }}><MessageCircle size={14}/>{notice.command?'Revisar tarea':'Responder'}<ArrowUpRight size={12}/></button>
      <button title="Pausar iniciativa durante una hora" onClick={()=>void act('snooze')}><BellOff size={14}/>{compact?'1 h':'Silencio 1 h'}</button>
    </div>
  </section>;
}
export function InitiativePanel(){
  const s=useStore(x=>x.settings), journal=useStore(x=>x.initiative), native=useStore(x=>x.native);
  const [busy,setBusy]=useState(false);
  const save=async(patch:Partial<Settings>)=>{try{useStore.setState({settings:await bridge.settings(patch)});}catch(e){report(e);}};
  const latest=journal?.notices.filter(n=>!n.dismissed).at(-1);
  const paused=(journal?.snoozedUntil||0)>Date.now();
  const disabled=!native||!bridge.initiative;
  const toggle=(label:string,key:'initiativeEnabled'|'initiativeSpeak',description:string)=><div className="setting-row">
    <div><label>{label}</label><p>{description}</p></div><button className="toggle" role="switch" aria-label={label} aria-checked={s[key]} disabled={disabled}
      onClick={()=>void save({[key]:!s[key]})}><span/></button></div>;
  return <div className="initiative-page">
    <div className="initiative-intro"><span className="eyebrow">COMPAÑÍA, A TU RITMO</span>
      <h2>También puede empezar Karen.</h2><p>Un saludo, una pregunta o un aviso de tus tareas. Tú eliges cuándo y cuánto.</p>
      <span className={`initiative-status ${s.initiativeEnabled&&!paused&&s.mode==='normal'?'on':''}`}><i/>{!s.initiativeEnabled?'Iniciativa desactivada':s.mode!=='normal'?'En pausa por tu modo actual':paused?'En silencio durante una hora':'Iniciativa activada'}</span>
    </div>
    <section className="group">
      {toggle('Karen puede iniciar conversación','initiativeEnabled','Sugiere sin abrir el micrófono ni enviar consultas a un proveedor.')}
      {toggle('Decir las sugerencias en voz alta','initiativeSpeak','Usa tu voz configurada cuando las respuestas habladas estén activadas.')}
      <div className="initiative-fields">
        <div className="input-field"><label htmlFor="initiative-interval">Entre conversaciones</label><select id="initiative-interval" value={s.initiativeInterval} disabled={disabled} onChange={e=>void save({initiativeInterval:Number(e.target.value)})}>
          {[15,30,45,60,120,240,...([15,30,45,60,120,240].includes(s.initiativeInterval)?[]:[s.initiativeInterval])].sort((a,b)=>a-b).map(v=><option key={v} value={v}>{v} minutos</option>)}</select></div>
        <div className="input-field"><label htmlFor="initiative-limit">Máximo por día</label><select id="initiative-limit" value={s.initiativeDailyLimit} disabled={disabled} onChange={e=>void save({initiativeDailyLimit:Number(e.target.value)})}>
          {Array.from({length:12},(_,i)=>i+1).map(v=><option key={v} value={v}>{v} {v===1?'vez':'veces'}</option>)}</select></div>
        {(['initiativeQuietStart','initiativeQuietEnd'] as const).map((key,i)=><div className="input-field" key={key}><label htmlFor={key}>{i?'Volver a hablar desde':'Guardar silencio desde'}</label><select id={key} value={s[key]} disabled={disabled} onChange={e=>void save({[key]:Number(e.target.value)})}>
          {Array.from({length:24},(_,h)=><option key={h} value={h}>{String(h).padStart(2,'0')}:00</option>)}</select></div>)}
      </div>
      <p className="quiet-note">Horario local del equipo. Horas iguales desactivan el horario silencioso. Espera si estás hablando, hay una respuesta en curso, el PC está bloqueado o llevas tres minutos ausente.</p>
      <div className="button-row"><button className="primary" disabled={disabled||busy||!s.initiativeEnabled} onClick={async()=>{setBusy(true);try{await act('now');}finally{setBusy(false);}}}><Sparkles size={15}/>{busy?'Preparando…':'Sugerir ahora'}</button>
        <button disabled={disabled} onClick={()=>void act(paused?'resume':'snooze')}><BellOff size={15}/>{paused?'Reanudar iniciativa':'Silencio durante 1 h'}</button></div>
      <p className="quiet-note">«Sugerir ahora» es una petición manual: omite horario, pausa y cuota. Respeta actividades en curso y tu modo.</p>
      {!s.voiceEnabled&&s.initiativeSpeak&&<p className="info-note">Las respuestas habladas están desactivadas. Las sugerencias se mostrarán por escrito.</p>}
      {disabled&&<p className="info-note">Disponible en Karen para Windows. Esta vista no inicia conversaciones por su cuenta.</p>}
    </section>
    {latest&&<Notice notice={latest}/>}
    <section className="group initiative-history"><div className="section-heading"><h2>Lo que te ha propuesto</h2><span>{journal?.todayCount||0} hoy</span></div>
      {journal?.notices.length?<ol>{[...journal.notices].reverse().map(n=><li key={n.id}><Clock3 size={15}/><div><time dateTime={new Date(n.at).toISOString()}>{new Date(n.at).toLocaleString('es',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})}</time><p>{n.text}</p><small>{n.reason}{n.dismissed?' · Cerrado':''}</small></div></li>)}</ol>:
        <p className="quiet-note">Todavía no hay propuestas. Las que aparezcan aquí serán avisos reales, con su motivo.</p>}
    </section>
    <p className="quiet-note">Esta iniciativa ofrece compañía y detecta cambios de tareas mientras Karen está abierta. Las acciones y aprobaciones siguen en tus manos.</p>
  </div>;
}
