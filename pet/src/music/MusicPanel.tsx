import { useEffect, useState } from 'react';
import { Music2, Play, Pause, SkipBack, SkipForward, X, Pin, Minus, Heart } from 'lucide-react';
import { bridge } from '../native';
import { report, useStore } from '../state/store';
import { MUSIC_PLATFORMS, chooseMusicSession, musicPosition, type MusicSnapshot, type MusicRequest, type MusicHistoryRow } from '../../shared/music';
import type { Settings } from '../../shared/types';

export { useMusic } from './state';
import { useMusic, act, time, platformNames } from './state';
export function MusicPlayer({ mini = false }: { mini?: boolean }) {
  const state = useMusic(), song = chooseMusicSession(state.sessions, state.activeId);
  const [now, setNow] = useState(Date.now());
  const pinned = state.playerPinned ?? false;
  useEffect(() => {
    if (song?.status !== 'playing') return;
    const timer = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 1000);
    return () => clearInterval(timer);
  }, [song?.status, song?.sessionId]);
  const control = (action: MusicRequest['action'], value?: MusicRequest['value']) => void invoke({ action, value, sessionId: song?.sessionId, trackId: song?.trackId });
  const supported = (name: string) => Boolean(song?.controls.includes(name as never));
  const position = song ? musicPosition(song, now) : undefined;
  const [error, setError] = useState('');
  const invoke = async (request: MusicRequest) => { try { setError(''); await bridge.music?.action(request); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } };
  return <section className={`music-player ${mini ? 'music-mini' : ''}`} aria-label="Reproductor musical de Karen">
    <header className="music-header"><span><Music2 size={17}/> KAREN / MÚSICA</span>{mini && <div>
      <button aria-label="Anclar reproductor" aria-pressed={pinned} onClick={() => void invoke({ action: 'pin', value: !pinned })}><Pin size={15}/></button>
      <button aria-label="Minimizar reproductor" onClick={() => void invoke({ action: 'minimize' })}><Minus size={16}/></button>
      <button aria-label="Ocultar reproductor" onClick={() => void invoke({ action: 'close' })}><X size={16}/></button>
    </div>}</header>
    {song ? <>
      <div className="music-track"><div className="music-art">{song.cover ? <img src={song.cover} alt="Portada del álbum"/> : <Music2 size={44} aria-hidden="true"/>}</div>
        <div><small>{song.platform ? platformNames[song.platform] : song.source}</small><h2>{song.title}</h2>{song.artist && <p>{song.artist}</p>}{song.album && <p className="music-album">{song.album}</p>}</div>
      </div>
      {state.sessions.length > 1 && <label>Sesión multimedia<select value={state.activeId} onChange={e => void invoke({ action: 'select', sessionId: e.target.value })}>
        {state.sessions.map(s => <option key={s.sessionId} value={s.sessionId}>{s.platform ? platformNames[s.platform] : s.source} · {s.title}</option>)}
      </select></label>}
      <label className="music-progress">Posición<input aria-label="Posición de reproducción" type="range" min="0" max={song.duration ?? 1} step="1" value={Math.min(song.duration ?? 1, position ?? 0)} disabled={!supported('seek') || !song.duration} onChange={e => control('seek', Number(e.target.value))}/></label>
      <div className="music-times"><span>{time(position)}</span><span>{time(song.duration)}</span></div>
      <div className="music-controls"><button aria-label="Canción anterior" disabled={!supported('previous')} onClick={() => control('previous')}><SkipBack size={21}/></button>
        <button className="music-play" aria-label={song.status === 'playing' ? 'Pausar música' : 'Reproducir música'} disabled={!supported(song.status === 'playing' ? 'pause' : 'play')} onClick={() => control(song.status === 'playing' ? 'pause' : 'play')}>{song.status === 'playing' ? <Pause size={24}/> : <Play size={24}/>}</button>
        <button aria-label="Siguiente canción" disabled={!supported('next')} onClick={() => control('next')}><SkipForward size={21}/></button>
        <button aria-label="Me gusta esta canción" onClick={() => void invoke({ action: 'like', sessionId: song.sessionId, trackId: song.trackId })}><Heart size={19}/></button></div>
      {supported('volume') && song.volume !== undefined && <label>Volumen de esta sesión<input type="range" min="0" max="1" step=".05" value={song.volume} onChange={e => control('volume', Number(e.target.value))}/></label>}
      {supported('shuffle') && <button aria-pressed={song.shuffle ?? false} onClick={() => control('shuffle', !song.shuffle)}>Aleatorio</button>}
      {supported('repeat') && <label>Repetición<select value={song.repeat ?? 'none'} onChange={e => control('repeat', e.target.value)}><option value="none">Desactivada</option><option value="track">Canción</option><option value="list">Lista</option></select></label>}
    </> : <div className="music-empty"><Music2 size={38}/><h2>{state.enabled ? 'Esperando música confirmada' : 'La percepción musical está apagada'}</h2><p>{state.enabled ? 'Reproduce música en una sesión compatible. Los vídeos ambiguos permanecen fuera.' : 'Puedes activarla en Ajustes → Música.'}</p></div>}
    {(error || state.error) && <p role="alert" className="music-error">{error || state.error}</p>}
    {state.comment && song?.trackId === state.comment.trackId && <p className="music-notice" role="status">{state.comment.text}</p>}
  </section>;
}
export function MusicSettings() {
  const s = useStore(x => x.settings), state = useMusic();
  const [history, setHistory] = useState<MusicHistoryRow[]>([]), [token, setToken] = useState('');
  const save = async (patch: Partial<Settings>) => { try { useStore.setState({ settings: await bridge.settings(patch) }); } catch (e) { report(e); } };
  const toggle = (label: string, key: keyof Settings, description: string) => <div className="setting-row"><div><label>{label}</label><p>{description}</p></div>
    <button className="toggle" role="switch" aria-label={label} aria-checked={Boolean(s[key])} disabled={!bridge.music} onClick={() => void save({ [key]: !s[key] })}><span/></button></div>;
  return <div className="music-settings"><section className="group"><h2>Escuchar tu música</h2>{state.error&&<p role="alert" className="music-error">{state.error}</p>}<p className="group-description">Conecta su presencia con lo que ya estás escuchando.</p>
    {toggle('Percepción musical', 'musicEnabled', 'Lee metadatos de Windows o del complemento emparejado. No captura audio.')}
    {toggle('Aparición automática', 'musicAutoShow', 'Muestra la cápsula solo ante una sesión musical confirmada, sin tomar el foco.')}
    {toggle('Expandir al pasar el cursor', 'musicHoverExpand', 'También puedes expandirla con el botón o contraerla con Escape.')}
    {toggle('Color ambiental de la portada', 'musicAmbientColors', 'Un matiz suave de la portada, calculado en esta PC.')}
    <label className="music-hide-delay">Ocultar tras una pausa (segundos)<input type="number" min="0" max="300" value={s.musicAutoHideSeconds} onChange={e=>void save({musicAutoHideSeconds:Number(e.target.value)})}/></label>
    {toggle('Minirreproductor', 'musicPlayer', 'Una ventana independiente, movible y con controles de la sesión.')}
    <button disabled={!bridge.music || !s.musicPlayer} onClick={() => void act({ action: 'open' })}>Abrir reproductor</button>
    <fieldset className="music-platforms"><legend>Plataformas habilitadas</legend>{MUSIC_PLATFORMS.map(p => <label className="music-check" key={p}><input type="checkbox" checked={s.musicPlatforms.includes(p)} onChange={e => void save({ musicPlatforms: e.target.checked ? [...s.musicPlatforms,p] : s.musicPlatforms.filter(x => x !== p) })}/>{platformNames[p]}</label>)}</fieldset>
    {toggle('Filtrado estricto de YouTube', 'musicStrictYouTube', 'Exige evidencia de categoría musical; un título o canal no bastan.')}
    <details className="settings-disclosure"><summary>Conectar música del navegador</summary><div>
    <p className="quiet-note">GSMTC no identifica dominios de pestañas. Para música web usa el complemento opcional de Chrome/Edge, restringido a los cinco sitios multimedia indicados. Compatibilidad real por plataforma pendiente de validación.</p>
    <div className="button-row"><button onClick={() => { void act({ action: 'pair-browser' }).then(value => { if (typeof value === 'string') setToken(value); }); }}>Generar código del complemento</button>
      <button onClick={() => { setToken(''); void act({ action: 'revoke-browser' }); }}>Revocar complemento</button></div>
    {token && <label>Código privado de emparejamiento<input readOnly type="password" value={token} aria-label="Código privado de emparejamiento" onFocus={e => e.currentTarget.select()}/><small>Cópialo a las opciones del complemento. No lo compartas.</small></label>}
    </div></details>
  </section><section className="group"><h2>Su presencia musical</h2>
    {toggle('Animaciones musicales', 'musicAnimations', 'Balanceos y notas discretas con las apariencias actuales. No infiere BPM ni emociones.')}
    {toggle('Reacciones durante juegos', 'musicGamingReactions', 'Solo reacciones visuales suaves al usar el modo Gaming; nunca comentarios.')}
    {toggle('Comentarios espontáneos', 'musicComments', 'Una evaluación tras 45 segundos. Prefiere una reacción visual; usa audio pregenerado si está disponible.')}
    <div className="music-fields">
      {([['Probabilidad por canción','musicCommentProbability',0,1,.05],['Volumen de comentarios','musicCommentVolume',0,1,.05],['Minutos entre comentarios','musicCooldownMinutes',1,240,1],['Máximo cada tres horas','musicMaxComments',1,10,1]] as const).map(([label,key,min,max,step]) => <label key={key}>{label}<input type="number" min={min} max={max} step={step} value={s[key]} onChange={e => void save({ [key]: Number(e.target.value) })}/></label>)}
    </div><p className="quiet-note">Se bloquean por actividad de Karen, ausencia, introducciones, No molestar y escritorio ocupado. Apps de comunicación o micrófono en uso también bloquean por precaución.</p>
  </section><section className="group"><h2>Memoria musical</h2>
    {toggle('Historial musical', 'musicHistory', 'Guarda solo metadatos y tiempo estimado en la memoria Core conectada. Una reproducción no indica gusto.')}
    {!state.historyAvailable && <p className="quiet-note">Conecta Karen Core para guardar el historial y las preferencias musicales.</p>}
    {toggle('Exportar resúmenes para Obsidian', 'musicObsidian', 'Exporta un resumen agregado en el archivo Markdown que elijas; no crea notas por reproducción.')}
    <div className="button-row"><button onClick={() => { void bridge.music?.history().then(setHistory).catch(report); }}>Ver historial</button><button disabled={!s.musicObsidian} onClick={() => void act({ action: 'summary' })}>Exportar resumen</button>
      <button onClick={() => { void act({ action: 'clear-history' }).then(() => setHistory([])); }}>Borrar historial musical</button></div>
    {history.length > 0 && <ul>{history.map(row => <li key={row.trackId}>{row.title}{row.artist ? ' — ' + row.artist : ''} · {row.plays} reproducciones · {Math.round(row.seconds)} s</li>)}</ul>}
  </section><div className="music-inline-status"><Music2 size={19}/><div><strong>{chooseMusicSession(state.sessions,state.activeId)?.title??'Tu música, cuando decidas compartirla.'}</strong><p>La cápsula aparece fuera del panel y no ocupa espacio aquí.</p></div></div></div>;
}
