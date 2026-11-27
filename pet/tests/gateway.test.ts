import { afterEach, describe, it, expect, vi } from "vitest";
import { WebSocketServer, WebSocket } from "ws";
import {
  generateKeyPairSync,
  createHash,
  createPublicKey,
  sign,
  verify,
} from "node:crypto";
import { buildDeviceAuthPayloadV3 } from "@openclaw/gateway-client";
import { OpenClawAdapter } from "../electron/gateway";
import { defaults } from "../shared/settings";
import type { DesktopEvent } from "../shared/types";
import type { TurnModels } from '../electron/model-manager';

const resources: { adapter: OpenClawAdapter; server: WebSocketServer }[] = [];
afterEach(async () => {
  for (const r of resources.splice(0)) {
    r.adapter.disconnect();
    for (const ws of r.server.clients) ws.terminate();
    await new Promise<void>((resolve) => r.server.close(() => resolve()));
  }
});
async function until(check: () => boolean, timeout = 4000) {
  const end = Date.now() + timeout;
  while (!check()) {
    if (Date.now() > end) throw new Error("Tiempo de espera agotado");
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}
async function setup(core?: { appendOpenClawTurn(sessionKey: string, runId: string, prompt: string, answer: string): void }, manager?:TurnModels,scope:'shared'|'desktop'='shared') {
  const server = new WebSocketServer({ port: 0, host: "127.0.0.1" });
  await new Promise<void>((resolve) => server.once("listening", resolve));
  const address = server.address();
  if (typeof address === "string" || !address) throw new Error("Sin puerto");
  const keys = generateKeyPairSync("ed25519");
  const raw = keys.publicKey
    .export({ format: "der", type: "spki" })
    .subarray(-32);
  const identity = {
    deviceId: createHash("sha256").update(raw).digest("hex"),
    publicKeyPem: keys.publicKey
      .export({ format: "pem", type: "spki" })
      .toString(),
    privateKeyPem: keys.privateKey
      .export({ format: "pem", type: "pkcs8" })
      .toString(),
  };
  const events: DesktopEvent[] = [];
  const requests: { method: string; params: Record<string, unknown> }[] = [];
  let signatureValid = false;
  let stored = false;
  let socket: WebSocket | undefined;
  let selectedModel: string | null = null;
  let failModelPatch = false;
  let failAbort = false;
  let delayNextSend = false;
  let delayedSend: { id: string; payload: unknown } | undefined;
  const adapter = new OpenClawAdapter(
    {
      settings: { ...defaults,conversationScope:scope, gatewayUrl: `ws://127.0.0.1:${address.port}` },
      credential: () => ({ token: "test-only-bootstrap" }),
      hostDeps: () => ({
        loadOrCreateDeviceIdentity: () => identity,
        signDevicePayload: (key, payload) =>
          sign(null, Buffer.from(payload), key).toString("base64url"),
        publicKeyRawBase64UrlFromPem: () => raw.toString("base64url"),
        storeDeviceAuthToken: () => {
          stored = true;
        },
      }),
    },
    (event) => events.push(event),
    () => {},
    core,
    manager,
  );
  resources.push({ adapter, server });
  server.on("connection", (ws) => {
    socket = ws;
    const nonce = "test-challenge-" + Math.random(),
      ts = Date.now();
    ws.send(
      JSON.stringify({
        type: "event",
        event: "connect.challenge",
        payload: { nonce, ts },
      }),
    );
    ws.on("message", (data) => {
      const req = JSON.parse(data.toString());
      requests.push(req);
      let payload: unknown = {};
      if (req.method === "connect") {
        const p = req.params;
        const proof = buildDeviceAuthPayloadV3({
          deviceId: p.device.id,
          clientId: p.client.id,
          clientMode: p.client.mode,
          role: p.role,
          scopes: p.scopes,
          signedAtMs: p.device.signedAt,
          token: p.auth.token,
          nonce: p.device.nonce,
          platform: p.client.platform,
          deviceFamily: p.client.deviceFamily,
        });
        signatureValid =
          p.device.nonce === nonce &&
          p.device.signedAt === ts &&
          verify(
            null,
            Buffer.from(proof),
            createPublicKey(identity.publicKeyPem),
            Buffer.from(p.device.signature, "base64url"),
          );
        payload = {
          type: "hello-ok",
          protocol: 4,
          server: { version: "test-fixture", connId: "test" },
          features: {
            methods: ["chat.send", "chat.history", "chat.abort"],
            events: ["chat", "agent"],
          },
          snapshot: {
            presence: [],
            health: {},
            stateVersion: { presence: 1, health: 1 },
            uptimeMs: 1,
          },
          policy: {
            maxPayload: 26214400,
            maxBufferedBytes: 52428800,
            tickIntervalMs: 15000,
          },
          auth: {
            role: "operator",
            scopes: ["operator.read", "operator.write"],
            deviceToken: "test-only-device",
          },
        };
      }
      if (req.method === "chat.history") payload = { messages: [] };
      if (req.method === 'models.list') payload = {models: [
        {id:'test-small', name:'Small', provider:'ollama', available:true},
        {id:'test-large', name:'Large', provider:'ollama', available:true},
        {id:'locked', name:'Locked', provider:'ollama', available:false},
      ]};
      if (req.method === 'sessions.list') {
        const [modelProvider, model] = (selectedModel ?? 'ollama/test-small').split('/');
        payload = {defaults: {modelProvider:'ollama', model:'test-small'}, sessions: [{key:adapter.sessionKey, model, modelProvider, modelOverrideSource: selectedModel ? 'user' : null}]};
      }
      if (req.method === 'sessions.patch') {
        if (failModelPatch) {
          ws.send(JSON.stringify({type:'res', id:req.id, ok:false, error:{code:'UNAVAILABLE', message:'Provider unavailable'}}));
          return;
        }
        selectedModel = req.params.model;
        payload = {ok:true};
      }
      if (req.method === 'chat.abort' && failAbort) {
        ws.send(JSON.stringify({type:'res', id:req.id, ok:false, error:{code:'UNAVAILABLE', message:'Abort unavailable'}}));
        return;
      }
      if (req.method === "chat.send") {
        payload = { runId: req.params.idempotencyKey, status: "started" };
        if (delayNextSend) {
          delayNextSend = false;
          delayedSend = { id: req.id, payload };
          return;
        }
      }
      ws.send(JSON.stringify({ type: "res", id: req.id, ok: true, payload }));
    });
  });
  await adapter.connect();
  await until(() => adapter.info.state === "connected");
  return {
    adapter,
    events,
    requests,
    get signatureValid() {
      return signatureValid;
    },
    get stored() {
      return stored;
    },
    event: (event: string, payload: unknown) =>
      socket?.send(JSON.stringify({ type: "event", event, payload })),
    close: () => socket?.close(),
    failModelPatch: () => { failModelPatch = true; },
    failAbort: () => { failAbort = true; },
    delayNextSend: () => { delayNextSend = true; },
    releaseSend: () => {
      if (!delayedSend) throw new Error('No hay envío pendiente');
      socket?.send(JSON.stringify({ type: 'res', id: delayedSend.id, ok: true, payload: delayedSend.payload }));
      delayedSend = undefined;
    },
  };
}
describe("adaptador contra servidor de contrato WebSocket", () => {
  it('keeps desktop history and model edits in their own session',async()=>{
    const t=await setup(undefined,undefined,'desktop');
    expect(t.adapter.sessionKey).toBe('agent:main:karen-desktop');
    await t.adapter.selectModel('ollama/test-large');await t.adapter.send('Hola');
    expect(t.requests.find(r=>r.method==='sessions.patch')?.params.key).toBe('agent:main:karen-desktop');
    expect(t.requests.find(r=>r.method==='chat.send')?.params.sessionKey).toBe('agent:main:karen-desktop');
  });
  it('routes before sending, confirms the model and releases ownership on the terminal event',async()=>{
    const release=vi.fn();
    const manager:TurnModels={inspect:vi.fn().mockRejectedValue(new Error('metadata test')),
      prepare:vi.fn().mockResolvedValue({id:'ollama/test-large',reason:'coding'}),acquire:vi.fn().mockResolvedValue(undefined),release};
    const t=await setup(undefined,manager);
    release.mockClear();
    await t.adapter.send('depura código');
    expect(t.requests.find(r=>r.method==='sessions.patch')?.params.model).toBe('ollama/test-large');
    expect(manager.acquire).toHaveBeenCalledOnce();
    const run=t.requests.find(r=>r.method==='chat.send')!.params.idempotencyKey;
    expect(release).not.toHaveBeenCalled();
    t.event('chat',{sessionKey:'agent:main:main',runId:run,state:'final',deltaText:'Listo'});
    await until(()=>release.mock.calls.length>0);
  });
  it('does not send or silently bypass a failed local lease',async()=>{
    const manager:TurnModels={inspect:vi.fn().mockRejectedValue(new Error('metadata test')),
      prepare:vi.fn().mockResolvedValue({id:'ollama/test-small',reason:'conversation'}),acquire:vi.fn().mockRejectedValue(new Error('ocupada')),release:vi.fn()};
    const t=await setup(undefined,manager);
    await expect(t.adapter.send('Hola')).rejects.toThrow('ocupada');
    expect(t.requests.some(r=>r.method==='chat.send')).toBe(false);
  });
  it('rejects overlapping preparation and model edits while routing',async()=>{
    let resume:(value:{id:string;reason:string})=>void=()=>{};
    const manager:TurnModels={inspect:vi.fn().mockRejectedValue(new Error('metadata test')),
      prepare:vi.fn(()=>new Promise<{id:string;reason:string}>(resolve=>{resume=resolve;})),acquire:vi.fn().mockResolvedValue(undefined),release:vi.fn()};
    const t=await setup(undefined,manager);
    const first=t.adapter.send('Primera');
    await until(()=>vi.mocked(manager.prepare).mock.calls.length>0);
    await expect(t.adapter.send('Segunda')).rejects.toThrow(/preparando/);
    await expect(t.adapter.selectModel('ollama/test-large')).rejects.toThrow(/Espera/);
    resume({id:'ollama/test-small',reason:'test'});await first;
    expect(t.requests.filter(r=>r.method==='chat.send')).toHaveLength(1);
  });
  it('cancels preparation without sending a late turn',async()=>{
    let resume:(value:{id:string;reason:string})=>void=()=>{};
    const manager:TurnModels={inspect:vi.fn().mockRejectedValue(new Error('metadata test')),
      prepare:vi.fn(()=>new Promise<{id:string;reason:string}>(resolve=>{resume=resolve;})),acquire:vi.fn().mockResolvedValue(undefined),release:vi.fn()};
    const t=await setup(undefined,manager);
    const first=t.adapter.send('Primera');
    const rejected=expect(first).rejects.toThrow(/cancelada/);
    await until(()=>vi.mocked(manager.prepare).mock.calls.length>0);
    await t.adapter.abort();resume({id:'ollama/test-small',reason:'test'});await rejected;
    expect(t.requests.some(r=>r.method==='chat.send')).toBe(false);
    expect(manager.acquire).not.toHaveBeenCalled();
  });
  it('shows schedules and development offline without gateway requests or write actions', async () => {
    const core = {appendOpenClawTurn: vi.fn(),
      listSchedules: vi.fn(() => [{id:'a'.repeat(32),name:'Routine',next_run:'2100-01-01',interval_seconds:null,retries:0,enabled:1,last_status:null}]),
      listHandoffs: vi.fn(() => [{id:'b'.repeat(32),project:'Karen',status:'pending',priority:'normal',updated_at:'2026-11-26'}])};
    const t = await setup(core);
    t.adapter.disconnect();
    await t.adapter.send('/automatizaciones listar');
    await t.adapter.send('/desarrollo listar');
    await t.adapter.send('/automatizaciones ejecutar ' + 'a'.repeat(32));
    expect(core.listSchedules).toHaveBeenCalledOnce();
    expect(core.listHandoffs).toHaveBeenCalledOnce();
    expect(t.events.some(event => event.type === 'chat' && event.final && event.speak === false && event.message.text.includes('Routine'))).toBe(true);
    expect(t.requests.filter(request => request.method === 'chat.send')).toHaveLength(0);
    expect(core.appendOpenClawTurn).not.toHaveBeenCalled();
  });
  it('consulta el ID de una tarea local sin Gateway, TTS, argumentos ni ejecución', async () => {
    const taskId = 'a'.repeat(32);
    const readTask = vi.fn(() => ({ id: taskId, status: 'running', cursor: 0,
      created_at: '2026-10-31', updated_at: '2026-10-31', cancel_requested: false,
      steps: [{ ordinal: 0, tool: 'cpu_sample', permission: 'read' as const, status: 'running' }] }));
    const core = { appendOpenClawTurn: vi.fn(), listTasks: vi.fn(() => []), readTask };
    const t = await setup(core);
    t.adapter.disconnect();
    await t.adapter.send(`/tareas estado ${taskId}`);
    expect(readTask).toHaveBeenCalledExactlyOnceWith(taskId);
    expect(t.events.some(event => event.type === 'chat' && event.final && event.speak === false && event.message.text.includes('paso 0/1'))).toBe(true);
    await t.adapter.send(`/tareas cancelar ${taskId}`);
    expect(readTask).toHaveBeenCalledTimes(1);
    expect(t.requests.filter(request => request.method === 'chat.send')).toHaveLength(0);
    expect(core.appendOpenClawTurn).not.toHaveBeenCalled();
  });
  it('muestra estado local de Core sin OpenClaw', async () => {
    const core = {
      appendOpenClawTurn: vi.fn(),
      status: vi.fn(() => ({ version: '1', chats: 2, memories: 1, voiceStyle: 'warm' })),
    };
    const t = await setup(core);
    t.adapter.disconnect();
    await t.adapter.send('/core estado');
    expect(core.status).toHaveBeenCalledOnce();
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    expect(t.events.some(e => e.type === 'chat' && e.final && e.speak === false && e.message.text.includes('2 chats'))).toBe(true);
  });

  it('consulta memoria local sin enviar texto al Gateway', async () => {
    const core = {
      appendOpenClawTurn: vi.fn(),
      listMemories: vi.fn(() => [{ id: 'memory-1', content: 'Respuesta breve', status: 'confirmed' }]),
    };
    const t = await setup(core);
    t.adapter.disconnect();
    await t.adapter.send('/memoria listar Karen');
    expect(core.listMemories).toHaveBeenCalledWith('Karen', '');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    expect(t.events.some(e => e.type === 'chat' && e.final && e.speak === false && e.message.text.includes('Respuesta breve'))).toBe(true);
  });

  it('envía memorias públicas confirmadas solo después de vista previa y confirmación', async () => {
    const core = {
      appendOpenClawTurn: vi.fn(),
      listMemories: vi.fn(() => [
        { id: '1', content: 'Servidor en Proxmox', status: 'confirmed' },
        { id: '2', content: 'Hipótesis no confirmada', status: 'inferred' },
        { id: '3', content: 'Prefiere respuesta breve', status: 'confirmed' },
      ]),
    };
    const t = await setup(core);
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('Prepara');
    await t.adapter.send('/memoria preparar Home Lab | servidor');
    expect(core.listMemories).toHaveBeenCalledWith('Home Lab', 'servidor');
    const preview = [...t.events].reverse().find(e => e.type === 'chat' && e.final && e.message.role === 'assistant');
    expect(preview?.type === 'chat' ? preview.message.text : '').toContain('Servidor en Proxmox');
    expect(preview?.type === 'chat' ? preview.message.text : '').not.toContain('Hipótesis no confirmada');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    await t.adapter.send('/memoria cancelar');
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('Prepara');
    await t.adapter.send('/memoria preparar Home Lab | servidor');
    await t.adapter.send('/memoria enviar');
    const sends = t.requests.filter(r => r.method === 'chat.send');
    expect(sends).toHaveLength(1);
    expect(sends[0].params.message).toContain('Servidor en Proxmox');
    expect(sends[0].params.message).not.toContain('Hipótesis no confirmada');
    const run = sends[0].params.idempotencyKey as string;
    t.event('chat', { sessionKey: 'agent:main:main', runId: run, state: 'final', deltaText: 'Contexto recibido.' });
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === run && e.final));
    expect(core.appendOpenClawTurn).not.toHaveBeenCalled();
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('Prepara');
  });

  it('no envía una memoria editada o borrada después de la vista previa', async () => {
    let rows = [{ id: '1', content: 'Dato anterior', status: 'confirmed' }];
    const core = { appendOpenClawTurn: vi.fn(), listMemories: vi.fn(() => rows) };
    const t = await setup(core);
    await t.adapter.send('/memoria preparar Karen | dato');
    rows = [{ id: '1', content: 'Dato corregido', status: 'confirmed' }];
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('cambiaron');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('Prepara');
    await t.adapter.send('/memoria preparar Karen | dato');
    rows = [];
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('cambiaron');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
  });

  it('descarta una memoria preparada al desconectar', async () => {
    const core = { appendOpenClawTurn: vi.fn(), listMemories: vi.fn(() => [
      { id: '1', content: 'Contexto local', status: 'confirmed' },
    ]) };
    const t = await setup(core);
    await t.adapter.send('/memoria preparar Karen | contexto');
    t.adapter.disconnect();
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('Prepara');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
  });

  it('invalida la vista previa de memoria tras perder el Gateway', async () => {
    const core = { appendOpenClawTurn: vi.fn(), listMemories: vi.fn(() => [
      { id: '1', content: 'Contexto local', status: 'confirmed' },
    ]) };
    const t = await setup(core);
    await t.adapter.send('/memoria preparar Karen | contexto');
    t.close();
    await until(() => t.events.some(e => e.type === 'connection' && e.info.state === 'reconnecting'));
    await expect(t.adapter.send('/memoria enviar')).rejects.toThrow('Prepara');
  });

  it('consulta historial clásico local sin enviarlo al Gateway', async () => {
    const chatId = 'a'.repeat(32);
    const core = {
      appendOpenClawTurn: vi.fn(),
      listChats: vi.fn(() => [{ id: chatId, title: 'Proyecto Karen', updated: '2026-10-27' }]),
      readChat: vi.fn(() => [{ prompt: 'Hola', answer: 'Hola de nuevo' }]),
    };
    const t = await setup(core);
    t.adapter.disconnect();
    await t.adapter.send('/historial listar');
    await t.adapter.send(`/historial ver ${chatId}`);
    expect(core.listChats).toHaveBeenCalledOnce();
    expect(core.readChat).toHaveBeenCalledWith(chatId);
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    expect(t.events.some(e => e.type === 'chat' && e.final && e.speak === false && e.message.text.includes('Hola de nuevo'))).toBe(true);
  });

  it('solo transfiere historial revisado tras un segundo comando y evita duplicarlo en Core', async () => {
    const chatId = 'a'.repeat(32);
    const core = {
      appendOpenClawTurn: vi.fn(),
      listChats: vi.fn(() => []),
      readChat: vi.fn(() => [{ prompt: 'Proyecto privado', answer: 'Estado confirmado' }]),
    };
    const t = await setup(core);
    await expect(t.adapter.send(`/historial enviar ${chatId}`)).rejects.toThrow('Prepara');
    await t.adapter.send(`/historial preparar ${chatId}`);
    const preview = [...t.events].reverse().find(e => e.type === 'chat' && e.final && e.message.role === 'assistant');
    expect(preview?.type === 'chat' ? preview.message.text : '').toContain('Proyecto privado');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    await t.adapter.send('/historial cancelar');
    await expect(t.adapter.send(`/historial enviar ${chatId}`)).rejects.toThrow('Prepara');
    await t.adapter.send(`/historial preparar ${chatId}`);
    await expect(t.adapter.send(`/historial enviar ${'b'.repeat(32)}`)).rejects.toThrow('Prepara');
    await t.adapter.send(`/historial preparar ${chatId}`);
    await t.adapter.send(`/historial enviar ${chatId}`);
    const sends = t.requests.filter(r => r.method === 'chat.send');
    expect(sends).toHaveLength(1);
    expect(sends[0].params.message).toContain('Proyecto privado');
    expect(sends[0].params.message).toContain('Estado confirmado');
    const run = sends[0].params.idempotencyKey as string;
    t.event('chat', { sessionKey: 'agent:main:main', runId: run, state: 'final', deltaText: 'Lista para continuar.' });
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === run && e.final));
    expect(core.appendOpenClawTurn).not.toHaveBeenCalled();
    await expect(t.adapter.send(`/historial enviar ${chatId}`)).rejects.toThrow('Prepara');
  });

  it('no envía un historial editado después de la vista previa', async () => {
    const chatId = 'a'.repeat(32);
    let rows = [{ prompt: 'Texto anterior', answer: 'Respuesta anterior' }];
    const core = { appendOpenClawTurn: vi.fn(), listChats: vi.fn(() => []), readChat: vi.fn(() => rows) };
    const t = await setup(core);
    await t.adapter.send(`/historial preparar ${chatId}`);
    rows = [{ prompt: 'Texto corregido', answer: 'Respuesta anterior' }];
    await expect(t.adapter.send(`/historial enviar ${chatId}`)).rejects.toThrow('cambió');
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(0);
    await expect(t.adapter.send(`/historial enviar ${chatId}`)).rejects.toThrow('Prepara');
  });

  it('comparte solo respuestas finales confirmadas con Karen clásica', async () => {
    const core = { appendOpenClawTurn: vi.fn() };
    const t = await setup(core);
    await t.adapter.send('Hola desde Pet');
    const run = t.requests.find(r => r.method === 'chat.send')!.params.idempotencyKey as string;
    t.event('chat', { sessionKey: 'agent:main:main', runId: run, state: 'delta', deltaText: 'Respuesta ' });
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === run));
    expect(core.appendOpenClawTurn).not.toHaveBeenCalled();
    t.event('chat', { sessionKey: 'agent:main:main', runId: run, state: 'final', deltaText: 'completa' });
    await until(() => core.appendOpenClawTurn.mock.calls.length === 1);
    expect(core.appendOpenClawTurn).toHaveBeenCalledWith('agent:main:main', run, 'Hola desde Pet', 'Respuesta completa');
  });

  it('descarta historial recibido después de cambiar la conexión', async () => {
    const t = await setup();
    const client = t.adapter.client!;
    let release!: (value: { messages: unknown[] }) => void;
    Object.defineProperty(client, 'request', {
      value: () => new Promise(resolve => { release = resolve; }),
      configurable: true,
    });
    const pending = t.adapter.history();
    t.adapter.disconnect(false);
    release({ messages: [{ id: 'historial-viejo', role: 'assistant', content: 'Respuesta privada anterior' }] });
    await pending;
    expect(t.adapter.messages.some(m => m.id === 'historial-viejo')).toBe(false);
    expect(t.events.some(e => e.type === 'chat' && e.message.id === 'historial-viejo')).toBe(false);
  });

  it('no aplica un cambio de modelo cuando la conexión cambia tras leer el catálogo', async () => {
    const t = await setup();
    const selection = await t.adapter.models();
    const before = t.requests.filter(r => r.method === 'sessions.patch').length;
    const models = t.adapter.models.bind(t.adapter);
    t.adapter.models = async () => {
      t.adapter.disconnect(false);
      return selection;
    };
    await expect(t.adapter.selectModel('ollama/test-large')).rejects.toThrow('conexión cambió');
    expect(t.requests.filter(r => r.method === 'sessions.patch')).toHaveLength(before);
    t.adapter.models = models;
  });

  it('una confirmación tardía del envío cancelado no reemplaza el runId nuevo', async () => {
    const t = await setup();
    t.delayNextSend();
    const old = t.adapter.send('Primera orden');
    await until(() => t.requests.some(r => r.method === 'chat.send'));
    await t.adapter.abort();
    await t.adapter.send('Segunda orden');
    t.releaseSend();
    await old;
    await expect(t.adapter.send('Tercera orden')).rejects.toThrow('en curso');
    const second = t.requests.filter(r => r.method === 'chat.send')[1].params.idempotencyKey;
    t.event('chat', { sessionKey: 'agent:main:main', runId: second, state: 'final', deltaText: 'Actual' });
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === second && e.final));
    await expect(t.adapter.send('Tercera orden')).resolves.toBeUndefined();
  });

  it('ignora eventos tardíos de una respuesta cancelada sin liberar la nueva', async () => {
    const t = await setup();
    await t.adapter.send('Primera orden');
    const first = t.requests.find(r => r.method === 'chat.send')!.params.idempotencyKey;
    await t.adapter.abort();
    await t.adapter.send('Segunda orden');
    const second = t.requests.filter(r => r.method === 'chat.send')[1].params.idempotencyKey;
    t.event('chat', { sessionKey: 'agent:main:main', runId: 'otro-cliente', state: 'final', deltaText: 'Otra respuesta' });
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === 'otro-cliente'));
    t.event('chat', { sessionKey: 'agent:main:main', runId: first, state: 'final', deltaText: 'Respuesta obsoleta' });
    await new Promise(resolve => setTimeout(resolve, 30));
    await expect(t.adapter.send('Tercera orden')).rejects.toThrow('en curso');
    expect(t.events.some(e => e.type === 'chat' && e.message.id === first && e.message.role === 'assistant')).toBe(false);
    t.event('chat', { sessionKey: 'agent:main:main', runId: second, state: 'final', deltaText: 'Respuesta actual' });
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === second && e.final));
    await expect(t.adapter.send('Tercera orden')).resolves.toBeUndefined();
  });

  it('libera la captura local aunque OpenClaw rechace cancelar la respuesta anterior', async () => {
    const t = await setup();
    await t.adapter.send('Primera orden');
    t.failAbort();
    await expect(t.adapter.abort()).rejects.toThrow();
    await expect(t.adapter.send('Nueva orden hablada')).resolves.toBeUndefined();
    expect(t.requests.filter(r => r.method === 'chat.send')).toHaveLength(2);
  });
  it('consulta catálogo autenticado y cambia solo el modelo de la sesión', async () => {
    const t = await setup();
    expect((await t.adapter.models()).effective).toBe('ollama/test-small');
    const chosen = await t.adapter.selectModel('ollama/test-large');
    expect(chosen.selected).toBe('ollama/test-large');
    expect(chosen.effective).toBe('ollama/test-large');
    expect(t.requests.find(r => r.method === 'sessions.patch')?.params).toEqual({key:'agent:main:main', model:'ollama/test-large'});
    expect((await t.adapter.selectModel(null)).selected).toBeNull();
    expect(t.requests.some(r => r.method.startsWith('config.'))).toBe(false);
    expect(t.events.some(e => e.type === 'models')).toBe(true);
  });
  it('rechaza modelos ajenos, no disponibles y cambios durante una respuesta', async () => {
    const t = await setup();
    await expect(t.adapter.selectModel('invented/model')).rejects.toThrow('catálogo');
    await expect(t.adapter.selectModel('ollama/locked')).rejects.toThrow('catálogo');
    await expect(t.adapter.selectModel({model:'ollama/test-large'})).rejects.toThrow('inválido');
    await t.adapter.send('Test');
    await expect(t.adapter.selectModel('ollama/test-large')).rejects.toThrow('termine');
    expect(t.requests.some(r => r.method === 'sessions.patch')).toBe(false);
  });
  it('mantiene el modelo confirmado cuando el Gateway rechaza el cambio', async () => {
    const t = await setup(); t.failModelPatch();
    await expect(t.adapter.selectModel('ollama/test-large')).rejects.toThrow('Provider unavailable');
    expect((await t.adapter.models()).effective).toBe('ollama/test-small');
    t.adapter.disconnect();
    await expect(t.adapter.models()).rejects.toThrow('Conecta');
  });
  it("envía capturas como adjuntos reales del protocolo", async () => {
    const t = await setup();
    await t.adapter.send("Describe esta imagen", [{ type: "image", mimeType: "image/png", fileName: "capture.png", content: "c3ludGhldGlj" }]);
    expect(t.requests.find(request => request.method === "chat.send")?.params.attachments).toEqual([{ type: "image", mimeType: "image/png", fileName: "karen-screen.png", content: "c3ludGhldGlj" }]);
  });
  it("firma el reto, autentica y conserva permisos de conversación", async () => {
    const t = await setup();
    expect(t.signatureValid).toBe(true);
    expect(t.stored).toBe(true);
    const connect = t.requests.find((r) => r.method === "connect")!;
    expect(connect.params.scopes).toEqual(["operator.read", "operator.write"]);
    expect(connect.params.caps).toEqual(["tool-events"]);
    expect(connect.params.minProtocol).toBe(4);
    expect(connect.params.maxProtocol).toBe(4);
  });
  it("envía a main, impide duplicados y recibe herramientas y respuesta", async () => {
    const t = await setup();
    await t.adapter.send("Hola Karen");
    await expect(t.adapter.send("Otra orden")).rejects.toThrow("en curso");
    const send = t.requests.find((r) => r.method === "chat.send")!;
    expect(send.params.sessionKey).toBe("agent:main:main");
    expect(send.params.message).toBe("Hola Karen");
    expect(send.params.idempotencyKey).toBeTypeOf("string");
    t.event("agent", {
      runId: send.params.idempotencyKey,
      seq: 1,
      ts: Date.now(),
      stream: "tool",
      data: { phase: "start", name: "read" },
    });
    t.event("chat", {
      sessionKey: "agent:main:main",
      runId: send.params.idempotencyKey,
      seq: 1,
      state: "delta",
      deltaText: "Respuesta de ",
    });
    t.event("chat", {
      sessionKey: "agent:main:main",
      runId: send.params.idempotencyKey,
      seq: 2,
      state: "delta",
      deltaText: "contrato",
    });
    t.event("chat", {
      sessionKey: "agent:main:main",
      runId: send.params.idempotencyKey,
      seq: 3,
      state: "final",
    });
    await until(() => t.events.some((e) => e.type === "chat" && e.final));
    expect(t.adapter.messages.at(-1)?.text).toBe("Respuesta de contrato");
    expect(
      t.adapter.messages.some(
        (message) => message.role === "user" && message.text === "Hola Karen",
      ),
    ).toBe(true);
    await t.adapter.send("Segunda orden");
    await t.adapter.abort();
    expect(t.requests.at(-1)?.method).toBe("chat.abort");
  });
  it("reporta una caída y reconecta con el cliente oficial", async () => {
    const t = await setup();
    t.close();
    await until(() => t.adapter.info.state === "reconnecting");
    await until(() => t.adapter.info.state === "connected", 4500);
    expect(t.requests.filter((r) => r.method === "connect").length).toBe(2);
  });
  it('descarta la respuesta vieja tras reconectar y conserva la nueva', async () => {
    const core = { appendOpenClawTurn: vi.fn() };
    const t = await setup(core);
    await t.adapter.send('Orden anterior');
    const oldRun = t.requests.find(r => r.method === 'chat.send')!.params.idempotencyKey;
    t.close();
    await until(() => t.adapter.info.state === 'reconnecting');
    await until(() => t.adapter.info.state === 'connected', 4500);
    await t.adapter.send('Orden nueva');
    const newRun = t.requests.filter(r => r.method === 'chat.send')[1].params.idempotencyKey;
    t.event('chat', {sessionKey: 'agent:main:main', runId: oldRun, state: 'final', deltaText: 'Obsoleta'});
    await new Promise(resolve => setTimeout(resolve, 30));
    expect(t.events.some(e => e.type === 'chat' && e.message.id === oldRun && e.message.role === 'assistant')).toBe(false);
    expect(core.appendOpenClawTurn).not.toHaveBeenCalled();
    await expect(t.adapter.send('Otra')).rejects.toThrow('en curso');
    t.event('chat', {sessionKey: 'agent:main:main', runId: newRun, state: 'final', deltaText: 'Actual'});
    await until(() => t.events.some(e => e.type === 'chat' && e.message.id === newRun && e.final));
    expect(core.appendOpenClawTurn).toHaveBeenCalledWith('agent:main:main', newRun, 'Orden nueva', 'Actual');
  });
});
