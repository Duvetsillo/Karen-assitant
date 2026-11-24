import { Keyboard, MousePointer2, ShieldCheck, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { ScreenActionProposal } from '../shared/types';
import { bridge } from './native';
import { report, useStore } from './state/store';

export function ScreenActionApproval() {
  const proposal = useStore(state => state.screenActionProposal);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!proposal) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [proposal?.id]);
  if (!proposal) return null;
  const seconds = Math.max(0, Math.ceil((proposal.expiresAt - now) / 1000));
  const expired = seconds === 0;
  const actionLabel = proposal.kind === 'click' ? 'Hacer un clic' : 'Hacer clic y escribir';
  const approve = async (value: ScreenActionProposal) => {
    setBusy(true);
    try { await bridge.approveScreenAction(value.id); }
    catch (error) { report(error); }
    finally { setBusy(false); }
  };
  const cancel = async (value: ScreenActionProposal) => {
    try { await bridge.cancelScreenAction(value.id); }
    catch (error) { report(error); }
  };
  return <section className="screen-action-approval" aria-labelledby="screen-action-title">
    <div className="screen-action-heading">
      <span className="screen-action-icon">{proposal.kind === 'click' ? <MousePointer2 size={18}/> : <Keyboard size={18}/>}</span>
      <div><h3 id="screen-action-title">Karen encontró un objetivo</h3><p>Windows espera tu aprobación · {expired ? 'propuesta vencida' : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`}</p></div>
      <ShieldCheck size={18} aria-label="Aprobación necesaria"/>
    </div>
    <p className="screen-action-target">{actionLabel} en <strong>{proposal.target}</strong></p>
    {proposal.kind === 'type' && <div className="screen-action-text"><span>Texto exacto que se enviará</span><q>{proposal.text}</q></div>}
    <p className="screen-action-limit">Solo hará esta acción en la pantalla capturada. No ejecutará comandos ni repetirá el clic.</p>
    <div className="screen-action-buttons">
      <button type="button" disabled={busy} onClick={() => void cancel(proposal)}><X size={15}/>Cancelar</button>
      <button type="button" className="primary" disabled={busy || expired} onClick={() => void approve(proposal)}><ShieldCheck size={15}/>{busy ? 'Aplicando…' : expired ? 'Captura otra pantalla' : 'Aprobar acción'}</button>
    </div>
  </section>;
}
