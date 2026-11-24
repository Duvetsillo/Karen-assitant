import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { bridge } from './native';
import { useStore } from './state/store';

export function ModelPicker() {
  const id = useId();
  const connection = useStore(s => s.connection.state);
  const gateway = useStore(s => s.settings.gatewayUrl);
  const agent = useStore(s => s.settings.agentId);
  const selection = useStore(s => s.models);
  const pending = useStore(s => s.messages.some(m => m.pending));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const request = useRef(0);
  const connected = connection === 'connected';
  const load = useCallback(async (model?: string | null) => {
    const revision = ++request.current;
    setBusy(true); setError('');
    try {
      const result = model === undefined ? await bridge.models() : await bridge.selectModel(model);
      if (request.current === revision) useStore.setState({models: result});
    } catch (e) {
      if (request.current === revision) setError(e instanceof Error ? e.message : 'No se pudo consultar el modelo.');
    } finally {
      if (request.current === revision) setBusy(false);
    }
  }, []);
  useEffect(() => {
    useStore.setState({models: undefined});
    if (connected) void load();
    else {setBusy(false); setError('');}
    return () => { request.current++; };
    // Refresh on connection/session changes, never on render or animation frames.
  }, [connected, gateway, agent, load]);
  const providers = [...new Set(selection?.models.map(m => m.provider) ?? [])];
  const unknownSelection = selection?.selected && !selection.models.some(m => m.id === selection.selected);
  return <section className="model-picker" aria-busy={busy} aria-label="Selector de modelo">
    <div className="model-picker-heading"><label htmlFor={id}>Modelo de IA</label><span>{busy ? 'Consultando OpenClaw…' : connected ? 'OpenClaw' : 'Sin conexión'}</span></div>
    <div className="model-picker-controls">
      <select id={id} value={selection?.selected ?? ''} disabled={!connected || busy || pending || selection?.busy || !selection}
        aria-describedby={`${id}-scope ${id}-status`}
        onChange={e => void load(e.target.value || null)}>
        <option value="">Predeterminado del agente</option>
        {unknownSelection && <option value={selection.selected!}>{selection.selected} · actual</option>}
        {providers.map(provider => <optgroup label={provider} key={provider}>
          {selection?.models.filter(m => m.provider === provider).map(m => <option key={m.id} value={m.id} disabled={!m.available}>{m.name}{m.available ? '' : ' · no disponible'}</option>)}
        </optgroup>)}
      </select>
      <button type="button" aria-label="Actualizar modelos" title="Actualizar modelos" disabled={!connected || busy} onClick={() => void load()}><RefreshCw size={16}/></button>
    </div>
    <p className="quiet-note model-current" id={`${id}-status`} role="status">{pending || selection?.busy ? 'Espera a que termine la respuesta y pulsa actualizar.' : selection?.effective ? `En uso: ${selection.effective}` : connected && !busy ? 'No hay modelo confirmado. Pulsa actualizar.' : 'Conecta el Gateway para ver sus modelos configurados.'}</p>
    <p className="quiet-note" id={`${id}-scope`}>Se aplica a la sesión {selection?.sessionKey ?? `agent:${agent}:main`}. Otros clientes de esa sesión usarán el mismo modelo.</p>
    {selection && !selection.models.length && <p className="info-note">No hay modelos configurados. Añádelos en OpenClaw y pulsa actualizar.</p>}
    {error && <p className="model-error" role="alert">{error}</p>}
  </section>;
}
