import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { bridge } from './native';
import { useStore } from './state/store';
import { ROUTING_MODES, type RoutingMode, type ResourceProfile } from '../shared/models';

const routeLabels:Record<RoutingMode,string>={auto:'Automático',manual:'Manual',fast:'Respuesta rápida',balanced:'Equilibrado',reasoning:'Razonamiento',coding:'Programación',vision:'Visión',voice:'Conversación por voz',economy:'Económico',local:'Local',privacy:'Privacidad'};

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
  const settings=useStore(s=>s.settings);
  const patch=async(value:Parameters<typeof bridge.settings>[0])=>{
    setError('');setBusy(true);
    try{useStore.setState({settings:await bridge.settings(value)});return true;}catch(e){setError(e instanceof Error?e.message:'No se pudo guardar.');return false;}finally{setBusy(false);}
  };
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
        onChange={e => {const model=e.target.value||null;void patch({routingMode:'manual'}).then(saved=>saved?load(model):undefined);}}>
        <option value="">Predeterminado del agente</option>
        {unknownSelection && <option value={selection.selected!}>{selection.selected} · actual</option>}
        {providers.map(provider => <optgroup label={provider} key={provider}>
          {selection?.models.filter(m => m.provider === provider).map(m => <option key={m.id} value={m.id} disabled={!m.available}>{m.name}{m.available ? '' : ' · no disponible'}</option>)}
        </optgroup>)}
      </select>
      <button type="button" aria-label="Actualizar modelos" title="Actualizar modelos" disabled={!connected || busy} onClick={() => void load()}><RefreshCw size={16}/></button>
    </div>
    <div className="model-routing-controls">
      <label>Selección<select aria-label="Ruta de modelos" value={settings.routingMode} disabled={busy||pending} onChange={e=>void patch({routingMode:e.target.value as RoutingMode})}>
        {ROUTING_MODES.map(mode=><option key={mode} value={mode}>{routeLabels[mode]}</option>)}
      </select></label>
      <label>Recursos<select aria-label="Perfil de recursos" value={settings.mode==='gaming'?'gaming':settings.mode==='do_not_disturb'?'silent':settings.resourceProfile} disabled={busy||pending}
        onChange={e=>void patch(e.target.value==='gaming'?{mode:'gaming'}:e.target.value==='silent'?{mode:'do_not_disturb'}:{mode:'normal',resourceProfile:e.target.value as ResourceProfile})}>
        <option value="performance">Rendimiento</option><option value="balanced">Equilibrado</option><option value="economy">Ahorro</option><option value="gaming">Juego</option><option value="work">Trabajo</option><option value="silent">Silencio</option>
      </select></label>
    </div>
    <p className="quiet-note model-current" id={`${id}-status`} role="status">{pending || selection?.busy ? 'Espera a que termine la respuesta y pulsa actualizar.' : selection?.effective ? `En uso: ${selection.effective}` : connected && !busy ? 'No hay modelo confirmado. Pulsa actualizar.' : 'Conecta el Gateway para ver sus modelos configurados.'}</p>
    <p className="quiet-note" id={`${id}-scope`}>Se aplica a la sesión {selection?.sessionKey ?? `agent:${agent}:main`}. Otros clientes de esa sesión usarán el mismo modelo.</p>
    {selection?.manager&&<details className="model-inventory"><summary>{selection.manager.catalog.length} modelos locales instalados · ver capacidades</summary>
      <p className="quiet-note" role="status">{selection.manager.reason}</p>
      <p className="quiet-note">RAM libre: {(selection.manager.budget.ram_available_bytes/1073741824).toFixed(1)} GB · VRAM libre: {selection.manager.budget.vram_available_bytes===null?'sin medición':`${(selection.manager.budget.vram_available_bytes/1073741824).toFixed(1)} GB`}. Las estimaciones filtran candidatos; OpenClaw administra la carga y la descarga. Juego y Silencio bloquean nuevas inferencias.</p>
      <ul>{selection.manager.catalog.map(model=><li key={model.name}><strong>{model.name}</strong><span>{(model.size/1073741824).toFixed(1)} GB · {model.capabilities.join(', ')}{selection.models.some(m=>m.id===`ollama/${model.name}`)?'':' · falta configurar en OpenClaw'}</span></li>)}</ul>
      <p className="quiet-note">Ollama verificado en este equipo. LM Studio, llama.cpp y proveedores remotos requieren un adaptador; no están conectados. Voz utiliza su motor local propio. Instala o elimina modelos desde Ollama; este panel no descarga pesos.</p>
    </details>}
    {selection?.managerError&&<p className="model-error" role="alert">{selection.managerError}</p>}
    {selection && !selection.models.length && <p className="info-note">No hay modelos configurados. Añádelos en OpenClaw y pulsa actualizar.</p>}
    {error && <p className="model-error" role="alert">{error}</p>}
  </section>;
}
