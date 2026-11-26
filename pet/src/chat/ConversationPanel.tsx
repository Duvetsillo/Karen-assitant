import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { ArrowDown, ArrowUp, ChevronRight, Mic, Square } from 'lucide-react';
import { canSendMessage } from '../../shared/local-commands';
import { bridge } from '../native';
import { report, useStore } from '../state/store';
import { Notice } from '../InitiativePanel';
import { ScreenActionApproval } from '../ScreenActionApproval';
import { ModelPicker } from '../ModelPicker';
import { MessageBubble } from './MessageBubble';

const commands = [
  { label: 'Mis tareas', text: '/tareas' },
  { label: 'Mi historial', text: '/historial' },
  { label: 'Mi memoria', text: '/memoria' },
];

export function ConversationPanel({ logo, status }: { logo: ReactNode; status: ReactNode }) {
  const messages = useStore(s => s.messages), connection = useStore(s => s.connection), settings = useStore(s => s.settings),
    capture = useStore(s => s.capture), wakeStatus = useStore(s => s.wakeStatus), native = useStore(s => s.native),
    initiative = useStore(s => s.initiative), draft = useStore(s => s.conversationDraft), text = useStore(s => s.chatDraft);
  const [sending, setSending] = useState(false), [visibleCount, setVisibleCount] = useState(40), [away, setAway] = useState(false);
  const editor = useRef<HTMLTextAreaElement>(null), viewport = useRef<HTMLDivElement>(null);
  const follow = useRef(true), anchor = useRef<number | undefined>(undefined);
  const pending = messages.some(m => m.pending), latest = initiative?.notices.filter(n => !n.dismissed).at(-1);
  const setText = (value: string) => useStore.setState({ chatDraft: value });
  useEffect(() => {
    if (draft) { useStore.setState({ chatDraft: draft, conversationDraft: '' }); editor.current?.focus(); }
  }, [draft]);
  useLayoutEffect(() => {
    const view = viewport.current;
    if (!view) return;
    if (anchor.current !== undefined) { view.scrollTop += view.scrollHeight - anchor.current; anchor.current = undefined; }
    else if (follow.current) view.scrollTop = view.scrollHeight;
  }, [messages, visibleCount]);
  const fill = (value: string) => { setText(value); editor.current?.focus(); };
  const send = async () => {
    if (!canSendMessage(text, connection.state) || sending || pending) return;
    const message = text;
    setSending(true);
    try {
      await bridge.send(message);
      if (useStore.getState().chatDraft === message) setText('');
      follow.current = true; setAway(false);
      const view = viewport.current; if (view) view.scrollTop = view.scrollHeight;
    } catch (error) { report(error); }
    finally { setSending(false); }
  };
  return <section className="conversation" data-has-suggestion={Boolean(latest)}>
    <div className="conversation-heading">
      <div className="companion-identity">{logo}<div><h2>Karen</h2><span>{capture.phase === 'recording' ? 'Te estoy escuchando' : capture.phase === 'speaking' ? 'Hablando contigo' : capture.phase === 'preparing' ? 'Preparando la voz' : pending ? 'Pensando tu respuesta' : 'Tu asistente personal'}</span></div></div>
      <button className="voice-pill" onClick={() => useStore.setState({ tab: 'Voz' })}><i className={wakeStatus === 'listening' ? 'listening' : ''}/>{wakeStatus === 'listening' ? 'Escucha activada' : settings.voiceEnabled ? 'Voz activada' : 'Voz silenciada'}</button>
    </div>
    {latest && <Notice notice={latest}/>}<ScreenActionApproval/>
    <details className="conversation-model"><summary><span>{status}</span><span>Modelo y conexión</span></summary><ModelPicker/></details>
    <div ref={viewport} className="messages" role="log" aria-label="Conversación con Karen" onScroll={event => {
      const view = event.currentTarget; follow.current = view.scrollHeight - view.scrollTop - view.clientHeight < 70;
      setAway(!follow.current);
    }}>
      {messages.length > visibleCount && <button className="load-messages" onClick={() => { anchor.current = viewport.current?.scrollHeight; setVisibleCount(n => n + 40); }}>Ver mensajes anteriores</button>}
      {!messages.length ? <div className="empty-chat">
        <div className="empty-symbol">{logo}</div><span className="eyebrow">UN ESPACIO PARA PENSAR JUNTOS</span><h3>¿Qué hacemos hoy?</h3>
        <p>{connection.state === 'connected' ? 'Escribe una idea, una pregunta o una tarea. Empezamos por ahí.' : 'Puedes consultar tus datos Core. Para conversar, conecta tu Gateway de OpenClaw.'}</p>
        {connection.state !== 'connected' && <button className="text-button" onClick={() => useStore.setState({ tab: 'OpenClaw' })}>Revisar conexión<ChevronRight size={15}/></button>}
        <div className="chat-starters" aria-label="Comenzar conversación">{commands.slice(0, 2).map(item => <button key={item.text} onClick={() => fill(item.text)}>{item.label}<ChevronRight size={14}/></button>)}<button onClick={() => useStore.setState({ tab: 'Iniciativa' })}>Sugerencias de Karen<ChevronRight size={14}/></button></div>
      </div> : messages.slice(-visibleCount).map(message => <MessageBubble key={message.id} message={message}/>)}
    </div>
    {away && <button className="jump-latest" onClick={() => { follow.current = true; setAway(false); if (viewport.current) viewport.current.scrollTop = viewport.current.scrollHeight; }}><ArrowDown size={14}/>Volver al final</button>}
    <form className="composer" onSubmit={event => { event.preventDefault(); void send(); }}>
      <label className="sr-only" htmlFor="message">Mensaje para Karen</label>
      <textarea id="message" ref={editor} rows={2} maxLength={16000} value={text}
        placeholder={connection.state === 'connected' ? 'Habla con Karen…' : 'Consulta /tareas, /historial o /memoria…'}
        onChange={event => setText(event.target.value)} onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send(); }
        }}/>
      <div className="composer-actions">
        <button type="button" className="icon-button" aria-label="Capturar voz" title="Iniciar o terminar captura de voz" disabled={!native || !settings.sttEnabled} onClick={() => void bridge.listen().catch(report)}><Mic size={17}/></button>
        <button type="button" className="icon-button" aria-label="Detener" title="Detener respuesta y voz" onClick={() => void bridge.abort().catch(report)}><Square size={15}/></button>
        <small>Enter envía · Shift+Enter nueva línea</small><button className="send-button" aria-label="Enviar mensaje" disabled={sending || pending || !canSendMessage(text, connection.state)}><ArrowUp size={19}/></button>
      </div>
    </form>
    <div className="conversation-footer"><details className="quick-commands"><summary>Accesos rápidos</summary><div>{commands.map(item => <button key={item.text} onClick={() => fill(item.text)}>{item.label}<code>{item.text}</code></button>)}</div></details><span>Los comandos Core se consultan localmente.</span></div>
  </section>;
}
