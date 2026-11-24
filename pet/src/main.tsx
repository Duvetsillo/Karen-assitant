import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { canSendMessage } from '../shared/local-commands';
import {
  MessageCircle,
  Sparkles,
  SlidersHorizontal,
  Radio,
  AudioLines,
  Monitor,
  Activity,
  ChevronRight,
  ArrowUp,
  Mic,
  Square,
  Settings as SettingsIcon,
  EyeOff,
  X,
  RefreshCw,
  Check,
  Moon,
  Zap,
  Volume2,
  VolumeX,
  RotateCcw,
  Power,
  CircleHelp,
  PersonStanding,
  Bell,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { PetState, Settings } from "../shared/types";
import { PET_STATES } from "../shared/types";
import { bridge } from "./native";
import { machine, signals, useStore, report } from "./state/store";
import { PetRenderer } from "./pet/Renderer";
import { AudioDirector } from "./voice/audio";
import { VoiceReplies } from "./voice/replies";
import "./style.css";
import { APP_VERSION } from "../shared/version";
import { mergeMessages } from "../shared/protocol";
import { PET_SCALE } from "../shared/pet-layout";
import { effectiveSettings } from '../shared/settings';
import { Perception, CaptureIndicator } from "./Perception";
import { ModelPicker } from './ModelPicker';
import { StylePicker } from './pet/StylePicker';
import {InitiativePanel,Notice} from './InitiativePanel';
import { ScreenActionApproval } from './ScreenActionApproval';
import { PRESENCE_PRESETS } from './pet/presence-motion';
import { petStyles } from '../shared/pet-styles';

const isPet = new URLSearchParams(location.search).get("view") === "pet";
document.documentElement.dataset.view = isPet ? "pet" : "settings";
document.title = isPet ? "Karen Desktop Pet" : "Karen · Ajustes";
const labels: Record<PetState, string> = {
  IDLE: "En calma",
  LISTENING: "Escuchando",
  THINKING: "Pensando",
  SPEAKING: "Hablando",
  HAPPY: "Feliz",
  LAUGHING: "Riendo",
  ANGRY: "Molesta",
  SAD: "Triste",
  SURPRISED: "Sorprendida",
  PROUD: "Orgullosa",
  CURIOUS: "Curiosa",
  CONFUSED: "Con duda",
  ERROR: "Algo ocurrió",
  SLEEPING: "Descansando",
  DRAGGING: "En tus manos",
};
const audio = isPet ? new AudioDirector() : undefined;
const replies = audio ? new VoiceReplies(text => audio.speak(text), () => ({ enabled: effectiveSettings(useStore.getState().settings).voiceEnabled, capture: useStore.getState().capture })) : undefined;
async function action(operation: () => Promise<unknown>) {
  try {
    useStore.setState({ error: "" });
    await operation();
  } catch (e) {
    report(e);
  }
}
async function patch(patch: Partial<Settings>) {
  await action(async () => {
    useStore.setState({ settings: await bridge.settings(patch) });
  });
}
function Logo() {
  return (
    <svg viewBox="0 0 40 44" aria-hidden="true">
      <path
        d="M10 17C4 12 7 3 10 3c6 3 7 8 6 11m14 3c6-5 3-14 0-14-6 3-7 8-6 11"
        fill="#b7bef5"
      />
      <path
        d="M20 12C6 11 2 22 5 32c1 6 6 10 11 7 4 4 7 1 9 0 7 4 13-4 11-14-1-8-6-13-16-13"
        fill="#b4edf8"
      />
      <path d="M9 24q11-6 22 0v7q-11 6-22 0" fill="#263c59" />
      <ellipse cx="15" cy="27" rx="2.6" ry="3.6" fill="#e6fdff" />
      <ellipse cx="25" cy="27" rx="2.6" ry="3.6" fill="#e6fdff" />
    </svg>
  );
}
function Status({ compact = false }: { compact?: boolean }) {
  const c = useStore((s) => s.connection);
  return (
    <span className={`connection ${c.state}`} title={c.message}>
      <i />
      {compact
        ? c.state === "connected"
          ? "Conectada"
          : c.state === "reconnecting"
            ? "Reconectando"
            : c.state === "connecting"
              ? "Conectando"
              : c.state === "action-required"
                ? "Revisar conexión"
                : "Desconectada"
        : c.message}
    </span>
  );
}
function ErrorBanner() {
  const error = useStore((s) => s.error);
  const wakeError = useStore((s) => s.wakeError);
  const [expanded, setExpanded] = useState(false);
  if (!error || (isPet && error === wakeError)) return null;
  return (
    <>
      {isPet && expanded && <div className="error-detail" id="karen-error-detail" role="status">{error}</div>}
      <div className="error-banner" role="alert">
        <CircleHelp size={18} />
        <span title={error}>{error}</span>
        {isPet && <button aria-label="Ver error completo" aria-expanded={expanded} aria-controls="karen-error-detail" onClick={() => setExpanded(value => !value)}><ChevronRight size={16} /></button>}
        <button
          aria-label="Cerrar aviso"
          onClick={() => { setExpanded(false); useStore.setState({ error: "" }); }}
        >
          <X size={16} />
        </button>
      </div>
    </>
  );
}
function Toggle({
  label,
  description,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  description?: string;
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="setting-row">
      <div>
        <label>{label}</label>
        {description && <p>{description}</p>}
      </div>
      <button
        className="toggle"
        role="switch"
        aria-label={label}
        aria-checked={value}
        disabled={disabled}
        onClick={() => onChange(!value)}
      >
        <span />
      </button>
    </div>
  );
}
function Range({
  label,
  value,
  min,
  max,
  step = 0.05,
  onChange,
  unit = "",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  unit?: string;
}) {
  return (
    <div className="range-field">
      <label>
        {label}
        <output>
          {unit === "%"
            ? `${Math.round(value * 100)} %`
            : `${Math.round(value * 100) / 100}${unit}`}
        </output>
      </label>
      <input
        aria-label={label}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
function Group({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="group">
      <h2>{title}</h2>
      {description && <p className="group-description">{description}</p>}
      {children}
    </section>
  );
}
function PetPreview() {
  const [background, setBackground] = useState<'dark' | 'light'>('dark');
  const coreActivity = useStore(s => s.coreActivity);
  const style = useStore(s => s.settings.petStyle);
  const state = useStore((s) => s.state),
    reason = useStore((s) => s.reason),
    scale = useStore((s) => s.settings.scale);
  const gesture = (next: PetState) => {
    useStore.getState().transition(next, 'Demostración visual local');
    void action(() => bridge.demo(next));
  };
  return (
    <aside className="preview-pane">
      <div className="preview-window" data-background={background}>
        <PetRenderer preview />
        <div className="preview-state">
          <i />
          {labels[state]}
        </div>
      </div>
      <div className="preview-background" role="group" aria-label="Fondo de la vista previa">
        <span>Ver sobre</span>
        <button aria-pressed={background === 'dark'} onClick={() => setBackground('dark')}>Oscuro</button>
        <button aria-pressed={background === 'light'} onClick={() => setBackground('light')}>Claro</button>
      </div>
      <div className="preview-caption">
        <span>Karen</span><span className="preview-scale">{petStyles[style].name} · {Math.round(scale * 100)} %</span>
        <small>{reason || "Aquí contigo, a su ritmo."}</small>
        {coreActivity.map(client => <small key={client.interface}>Otra interfaz · {client.interface}: {client.state}</small>)}
      </div>
      <div className="preview-commands">
        <button onClick={() => gesture('HAPPY')}>
          <Sparkles size={16} />
          Saludar
        </button>
        <button
          onClick={() => gesture(state === 'SLEEPING' ? 'HAPPY' : 'SLEEPING')}
        >
          <Moon size={16} />
          {state === "SLEEPING" ? "Despertar" : "Reposar"}
        </button>
      </div>
      <p className="quiet-note">
        Vista en directo de tu mascota.
        <br />
        Arrástrala desde el escritorio para moverla.
      </p>
    </aside>
  );
}
const tabs: { name: string; icon: LucideIcon }[] = [
  { name: "Conversación", icon: MessageCircle },
  { name: "Iniciativa", icon: Bell },
  { name: "Apariencia", icon: Sparkles },
  { name: "Comportamiento", icon: SlidersHorizontal },
  { name: "OpenClaw", icon: Radio },
  { name: "Voz", icon: AudioLines },
  { name: "Percepción", icon: Monitor },
  { name: "Sistema", icon: Monitor },
  { name: "Diagnóstico", icon: Activity },
];
const subtitles: Record<string, string> = {
  Conversación: "Aquí para escucharte, pensar contigo y ayudarte.",
  Iniciativa: 'Cuándo puede hablarte y qué te ha sugerido.',
  Apariencia: "Luz, color y pequeños detalles.",
  Comportamiento: "Encuentra su ritmo en tu escritorio.",
  OpenClaw: "Tu asistente existente, conectado de forma segura.",
  Voz: "Escuchar, responder y dar vida a cada palabra.",
  Percepción: "Audio y pantalla, cuando tú decidas compartirlos.",
  Sistema: "Un pequeño espacio en Windows.",
  Diagnóstico: "Lo que está ocurriendo, sin secretos.",
};
function SettingsApp() {
  const tab = useStore((s) => s.tab),
    native = useStore((s) => s.native),
    runtime = useStore((s) => s.runtime),
    agent = useStore(s=>s.settings.agentId),
    mode = useStore(s=>s.settings.mode);
  return (
    <div className="app-shell">
      <nav className="sidebar" aria-label="Ajustes de Karen">
        <div className="brand">
          <Logo />
          <div>
            Karen<small>ASISTENTE PERSONAL</small>
          </div>
        </div>
        <div className="nav-links">
          {tabs.map(({ name, icon: Icon }) => (
            <React.Fragment key={name}>
            {['Conversación','Apariencia','OpenClaw'].includes(name)&&<span className="nav-section">{name==='Conversación'?'TU ESPACIO':name==='Apariencia'?'PERSONALIZA':'CONEXIONES Y SISTEMA'}</span>}
            <button
              key={name}
              className={tab === name ? "active" : ""}
              aria-current={tab === name ? "page" : undefined}
              onClick={() => useStore.setState({ tab: name })}
            >
              <Icon size={18} />
              {name}
              {tab === name && <ChevronRight size={14} />}
            </button>
            </React.Fragment>
          ))}
        </div>
        <div className="sidebar-foot">
          <Status compact />
          <span>Agente · {agent}</span>
          <small>
            Versión {APP_VERSION}
          </small>
        </div>
      </nav>
      <main className="workspace">
        <header className="page-header">
          <div>
            <span className="eyebrow">KAREN / {tab==='Conversación'?'CONTIGO':tab==='Iniciativa'?'COMPAÑÍA':'TU ASISTENTE'}</span>
            <h1>{tab}</h1>
            <p>{subtitles[tab]}</p>
          </div>
          <div className="header-actions"><select aria-label="Modo de Karen" value={mode} onChange={e=>void patch({mode:e.target.value as Settings['mode']})}>
            <option value="normal">Normal</option><option value="gaming">Gaming</option><option value="do_not_disturb">No molestar</option>
          </select><button
            className="icon-button"
            title="Volver a mostrar a Karen en el escritorio"
            aria-label="Mostrar mascota"
            onClick={() => void action(() => bridge.show())}
          >
            <Sparkles size={18} />
          </button>
          </div>
        </header>
        {!native && (
          <div className="browser-note">
            {runtime === "server"
              ? "Modo servidor · conexión de OpenClaw gestionada por tu administrador. Las funciones de escritorio y voz de Windows requieren el cliente nativo."
              : "Vista de navegador. Las funciones de Windows y OpenClaw están disponibles en la aplicación instalada."}
          </div>
        )}
        <ErrorBanner />
        <CaptureIndicator />
        <div
          className={`page-body ${tab === "Diagnóstico" ? "diagnostics-page" : ""} ${tab==='Conversación'?'conversation-page':''} ${tab==='Iniciativa'?'initiative-layout':''} ${tab==='Apariencia'?'appearance-page':''}`}
        >
          <div className="settings-content">
            {tab === "Conversación" ? (
              <Conversation />
            ) : tab === 'Iniciativa' ? (
              <InitiativePanel/>
            ) : tab === "Apariencia" ? (
              <Appearance />
            ) : tab === "Comportamiento" ? (
              <Behavior />
            ) : tab === "OpenClaw" ? (
              <OpenClaw />
            ) : tab === "Voz" ? (
              <Voice />
            ) : tab === "Percepción" ? (
              <Perception />
            ) : tab === "Sistema" ? (
              <System />
            ) : (
              <Diagnostics />
            )}
          </div>
          {['Apariencia','Comportamiento','Voz'].includes(tab) && <PetPreview />}
        </div>
      </main>
    </div>
  );
}
function Conversation() {
  const messages = useStore((s) => s.messages),
    connection = useStore((s) => s.connection),
    settings=useStore(s=>s.settings),
    capture=useStore(s=>s.capture),
    wakeStatus=useStore(s=>s.wakeStatus),
    initiative=useStore(s=>s.initiative),
    native=useStore(s=>s.native),
    draft=useStore(s=>s.conversationDraft);
  const [text, setText] = useState("");
  const editor=useRef<HTMLTextAreaElement>(null);
  const [sending,setSending]=useState(false);
  const latest=initiative?.notices.filter(n=>!n.dismissed).at(-1);
  const pending=messages.some(m=>m.pending);
  useEffect(()=>{if(draft){setText(draft);useStore.setState({conversationDraft:''});editor.current?.focus();}},[draft]);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if(messages.length)end.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);
  const send = async () => {
    const message = text;
    if (!canSendMessage(message,connection.state)||sending||pending) return;
    setSending(true);
    try {await bridge.send(message);setText(current=>current===message?'':current);}
    finally{setSending(false);}
  };
  return (
    <section className="conversation" data-has-suggestion={Boolean(latest)}>
      <div className="conversation-heading">
        <div className="companion-identity"><Logo/><div><h2>Karen</h2><span>{capture.phase==='recording'?'Te estoy escuchando':capture.phase==='speaking'?'Hablando contigo':capture.phase==='preparing'?'Preparando la voz':pending?'Pensando tu respuesta':'Tu asistente personal'}</span></div></div>
        <button className="voice-pill" onClick={()=>useStore.setState({tab:'Voz'})}><i className={wakeStatus==='listening'?'listening':''}/>{wakeStatus==='error'?'Escucha detenida':wakeStatus==='listening'?'Escucha activada':settings.voiceEnabled?'Voz activada':'Voz silenciada'}</button>
      </div>
      {latest&&<Notice notice={latest}/>}
      <ScreenActionApproval />
      <details className="conversation-model"><summary><span><Status compact/></span><span>Modelo y conexión</span></summary><ModelPicker/></details>
      <div className="messages" role="log" aria-label="Conversación con Karen">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-symbol">
              <Logo/>
            </div>
            <span className="eyebrow">UN ESPACIO PARA PENSAR JUNTOS</span><h3>¿Qué hacemos hoy?</h3>
            <p>
              {connection.state === "connected"
                ? "Escribe una idea, una pregunta o una tarea para tu asistente."
                : "Conecta tu Gateway de OpenClaw para empezar a conversar con Karen."}
            </p>
            {connection.state !== "connected" && (
              <button
                className="text-button"
                onClick={() => useStore.setState({ tab: "OpenClaw" })}
              >
                Revisar conexión
                <ChevronRight size={15} />
              </button>
            )}
            <div className="chat-starters" aria-label="Comenzar conversación">
              {[
                {label:'Ver mis tareas',text:'/tareas'},
                {label:'Retomar un chat',text:'/historial'},
                {label:'Que Karen tome la iniciativa',tab:'Iniciativa'},
              ].map(item=><button key={item.label} onClick={()=>{if(item.tab)useStore.setState({tab:item.tab});else{setText(item.text!);editor.current?.focus();}}}>{item.label}<ChevronRight size={14}/></button>)}
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <article key={m.id} className={`message ${m.role}`}>
              <span>
                {m.role === "user" ? "Tú" : "Karen"}
                {m.pending ? " · respondiendo" : ""}
              </span>
              <p>{m.text || (m.pending?'Preparando respuesta…':'')}</p>
            </article>
          ))
        )}
        <div ref={end} />
      </div>
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          void action(send);
        }}
      >
        <label className="sr-only" htmlFor="message">
          Mensaje para Karen
        </label>
        <textarea
          id="message"
          ref={editor}
          rows={2}
          maxLength={16000}
          value={text}
          placeholder={
            connection.state === "connected"
              ? "Habla con Karen…"
              : "Comandos Core disponibles; conecta OpenClaw para conversar…"
          }
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              void action(send);
            }
          }}
        />
        <div className="composer-actions">
          <button
            type="button"
            className="icon-button"
            title="Iniciar o terminar captura de voz"
            aria-label="Capturar voz"
            disabled={!native||!settings.sttEnabled}
            onClick={() => void action(() => bridge.listen())}
          >
            <Mic size={17} />
          </button>
          <button
            type="button"
            className="icon-button"
            title="Detener respuesta y voz"
            aria-label="Detener"
            onClick={() => void action(() => bridge.abort())}
          >
            <Square size={15} />
          </button>
          <small>Enter para enviar</small>
          <button
            className="send-button"
            aria-label="Enviar mensaje"
            disabled={sending||pending||!canSendMessage(text, connection.state)}
          >
            <ArrowUp size={19} />
          </button>
        </div>
      </form>
      <p className="quiet-note">
        Los comandos Core se consultan localmente. Las demás órdenes usan los permisos de OpenClaw.
      </p>
    </section>
  );
}
function Appearance() {
  const s = useStore((x) => x.settings);
  return (
    <>
      <Group title="Elige su forma" description="Ocho estilos, la misma Karen. Los cambios se guardan al elegir.">
        <StylePicker value={s.petStyle} arms={s.showArms} legs={s.showLegs} onChange={petStyle => void patch({petStyle})}/>
      </Group>
      <Group title="Su manera de moverse" description="Elige un ritmo y prueba el saludo en la vista previa.">
        <div className="presence-presets" role="group" aria-label="Ritmo de la mascota">
          {PRESENCE_PRESETS.map(preset => <button key={preset.name}
            aria-pressed={s.animations && Math.abs(s.activity - preset.activity) < .05}
            title={preset.description} onClick={() => void patch({activity: preset.activity, animations: true})}>
            <span className={`presence-mark ${preset.name === 'Serena' ? 'calm' : preset.name === 'Expresiva' ? 'lively' : 'balanced'}`} aria-hidden="true"><i/><i/><i/></span>
            {preset.name}
          </button>)}
        </div>
        <p className="quiet-note">Gaming, No molestar y movimiento reducido mantienen sus límites.</p>
      </Group>
      <Group title="Su silueta" description="Cada estilo puede tener brazos, piernas o flotar libremente.">
        <div className="size-presets" role="group" aria-label="Versiones de cuerpo">
          {[
            { name: 'Completa', arms: true, legs: true },
            { name: 'Sin brazos', arms: false, legs: true },
            { name: 'Flotante', arms: false, legs: false },
          ].map(preset => <button key={preset.name} aria-pressed={s.showArms === preset.arms && s.showLegs === preset.legs}
            onClick={() => void patch({showArms:preset.arms,showLegs:preset.legs})}>{preset.name}</button>)}
        </div>
        <Toggle label="Mostrar brazos" value={s.showArms} onChange={showArms => void patch({showArms})}/>
        <Toggle label="Mostrar piernas" value={s.showLegs} onChange={showLegs => void patch({showLegs})}/>
        <button onClick={() => void patch({showArms:false,showLegs:false})}>Ocultar brazos y piernas</button>
      </Group>
      <Group
        title="Tamaño del PET"
        description="Cambia al instante y se recuerda al volver a abrir Karen."
      >
        <Range
          label="Tamaño del PET"
          value={s.scale}
          min={PET_SCALE.min}
          max={PET_SCALE.max}
          unit="%"
          onChange={(scale) => void patch({ scale })}
        />
        <div className="size-presets" role="group" aria-label="Tamaños rápidos">
          {([{ label: "Pequeña", scale: 0.7 }, { label: "Normal", scale: 1 }, { label: "Grande", scale: 1.5 }] as const).map((preset) => (
            <button key={preset.label} aria-pressed={s.scale === preset.scale} onClick={() => void patch({ scale: preset.scale })}>
              {preset.label}<small>{Math.round(preset.scale * 100)} %</small>
            </button>
          ))}
        </div>
        <p className="quiet-note">50–200 %. Se ajusta al espacio disponible de tu monitor.</p>
      </Group>
      <Group title="Una luz propia" description="Ajusta su presencia sin perder la suavidad.">
        <Range
          label="Luminosidad"
          value={s.brightness}
          min={0.35}
          max={1.4}
          unit="%"
          onChange={(brightness) => void patch({ brightness })}
        />
        <Range
          label="Opacidad"
          value={s.opacity}
          min={0.35}
          max={1}
          unit="%"
          onChange={(opacity) => void patch({ opacity })}
        />
        <div className="color-row">
          <label htmlFor="accent">Tono holográfico</label>
          <div className="swatches">
            {["#8be4f3", "#b7b2f5", "#ade9d5", "#c9e8ff"].map((color) => (
              <button
                key={color}
                style={{ backgroundColor: color }}
                className={s.accent === color ? "selected" : ""}
                aria-label={`Color ${color}`}
                aria-pressed={s.accent === color}
                onClick={() => void patch({ accent: color })}
              >
                {s.accent === color && <Check size={15} />}
              </button>
            ))}
            <input
              id="accent"
              type="color"
              value={s.accent}
              onChange={(e) => void patch({ accent: e.target.value })}
            />
          </div>
        </div>
      </Group>
      <Group title="En el aire">
        <Toggle
          label="Partículas de luz"
          description="Pequeños destellos que acompañan sus movimientos."
          value={s.particles}
          onChange={(particles) => void patch({ particles })}
        />
        <Toggle
          label="Globos de diálogo"
          description="Muestra la respuesta sobre la mascota."
          value={s.bubbles}
          onChange={(bubbles) => void patch({ bubbles })}
        />
        <Toggle
          label="Modo nocturno"
          description="Una luz más tenue para las últimas horas."
          value={s.nightMode}
          onChange={(nightMode) => void patch({ nightMode })}
        />
      </Group>
    </>
  );
}
function Behavior() {
  const s = useStore((x) => x.settings);
  return (
    <>
      <Group title="Cuando tiene un rato libre" description="Juega con una luz, se estira o contempla estrellas. Se detiene cuando la necesitas.">
        <Toggle label="Entretenerse en reposo" value={s.idleActivities} onChange={idleActivities => void patch({idleActivities})}/>
        <div className="input-field">
          <label htmlFor="idle-activity">Actividad favorita</label>
          <select id="idle-activity" value={s.idleActivity} onChange={e => void patch({idleActivity:e.target.value as Settings['idleActivity']})}>
            <option value="variety">Un poco de todo</option><option value="play">Jugar con una luz</option>
            <option value="stretch">Estirarse</option><option value="stargaze">Mirar estrellas</option>
          </select>
        </div>
        <Range label="Comenzar tras estar libre" value={s.idleAfter} min={15} max={300} step={1} unit="s" onChange={idleAfter => void patch({idleAfter})}/>
        <p className="quiet-note">Respeta reposo, bajo consumo, No molestar y movimiento reducido.</p>
      </Group>
      <Group title="A su manera">
        <Toggle
          label="Movimiento orgánico"
          description="Respiración, flotación y pequeños gestos."
          value={s.animations}
          onChange={(animations) => void patch({ animations })}
        />
        <Toggle
          label="Seguir el cursor"
          description="Sus ojos acompañan suavemente tu movimiento."
          value={s.cursorTracking}
          onChange={(cursorTracking) => void patch({ cursorTracking })}
        />
        <Range
          label="Nivel de actividad"
          value={s.activity}
          min={0}
          max={1}
          unit="%"
          onChange={(activity) => void patch({ activity })}
        />
        <div className="input-field">
          <label htmlFor="sleep">Reposar después de</label>
          <select
            id="sleep"
            value={s.sleepAfter}
            onChange={(e) => void patch({ sleepAfter: Number(e.target.value) })}
          >
            <option value={30}>30 segundos</option>
            <option value={60}>1 minuto</option>
            <option value={180}>3 minutos</option>
            <option value={300}>5 minutos</option>
            <option value={900}>15 minutos</option>
            <option value={3600}>1 hora</option>
          </select>
        </div>
      </Group>
      <Group
        title="Sus expresiones"
        description="Demostración visual local. No genera eventos de OpenClaw."
      >
        <div className="state-grid">
          {PET_STATES.map((state) => (
            <button
              key={state}
              onClick={() => {
                useStore
                  .getState()
                  .transition(state, "Demostración visual local");
                void action(() => bridge.demo(state));
              }}
            >
              {labels[state]}
            </button>
          ))}
        </div>
      </Group>
    </>
  );
}
function OpenClaw() {
  const s = useStore((x) => x.settings),
    c = useStore((x) => x.connection),
    hasCredential = useStore((x) => x.hasCredential),
    diagnostics = useStore((x) => x.diagnostics);
  const [url, setUrl] = useState(s.gatewayUrl),
    [agent, setAgent] = useState(s.agentId),
    [token, setToken] = useState(""),
    [mode, setMode] = useState<"local" | "remote">(s.authSource === "stored" ? "remote" : "local"),
    [busy, setBusy] = useState(false);
  const isLocalAddress = (value: string) => {
    try { return ["localhost", "127.0.0.1", "[::1]"].includes(new URL(value).hostname); }
    catch { return false; }
  };
  const pairing = [...diagnostics].reverse().find(item => item.area === "OpenClaw" && item.message.includes("solicitud de vinculación"));
  const runtime = useStore((x) => x.runtime);
  if (runtime === "server")
    return (
      <Group
        title="Gateway del servidor"
        description="La dirección, el agente y los secretos se configuran mediante variables de entorno o archivos privados del administrador."
      >
        <Status />
        <ModelPicker />
        <dl className="service-list">
          <div>
            <dt>Gateway</dt>
            <dd>{s.gatewayUrl}</dd>
          </div>
          <div>
            <dt>Agente</dt>
            <dd>{s.agentId}</dd>
          </div>
          <div>
            <dt>Credencial</dt>
            <dd>
              {hasCredential ? "Disponible en el servidor" : "No configurada"}
            </dd>
          </div>
        </dl>
        <button onClick={() => void action(() => bridge.connect())}>
          <RefreshCw size={15} />
          Reconectar
        </button>
      </Group>
    );
  return (
    <>
      <Group title="Modelo para esta conversación"><ModelPicker /></Group>
      <Group title="Conectar Karen con OpenClaw" description="Elige dónde está tu Gateway. Karen usa tu instalación y tus permisos de OpenClaw.">
        <div className="gateway-status">
          <Radio size={21} />
          <div>
            <Status />
            <p>
              {c.version
                ? `Gateway ${c.version}`
                : "Protocolo oficial WebSocket v4"}
            </p>
          </div>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void action(async () => {
              setBusy(true);
              try {
                const gatewayUrl = mode === "local" && !isLocalAddress(url)
                  ? "ws://127.0.0.1:18789" : url.trim();
                const settings = await bridge.settings({ gatewayUrl, agentId: agent.trim(), authSource: mode === "local" ? "local" : "stored" });
                useStore.setState({ settings });
                setUrl(settings.gatewayUrl);
                if (mode === "remote" && token.trim()) {
                  await bridge.credential(token.trim());
                  setToken("");
                  useStore.setState({ hasCredential: true });
                }
                await bridge.connect();
              } finally { setBusy(false); }
            });
          }}
        >
          <div className="input-field">
            <label htmlFor="gateway-mode">¿Dónde está OpenClaw?</label>
            <select id="gateway-mode" value={mode} onChange={e => {
              const next = e.target.value as "local" | "remote";
              setMode(next);
              if (next === "local" && !isLocalAddress(url)) setUrl("ws://127.0.0.1:18789");
            }}>
              <option value="local">En este equipo</option>
              <option value="remote">En otro equipo</option>
            </select>
          </div>
          <div className="input-field">
            <label htmlFor="gateway">Dirección del Gateway</label>
            <input
              id="gateway"
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              spellCheck={false}
            />
            <p className="quiet-note">{mode === "local" ? "Normalmente ws://127.0.0.1:18789; se lee la credencial de OpenClaw en este equipo." : "Usa wss:// para un Gateway remoto. El token se cifra en tu cuenta Windows."}</p>
          </div>
          <div className="input-field">
            <label htmlFor="agent">Agente</label>
            <input
              id="agent"
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
              spellCheck={false}
            />
          </div>
          {mode === "remote" && <div className="input-field">
            <label htmlFor="token">Token del Gateway</label>
            <input id="token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} placeholder={hasCredential && s.authSource === "stored" && s.gatewayUrl === url ? "Ya guardado; déjalo vacío para conservarlo" : "Pega el token de tu Gateway"} required={s.authSource !== "stored" || !hasCredential || s.gatewayUrl !== url} />
          </div>}
          <div className="button-row">
            <button className="primary" type="submit" disabled={busy}>
              <RefreshCw size={15} />
              {busy ? "Conectando…" : "Guardar y conectar"}
            </button>
            <button
              type="button"
              onClick={() => void action(() => bridge.disconnect())}
            >
              Desconectar
            </button>
          </div>
        </form>
        {c.state === "action-required" && <div className="info-note" role="status">
          <strong>Puede faltar aprobar este dispositivo.</strong> En el equipo del Gateway, ejecuta <code>openclaw devices list</code>, comprueba que la solicitud sea de Karen y apruébala en OpenClaw. Después pulsa «Guardar y conectar».
          {pairing && <p>Detalle de la solicitud: {pairing.message}</p>}
        </div>}
        <p className="quiet-note">{mode === "local" ? "Karen lee ~/.openclaw/openclaw.json solo para el Gateway local." : "El token se almacena cifrado con DPAPI y nunca aparece en el PET."} La conexión solicita lectura y escritura de conversación.</p>
      </Group>
      <Group title="Permisos para actuar" description="Hay dos controles distintos: los permisos del agente en OpenClaw y la aprobación local de Windows para cada acción visual.">
        <dl className="service-list">
          <div><dt>Conexión de Karen</dt><dd>{c.state === 'connected' ? c.scopes?.join(', ') || 'Conectada; el Gateway no comunicó los scopes.' : c.message}</dd></div>
          <div><dt>Herramientas del agente</dt><dd>Las define OpenClaw en el agente y su equipo anfitrión. Karen no puede habilitarlas ni ampliarlas desde esta pantalla.</dd></div>
          <div><dt>Clic y escritura en la pantalla</dt><dd>Solo desde una captura reciente y después de aprobar la acción exacta en Conversación. Sin comandos, ejecución en segundo plano ni permiso permanente.</dd></div>
        </dl>
        <p className="quiet-note">Si esperabas que OpenClaw use archivos, navegador o terminal, revisa las herramientas y reglas de aprobación de tu agente en OpenClaw. Los scopes de conversación de esta conexión no conceden por sí solos permisos de Windows.</p>
      </Group>
    </>
  );
}
function Voice() {
  const s = useStore((x) => x.settings);
  const wakeError = useStore((x) => x.wakeError);
  const runtime = useStore((x) => x.runtime);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]),
    [health, setHealth] = useState(
      "Consulta los motores para comprobar su disponibilidad.",
    );
  useEffect(() => {
    let alive = true;
    if (runtime === "desktop") void bridge.voiceHealth().then(value => { if (alive) setHealth(value); }).catch(report);
    return () => { alive = false; };
  }, [s.voiceRoot, s.ttsEngine, runtime]);
  useEffect(() => {
    void navigator.mediaDevices
      ?.enumerateDevices()
      .then(setDevices)
      .catch(report);
  }, []);
  return (
    <>
      {runtime === "server" && (
        <p className="info-note">
          Modo servidor: conversación de texto y animaciones. TTS/STT no están
          configurados. La voz de Windows pertenece al cliente nativo.
        </p>
      )}
      <Group title="La voz de Karen">
        <button disabled={runtime !== "desktop"} onClick={() => void action(async () => { const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false }); stream.getTracks().forEach(track => track.stop()); setDevices(await navigator.mediaDevices.enumerateDevices()); })}>Actualizar dispositivos de audio</button>
        <p className="quiet-note">Abre y cierra brevemente el micrófono para que Windows muestre los nombres de los dispositivos.</p>
        <Toggle
          label="Leer las respuestas"
          description="Reproduce audio real y sincroniza la boca con su energía."
          value={s.voiceEnabled}
          onChange={(voiceEnabled) => void patch({ voiceEnabled })}
        />
        <button disabled={runtime !== "desktop" || !s.voiceEnabled} onClick={() => void action(() => bridge.testVoice())}>Probar voz de Karen</button>
        <div className="input-field">
          <label htmlFor="tts">Motor de voz</label>
          <select
            id="tts"
            value={s.ttsEngine}
            onChange={(e) =>
              void patch({ ttsEngine: e.target.value as Settings["ttsEngine"] })
            }
          >
            <option value="system">Voz instalada en Windows</option>
            <option value="local">Voz original compartida de Karen</option>
            <option value="fast">Rápida local · Kokoro (otro timbre)</option>
            <option value="edge">Natural rápida · Dalia (en línea)</option>
          </select>
        </div>
        {s.ttsEngine === "local" && <p className="quiet-note">Usa el mismo perfil fijo que Karen Local y WhatsApp. Se inicia al hablar; si no está disponible, muestra un error sin sustituir la voz.</p>}
        {s.ttsEngine === 'fast' && <p className="quiet-note">Prioriza rapidez con Kokoro en CPU. Usa otro timbre fijo; no es la referencia original de WhatsApp. Requiere tus modelos locales de Kokoro.</p>}
        {s.ttsEngine === 'edge' && <p className="quiet-note">Voz femenina neural en español de México. Necesita internet; si falla, conserva la respuesta escrita.</p>}
        <div className="input-field">
          <label htmlFor="voice-style">Estilo de la voz original</label>
          <select id="voice-style" value={s.voiceStyle} disabled={s.ttsEngine === 'system' || s.ttsEngine === 'edge'} onChange={e => void patch({voiceStyle:e.target.value as Settings['voiceStyle']})}>
            <option value="serene">Serena · madura y pausada</option>
            <option value="warm">Cercana · cálida</option>
            <option value="serious">Seria · sobria</option>
            <option value="bright">Alegre · ligera</option>
            <option value="wry">Ironía suave · pausada</option>
            <option value="neutral">Original · sin ajustar</option>
          </select>
          <p className="quiet-note">Ajusta ritmo y tono conservando el perfil. La intención emocional y el sarcasmo dependen del texto del asistente.</p>
        </div>
        <Range
          label="Volumen"
          value={s.volume}
          min={0}
          max={1}
          unit="%"
          onChange={(volume) => void patch({ volume })}
        />
        <div className="input-field">
          <label htmlFor="output">Dispositivo de salida</label>
          <select
            id="output"
            value={s.outputDevice}
            onChange={(e) => void patch({ outputDevice: e.target.value })}
          >
            <option value="">Predeterminado de Windows</option>
            {devices
              .filter((d) => d.kind === "audiooutput" && d.deviceId)
              .map((d, i) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || `Salida ${i + 1}`}
                </option>
              ))}
          </select>
        </div>
        <button
          onClick={() => void action(() => bridge.demo("SPEAKING"))}
          className="text-button"
        >
          <AudioLines size={16} />
          Ver expresión de habla sin audio
        </button>
      </Group>
      <Group title="Escucharte, cuando tú decidas">
        <p className="quiet-note">Recursos: {s.voiceRoot || "Directorio de voz de la aplicación / KAREN_PROJECT_ROOT"}</p>
        <button disabled={runtime !== "desktop"} onClick={() => void action(async () => { await bridge.chooseVoiceRoot(); setHealth(await bridge.voiceHealth()); })}>Elegir carpeta de recursos de voz</button>
        <Toggle
          label="Reconocimiento local de voz"
          description="Se activa con el botón de micrófono. Usa faster-whisper de Karen."
          value={s.sttEnabled}
          onChange={(sttEnabled) => void patch({ sttEnabled })}
        />
        <button disabled={runtime !== "desktop" || !s.sttEnabled} onClick={() => void action(() => bridge.listen())}>Iniciar o finalizar micrófono</button>
        <Toggle label="Activar al decir Karen o Caren" description="Escucha local continua mientras está activado. Solo una frase dirigida a Karen/Caren envía la orden; se pausa al hablar y al capturar el PC." value={s.wakeWordEnabled} disabled={runtime !== 'desktop' || !s.sttEnabled} onChange={wakeWordEnabled => void patch({wakeWordEnabled})} />
        {wakeError && <div className="info-note" role="status">
          <p>{wakeError}</p>
          <button disabled={runtime !== 'desktop'} onClick={() => void action(async () => {
            await bridge.settings({wakeWordEnabled:false});
            await bridge.settings({wakeWordEnabled:true});
          })}>Reintentar escucha</button>
        </div>}
        <div className="input-field">
          <label htmlFor="input">Micrófono</label>
          <select
            id="input"
            value={s.inputDevice}
            onChange={(e) => void patch({ inputDevice: e.target.value })}
          >
            <option value="">Predeterminado de Windows</option>
            {s.inputDevice && !devices.some(d => d.kind === 'audioinput' && d.deviceId === s.inputDevice) &&
              <option value={s.inputDevice}>Micrófono guardado · pendiente de verificar</option>}
            {devices
              .filter((d) => d.kind === "audioinput" && d.deviceId)
              .map((d, i) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label || `Micrófono ${i + 1}`}
                </option>
              ))}
          </select>
        </div>
        <Range
          label="Sensibilidad visual"
          value={s.sensitivity}
          min={0.2}
          max={5}
          step={0.1}
          onChange={(sensitivity) => void patch({ sensitivity })}
        />
        <p className="info-note">
          La captura se detiene antes de reproducir voz. Un segundo clic
          finaliza la captura; Detener cancela la operación.
        </p>
        <p className="quiet-note">
          La activación usa transcripción local de fragmentos con voz. Puede
          confundirse con ruido o voces de fondo; no identifica al hablante.
        </p>
      </Group>
      <Group title="Disponibilidad">
        <button
          onClick={() =>
            void action(async () => setHealth(await bridge.voiceHealth()))
          }
        >
          <RefreshCw size={15} />
          Consultar motores
        </button>
        <p className="quiet-note">{health}</p>
      </Group>
    </>
  );
}
function System() {
  const s = useStore((x) => x.settings);
  const runtime = useStore((x) => x.runtime);
  if (runtime === "server")
    return (
      <Group
        title="Servidor y navegador"
        description="La mascota vive en esta pestaña. Bandeja, arrastre entre monitores e inicio con Windows pertenecen al cliente nativo."
      >
        <Toggle
          label="Modo de bajo consumo"
          value={s.lowPower}
          onChange={(lowPower) => void patch({ lowPower })}
        />
      </Group>
    );
  return (
    <>
      <Group title="Modo de funcionamiento" description="Se aplica mientras esté seleccionado; conserva tus ajustes normales.">
        <div className="input-field">
          <label htmlFor="pet-mode">Modo activo</label>
          <select id="pet-mode" value={s.mode} onChange={e => void patch({mode: e.target.value as Settings['mode']})}>
            <option value="normal">Normal</option>
            <option value="gaming">Gaming</option>
            <option value="do_not_disturb">No molestar</option>
          </select>
        </div>
        <p className="quiet-note">Gaming reduce animación, partículas y overlays; conserva la voz configurada. No molestar también pausa escucha y voz automáticas. No detecta juegos ni cambia Windows.</p>
      </Group>
      <Group title="En tu escritorio">
        <Toggle
          label="Iniciar con Windows"
          description="Karen aparece al entrar en tu cuenta, después de instalarla."
          value={s.autoStart}
          onChange={(autoStart) => void patch({ autoStart })}
        />
        <Toggle
          label="Siempre visible"
          description="Mantiene la mascota por encima de otras ventanas."
          value={s.alwaysOnTop}
          onChange={(alwaysOnTop) => void patch({ alwaysOnTop })}
        />
        <Toggle
          label="Modo de bajo consumo"
          description="15 FPS y sin partículas; reposo automático a 15 FPS."
          value={s.lowPower}
          onChange={(lowPower) => void patch({ lowPower })}
        />
      </Group>
      <Group title="Pequeña, pero a mano">
        <div className="shortcut">
          <span>Recuperar control</span>
          <kbd>Ctrl</kbd>
          <kbd>Alt</kbd>
          <kbd>K</kbd>
        </div>
        <p className="quiet-note">
          El atajo vuelve a mostrar a Karen y desactiva «Ignorar clics». También
          puedes usar su icono en la bandeja de Windows.
        </p>
        <div className="button-row">
          <button onClick={() => void action(() => bridge.hide())}>
            <EyeOff size={16} />
            Ocultar en la bandeja
          </button>
        </div>
        <p className="info-note">
          Clic derecho sobre Karen: menú de escritorio. Doble clic: ajustes. Los
          espacios transparentes dejan pasar los clics.
        </p>
      </Group>
      <Group title="Rendimiento">
        <p className="quiet-note">
          El renderizado usa texturas locales, limita la densidad a 2×, reduce
          partículas si caen los FPS y se pausa al ocultarse. La prioridad del
          proceso permanece normal.
        </p>
      </Group>
    </>
  );
}
function Diagnostics() {
  const c = useStore((x) => x.connection),
    d = useStore((x) => x.diagnostics),
    native = useStore((x) => x.native);
  const runtime = useStore((x) => x.runtime);
  return (
    <>
      <Group title="Estado de los servicios">
        <dl className="service-list">
          <div>
            <dt>Aplicación de Windows</dt>
            <dd>
              {native
                ? "Proceso nativo disponible"
                : runtime === "server"
                  ? "Servidor Node disponible"
                  : "Vista de navegador"}
            </dd>
          </div>
          <div>
            <dt>OpenClaw Gateway</dt>
            <dd>
              <Status compact />
            </dd>
          </div>
          <div>
            <dt>Versión del Gateway</dt>
            <dd>{c.version || "Aún no autenticado"}</dd>
          </div>
          <div>
            <dt>Permisos de la conexión</dt>
            <dd>{c.scopes?.join(", ") || "No negociados"}</dd>
          </div>
          <div>
            <dt>Micrófono</dt>
            <dd>Solo tras activación explícita</dd>
          </div>
          <div>
            <dt>Palabra clave</dt>
            <dd>Sin detector configurado</dd>
          </div>
        </dl>
        <div className="button-row">
          <button onClick={() => void action(() => bridge.connect())}>
            <RefreshCw size={15} />
            Reconectar
          </button>
          <button onClick={() => useStore.setState({ tab: "Voz" })}>
            <Volume2 size={15} />
            Comprobar voz
          </button>
        </div>
      </Group>
      <Group
        title="Registro de esta sesión"
        description="Eventos técnicos reales. No se guardan mensajes, audio ni credenciales en este registro."
      >
        <div className="diagnostic-log" role="log">
          {d.length ? (
            d.map((item, i) => (
              <div
                className={`diagnostic ${item.level}`}
                key={`${item.time}-${i}`}
              >
                <time>{new Date(item.time).toLocaleTimeString("es")}</time>
                <b>{item.area}</b>
                <p>{item.message}</p>
              </div>
            ))
          ) : (
            <p className="quiet-note">Aún no hay eventos de diagnóstico.</p>
          )}
        </div>
      </Group>
    </>
  );
}
function PetApp() {
  const s = useStore((x) => x.settings),
    state = useStore((x) => x.state),
    messages = useStore((x) => x.messages),
    connection = useStore((x) => x.connection),
    capture = useStore((x) => x.capture),
    error = useStore((x) => x.error),
    native = useStore((x) => x.native),
    initiative = useStore(x=>x.initiative);
  const [bubble, setBubble] = useState(false),
    [compose, setCompose] = useState(false),
    [text, setText] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; started: boolean } | null>(null);
  const last = messages.filter((m) => m.role === "assistant").at(-1);
  const showReply = Boolean(effectiveSettings(s).bubbles && bubble && last && !compose && !error);
  const voiceActive = capture.kind === 'voice' && capture.phase !== 'idle';
  const latestNotice=initiative?.notices.filter(n=>!n.dismissed).at(-1);
  const showInitiative=Boolean(latestNotice && Date.now()-latestNotice.at<120000 && !showReply && !compose && !error && s.mode==='normal');
  useEffect(() => {
    if (last) setBubble(true);
  }, [last?.text]);
  useEffect(() => {
    if (!bubble || voiceActive) return;
    const timer = setTimeout(() => setBubble(false), 16000);
    return () => clearTimeout(timer);
  }, [bubble, last?.text, voiceActive]);
  useEffect(() => {
    const check = (x: number, y: number) => {
      const r = root.current?.getBoundingClientRect();
      if (!r) return;
      const silhouette = signals.hitTest?.(x, y) ?? false;
      const target = document.elementFromPoint(x, y);
      bridge.hitTest(
        silhouette ||
          Boolean(
            target?.closest(
              ".pet-bubble,.pet-initiative,.pet-toolbar,.pet-composer,.pet-error,.capture-status",
            ),
          ),
      );
    };
    const move = (e: MouseEvent) => check(e.clientX, e.clientY);
    document.addEventListener("mousemove", move);
    const off = bridge.event((e) => {
      if (e.type === "cursor") check(e.x * innerWidth, e.y * innerHeight);
    });
    return () => {
      document.removeEventListener("mousemove", move);
      off();
    };
  }, []);
  return (
    <div
      ref={root}
      className="desktop-pet"
      data-capturing={capture.phase !== "idle"}
      data-has-dock={showReply || showInitiative || Boolean(error)}
      onContextMenu={(e) => {
        e.preventDefault();
        void action(() => bridge.contextMenu());
      }}
    >
      <PetRenderer />
      <div className="pet-dialogue">
        <CaptureIndicator />
      </div>
      {showInitiative&&latestNotice&&<div className="pet-initiative"><Notice notice={latestNotice} compact/></div>}
      {showReply && last && (
        <div
          className="pet-bubble"
          role="status"
        >
          <button className="pet-bubble-open" aria-label="Abrir respuesta completa en Conversación" onClick={() => void bridge.openSettings()}>
            <span>{last.text.slice(0, 240)}{last.text.length > 240 ? "…" : ""}</span>
          </button>
          <button aria-label="Cerrar globo" onClick={() => setBubble(false)}>
            <X size={12} />
          </button>
        </div>
      )}
      <button
        className="pet-hit-area"
        aria-label={`Karen: ${labels[state]}. Arrastra para mover, doble clic para ajustes.`}
        onDoubleClick={() => void action(() => bridge.openSettings())}
        onPointerDown={(e) => {
          if (e.button !== 0) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.current = { x: e.screenX, y: e.screenY, started: false };
        }}
        onPointerMove={(e) => {
          if (
            drag.current &&
            !drag.current.started &&
            Math.hypot(e.screenX - drag.current.x, e.screenY - drag.current.y) >
              4
          ) {
            drag.current.started = true;
            useStore.getState().transition("DRAGGING");
            bridge.drag("start");
          }
        }}
        onPointerUp={() => {
          if (drag.current?.started) {
            bridge.drag("end");
            useStore.getState().transition("HAPPY");
          } else {
            useStore.getState().transition("HAPPY", "Un pequeño saludo");
          }
          drag.current = null;
        }}
        onLostPointerCapture={() => {
          if (drag.current?.started) bridge.drag("end");
          drag.current = null;
        }}
      />
      <div className="pet-toolbar">
        <button title="Mostrar u ocultar brazos y piernas" aria-label="Mostrar brazos y piernas"
          aria-pressed={s.showArms && s.showLegs}
          onClick={() => void patch({showArms:!(s.showArms && s.showLegs),showLegs:!(s.showArms && s.showLegs)})}>
          <PersonStanding size={16}/>
        </button>
        <button
          title="Conversar"
          aria-label="Abrir mensaje"
          onClick={() => setCompose(!compose)}
        >
          <MessageCircle size={16} />
        </button>
        <button
          title="Hablar ahora; interrumpe a Karen"
          aria-label="Hablar ahora o terminar dictado"
          aria-pressed={capture.kind === "microphone" && capture.phase === "recording"}
          disabled={!native || !s.sttEnabled}
          onClick={() => void action(() => bridge.listen())}
        >
          <Mic size={16} />
        </button>
        <button
          title={s.voiceEnabled ? "Silenciar respuestas habladas" : "Activar respuestas habladas"}
          aria-label="Leer respuestas"
          aria-pressed={s.voiceEnabled}
          disabled={!native}
          onClick={() => void patch({ voiceEnabled: !s.voiceEnabled })}
        >
          {s.voiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
        <button
          title="Repetir la última respuesta sin consultar al modelo"
          aria-label="Repetir última respuesta"
          disabled={!native || !s.voiceEnabled || !last || last.pending || capture.phase !== "idle"}
          onClick={() => void action(async () => { if (last && audio) { replies?.clear(); await audio.speak(last.text); } })}
        >
          <RotateCcw size={15} />
        </button>
        <button
          title="Detener"
          aria-label="Detener respuesta y voz"
          onClick={() => void action(() => bridge.abort())}
        >
          <Square size={13} />
        </button>
        <button
          title="Ajustes"
          aria-label="Abrir ajustes"
          onClick={() => void action(() => bridge.openSettings())}
        >
          <SettingsIcon size={16} />
        </button>
      </div>
      <div className="pet-caption">
        <span>{state === "IDLE" ? "Karen" : labels[state]}</span>
        <i className={connection.state} />
      </div>
      {compose && (
        <form
          className="pet-composer"
          onSubmit={(e) => {
            e.preventDefault();
            void action(async () => {
              await bridge.send(text);
              setText("");
              setCompose(false);
            });
          }}
        >
          <input
            autoFocus
            aria-label="Mensaje para Karen"
            value={text}
            maxLength={16000}
            onChange={(e) => setText(e.target.value)}
            placeholder="Dile algo a Karen…"
          />
          <button
            aria-label="Enviar"
            disabled={!canSendMessage(text, connection.state)}
          >
            <ArrowUp size={18} />
          </button>
          <button
            type="button"
            aria-label="Cerrar mensaje"
            onClick={() => setCompose(false)}
          >
            <X size={16} />
          </button>
        </form>
      )}
      <div className="pet-error">
        <ErrorBanner />
      </div>
    </div>
  );
}
function Root() {
  const ready = useStore(s => s.ready);
  const runtime = useStore(s => s.runtime);
  const wakeEnabled = useStore(s => effectiveSettings(s.settings).wakeWordEnabled);
  const sttEnabled = useStore(s => s.settings.sttEnabled);
  const inputDevice = useStore(s => s.settings.inputDevice);
  const sensitivity = useStore(s => s.settings.sensitivity);
  useEffect(() => {
    if (audio && ready) void audio.configureWake(runtime === 'desktop' && wakeEnabled && sttEnabled, inputDevice, sensitivity).catch(report);
  }, [ready, runtime, wakeEnabled, sttEnabled, inputDevice, sensitivity]);
  useEffect(() => {
    let alive = true;
    let connectionSeen = false;
    let settingsSeen = false;
    let captureSeen = false;
    let wakeSeen = false;
    let initiativeSeen = false;
    const off = bridge.event((e) => {
      if (e.type === "connection") connectionSeen = true;
      if (e.type === "settings") settingsSeen = true;
      if (e.type === "capture") captureSeen = true;
      if (e.type === 'wake-status') wakeSeen = true;
      if (e.type === 'initiative') initiativeSeen = true;
      useStore.getState().event(e);
      if (e.type === 'capture' && e.status.kind === 'system') audio?.suspendWake(e.status.phase !== 'idle');
      if (
        e.type === "chat" &&
        e.final && e.speak !== false
      ) {
        replies?.enqueue(e.message);
      }
      if (e.type === "capture" && e.status.phase === "idle") replies?.resume();
      if (e.type === "voice-cancel") { replies?.clear(); audio?.cancel(); }
      if (e.type === "voice-listen") void audio?.toggleListening();
      if (e.type === "voice-speak") void audio?.speak(e.text);
      if (e.type === "settings" && !effectiveSettings(e.settings).voiceEnabled) { replies?.clear(); audio?.cancel(); }
    });
    void bridge
      .snapshot()
      .then((snapshot) => {
        if (alive)
          useStore.setState({
            settings: settingsSeen
              ? useStore.getState().settings
              : snapshot.settings,
            connection: connectionSeen
              ? useStore.getState().connection
              : snapshot.connection,
            diagnostics: snapshot.diagnostics,
            messages: mergeMessages(
              snapshot.messages,
              useStore.getState().messages,
            ),
            native: snapshot.native,
            runtime:
              snapshot.runtime || (snapshot.native ? "desktop" : "preview"),
            hasCredential: snapshot.hasCredential,
            ready: true,
            initiative: initiativeSeen ? useStore.getState().initiative : snapshot.initiative,
            capture: captureSeen ? useStore.getState().capture : snapshot.capture || { kind: "microphone", phase: "idle" },
            wakeStatus: wakeSeen ? useStore.getState().wakeStatus : snapshot.wakeStatus || 'off',
            wakeError: wakeSeen ? useStore.getState().wakeError : snapshot.wakeError || '',
          });
      })
      .catch(report);
    const timer = setInterval(() => {
      const current = useStore.getState();
      const next = machine.tick(current.settings.sleepAfter);
      if (next.state !== current.state)
        useStore.setState({ state: next.state });
    }, 1000);
    let lastTouch=0;
    const touch=()=>{
      machine.touch();
      if(Date.now()-lastTouch>1000){lastTouch=Date.now();bridge.interaction?.();}
    };
    document.addEventListener('keydown',touch,{passive:true});
    document.addEventListener('pointerdown',touch,{passive:true});
    return () => {
      document.removeEventListener('keydown',touch);
      document.removeEventListener('pointerdown',touch);
      alive = false;
      off();
      clearInterval(timer);
      replies?.clear();
      audio?.dispose();
    };
  }, []);
  return isPet ? <PetApp /> : <SettingsApp />;
}
createRoot(document.getElementById("root")!).render(<Root />);
