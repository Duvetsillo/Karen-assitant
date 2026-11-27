import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Heart, Music2, Pause, Pin, Play, SkipBack, SkipForward, X } from 'lucide-react';
import { chooseMusicSession, musicPosition, type MusicRequest } from '../../shared/music';
import { bridge } from '../native';
import { platformNames, time, useMusic } from './state';
import './capsule.css';

export function MusicCapsule() {
  const snapshot=useMusic(), song=chooseMusicSession(snapshot.sessions,snapshot.activeId);
  const [visible,setVisible]=useState(true);
  const [expanded,setExpanded]=useState(false),[now,setNow]=useState(Date.now()),[error,setError]=useState(''),[ambient,setAmbient]=useState('');
  const leave=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  const art=useRef<HTMLImageElement>(null);
  const details=useRef<HTMLDivElement>(null);
  const options=snapshot.playerOptions;
  const sampleAmbient=(image:HTMLImageElement)=>{
    if(!options?.ambientColors){setAmbient('');return;}
    try{const canvas=document.createElement('canvas');canvas.width=canvas.height=1;const context=canvas.getContext('2d');context?.drawImage(image,0,0,1,1);const color=context?.getImageData(0,0,1,1).data;if(color)setAmbient(`rgba(${color[0]},${color[1]},${color[2]},.18)`);}catch{setAmbient('');}
  };
  useEffect(()=>bridge.event(event=>{if(event.type==='surface-visibility')setVisible(event.visible);}),[]);
  useEffect(()=>{if(art.current?.complete)sampleAmbient(art.current);},[options?.ambientColors,song?.cover]);
  useEffect(()=>{const height=Math.max(150,Math.min(360,(details.current?.scrollHeight??100)+104));void bridge.music?.layout?.(expanded,expanded?height:undefined).catch(()=>{});},[expanded,snapshot.sessions.length,error,song?.controls.join(',')]);
  useEffect(()=>{
    setNow(Date.now()); if(song?.status!=='playing')return;
    const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);
  },[song?.trackId,song?.status]);
  useEffect(()=>{setError('');},[song?.trackId]);
  useEffect(()=>()=>clearTimeout(leave.current),[]);
  const request=async(action:MusicRequest)=>{
    setError('');try{await bridge.music?.action(action);}catch(error){setError(error instanceof Error?error.message:'No se pudo completar el control.');setExpanded(true);}
  };
  const control=(action:MusicRequest['action'],value?:MusicRequest['value'])=>void request({action,sessionId:song?.sessionId,trackId:song?.trackId,value});
  const has=(action:string)=>Boolean(song?.controls.includes(action as never));
  const position=song&&musicPosition(song,now), progress=song?.duration&&position!==undefined?Math.min(100,position/song.duration*100):0;
  const collapse=()=>{clearTimeout(leave.current);setExpanded(false);};
  return <section className="music-capsule" data-expanded={expanded} data-visible={visible} aria-label="Cápsula musical de Karen"
    style={ambient&&options?.ambientColors?{background:`linear-gradient(125deg,${ambient},#141925 75%)`}:undefined}
    onMouseEnter={()=>{clearTimeout(leave.current);if(options?.hoverExpand)setExpanded(true);}}
    onMouseLeave={()=>{if(options?.hoverExpand)leave.current=setTimeout(collapse,350);}}
    onKeyDown={event=>{if(event.key==='Escape')collapse();}}>
    <div className="capsule-main">
      <div className="capsule-art">{song?.cover?<img ref={art} src={song.cover} alt="Portada del álbum" onLoad={event=>sampleAmbient(event.currentTarget)}/>:<Music2 size={22}/>}</div>
      <div key={song?.trackId??'empty'} className="capsule-track"><span>{song?.platform?platformNames[song.platform]:'KAREN / MÚSICA'}</span><h2 title={song?.title}>{song?.title??(snapshot.enabled?'Esperando música':'Percepción apagada')}</h2><p title={song?.artist}>{song?.artist??'Ajustes → Música'}</p></div>
      <div className="capsule-transport" aria-label="Controles de reproducción">
        <button aria-label="Canción anterior" disabled={!has('previous')} onClick={()=>control('previous')}><SkipBack size={15}/></button>
        <button className="capsule-play" aria-label={song?.status==='playing'?'Pausar música':'Reproducir música'} disabled={!has(song?.status==='playing'?'pause':'play')} onClick={()=>control(song?.status==='playing'?'pause':'play')}>{song?.status==='playing'?<Pause size={18}/>:<Play size={18}/>}</button>
        <button aria-label="Siguiente canción" disabled={!has('next')} onClick={()=>control('next')}><SkipForward size={15}/></button>
      </div>
      <button className="capsule-expand" aria-label={expanded?'Contraer reproductor':'Expandir reproductor'} aria-expanded={expanded} onClick={()=>setExpanded(value=>!value)}><ChevronDown size={15}/></button>
    </div>
    <div className="capsule-progress" role="progressbar" aria-label="Progreso de la canción" aria-valuenow={Math.round(progress)} aria-valuemin={0} aria-valuemax={100}><i style={{width:`${progress}%`}}/></div>
    <div ref={details} className="capsule-details" inert={!expanded}>
      {song&&<><label className="capsule-seek">Posición de reproducción<input aria-label="Posición de reproducción" type="range" min="0" max={song.duration??1} value={Math.min(song.duration??1,position??0)} disabled={!has('seek')||!song.duration} onChange={event=>control('seek',Number(event.target.value))}/></label><div className="capsule-times"><span>{time(position)}</span><span>{time(song.duration)}</span></div></>}
      {snapshot.sessions.length>1&&<label className="capsule-sessions">Sesión<select aria-label="Sesión multimedia" value={song?.sessionId} onChange={event=>void request({action:'select',sessionId:event.target.value})}>{snapshot.sessions.map(session=><option key={session.sessionId} value={session.sessionId}>{session.title}</option>)}</select></label>}
      {song&&has('volume')&&song.volume!==undefined&&<label className="capsule-volume">Volumen de esta sesión<input aria-label="Volumen de esta sesión" type="range" min="0" max="1" step=".05" value={song.volume} onChange={event=>control('volume',Number(event.target.value))}/></label>}
      <div className="capsule-playback-mode">{has('shuffle')&&<button aria-pressed={song?.shuffle??false} onClick={()=>control('shuffle',!song?.shuffle)}>Aleatorio</button>}{has('repeat')&&<label>Repetición<select aria-label="Repetición" value={song?.repeat??'none'} onChange={event=>control('repeat',event.target.value)}><option value="none">Desactivada</option><option value="track">Canción</option><option value="list">Lista</option></select></label>}</div>
      <div className="capsule-actions"><button aria-label="Me gusta esta canción" disabled={!song||!snapshot.historyAvailable||!snapshot.historyEnabled} title="Necesita historial musical autorizado" onClick={()=>control('like')}><Heart size={16}/></button><button aria-label="Anclar reproductor" aria-pressed={snapshot.playerPinned??false} onClick={()=>control('pin',!snapshot.playerPinned)}><Pin size={16}/></button><button className="capsule-close" aria-label="Cerrar reproductor" onClick={()=>control('close')}><X size={16}/><span>Cerrar</span></button></div>
      {(error||snapshot.error)&&<p className="capsule-error" role="alert">{error||snapshot.error}</p>}
      {!song&&<p className="capsule-empty">Activa la percepción musical en Ajustes para detectar una sesión compatible.</p>}
    </div>
  </section>;
}
