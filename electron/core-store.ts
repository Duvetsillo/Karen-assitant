import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import type { CoreTurnSink } from './gateway.js';
import type { CoreHandoffSummary } from '../shared/core-tasks.js';
import { publicCoreLabel } from '../shared/core-tasks.js';
import { VOICE_STYLES, type VoiceStyle, type Settings } from '../shared/types.js';
import { CoreTaskReader } from './core-tasks.js';
import { MusicMemory } from './music-memory.js';

type AssistantMode = Settings['mode'];
const MODES: AssistantMode[] = ['normal', 'gaming', 'do_not_disturb'];
export type CoreState = 'IDLE' | 'LISTENING' | 'TRANSCRIBING' | 'THINKING' | 'SPEAKING' | 'ERROR';
export interface CoreActivity { client_id: string; interface: 'classic' | 'pet'; state: CoreState; updated_at: number }

/** Optional v1 bridge to Karen classic's existing SQLite conversation archive. */
export class CoreStore implements CoreTurnSink {
  private db: DatabaseSync;
  private tasks: CoreTaskReader;
  private musicStore?: MusicMemory;
  musicMemory() { return this.musicStore ??= new MusicMemory(this.db); }

  constructor(path: string, taskPath?: string) {
    this.tasks = new CoreTaskReader(taskPath);
    if (!isAbsolute(path) || !existsSync(path))
      throw new Error('KAREN_CORE_DB debe apuntar a un archivo SQLite existente y absoluto.');
    this.db = new DatabaseSync(path);
    try {
      const tables = this.db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('chats','exchanges')").all();
      if (tables.length !== 2) throw new Error('El archivo no contiene un archivo de conversaciones de Karen.');
      const metaExists = this.db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_meta'").get();
      if (metaExists) {
        const existing = this.db.prepare("SELECT value FROM core_meta WHERE key='schema_version'").get() as { value: string } | undefined;
        if (!existing || existing.value !== '1')
          throw new Error(`Versión de Karen Core no compatible: ${existing?.value ?? 'sin versión'}`);
        const version = this.db.prepare("SELECT value FROM core_meta WHERE key='events_version'").get() as { value: string } | undefined;
        if (version && version.value !== '1') throw new Error('Versión de eventos Core no compatible.');
      }
      this.db.exec(`
        PRAGMA busy_timeout=200;
        CREATE TABLE IF NOT EXISTS core_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO core_meta (key,value) VALUES ('schema_version','1');
        CREATE TABLE IF NOT EXISTS core_external_turns (
          session_key TEXT NOT NULL, run_id TEXT NOT NULL, chat_id TEXT NOT NULL,
          PRIMARY KEY (session_key,run_id));
      `);
      const eventsVersion = this.db.prepare("SELECT value FROM core_meta WHERE key='events_version'").get() as { value: string } | undefined;
      if (eventsVersion && eventsVersion.value !== '1') throw new Error('Versión de eventos Core no compatible.');
      if (!eventsVersion) this.db.exec('BEGIN IMMEDIATE;\n' + readFileSync(new URL('../shared/core-events.sql', import.meta.url), 'utf8') + '\nCOMMIT;');
    } catch (error) {
      this.db.close();
      throw error;
    }
  }

  appendOpenClawTurn(sessionKey: string, runId: string, prompt: string, answer: string): void {
    if (!sessionKey || !runId || !prompt.trim() || !answer.trim() ||
        sessionKey.length > 512 || runId.length > 128 || prompt.length > 16000 || answer.length > 32000)
      throw new Error('Turno de conversación inválido.');
    const chatId = 'openclaw-' + createHash('sha256').update(sessionKey).digest('hex').slice(0, 32);
    const title = prompt.trim().replace(/\s+/g, ' ').slice(0, 65);
    this.db.exec('BEGIN IMMEDIATE');
    try {
      this.db.prepare('INSERT OR IGNORE INTO chats (id,title) VALUES (?,?)').run(chatId, title);
      const inserted = this.db.prepare('INSERT OR IGNORE INTO core_external_turns (session_key,run_id,chat_id) VALUES (?,?,?)')
        .run(sessionKey, runId, chatId);
      if (inserted.changes) {
        this.db.prepare('INSERT INTO exchanges (chat_id,prompt,answer,ok) VALUES (?,?,?,1)')
          .run(chatId, prompt, answer);
        this.db.prepare('UPDATE chats SET updated=CURRENT_TIMESTAMP WHERE id=?').run(chatId);
      }
      this.db.exec('COMMIT');
    } catch (error) {
      this.db.exec('ROLLBACK');
      throw error;
    }
  }

  listMemories(project: string, query = ''): { id: string; content: string; status: string }[] {
    project = project.trim();
    if (!project || project.length > 64 || /[\x00-\x1f]/.test(project) || query.length > 200)
      throw new Error('Proyecto o búsqueda inválida.');
    const exists = this.db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_memories'").get();
    if (!exists) return [];
    const needle = query.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
    return this.db.prepare(`SELECT id,content,status FROM core_memories WHERE project=? AND sensitive=0
      AND (expires_at IS NULL OR julianday(expires_at)>julianday('now'))
      AND content LIKE ? ESCAPE '\\' ORDER BY updated_at DESC,id DESC LIMIT 10`)
      .all(project, `%${needle}%`) as { id: string; content: string; status: string }[];
  }

  listChats(): { id: string; title: string; updated: string }[] {
    return this.db.prepare('SELECT id,title,updated FROM chats ORDER BY updated DESC,rowid DESC LIMIT 20')
      .all() as { id: string; title: string; updated: string }[];
  }

  readChat(chatId: string): { prompt: string; answer: string }[] {
    if (!/^(?:[0-9a-f]{32}|openclaw-[0-9a-f]{32})$/.test(chatId))
      throw new Error('ID de conversación inválido.');
    return this.db.prepare('SELECT prompt,answer FROM exchanges WHERE chat_id=? AND ok=1 ORDER BY id DESC LIMIT 10')
      .all(chatId).reverse() as { prompt: string; answer: string }[];
  }

  getVoiceStyle(): VoiceStyle | null {
    const row = this.db.prepare("SELECT value FROM preferences WHERE key='core.voice_style'").get() as { value: string } | undefined;
    return row && VOICE_STYLES.includes(row.value as VoiceStyle) ? row.value as VoiceStyle : null;
  }

  setVoiceStyle(style: VoiceStyle): void {
    if (!VOICE_STYLES.includes(style)) throw new Error('Estilo de voz desconocido.');
    this.db.prepare("INSERT INTO preferences (key,value) VALUES ('core.voice_style',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value")
      .run(style);
  }

  getMode(): AssistantMode | null {
    const row = this.db.prepare("SELECT value FROM preferences WHERE key='core.mode'").get() as { value: string } | undefined;
    return row && MODES.includes(row.value as AssistantMode) ? row.value as AssistantMode : null;
  }

  setMode(mode: AssistantMode): void {
    if (!MODES.includes(mode)) throw new Error('Modo desconocido.');
    this.db.prepare("INSERT INTO preferences (key,value) VALUES ('core.mode',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value")
      .run(mode);
  }

  status(): { version: string; chats: number; memories: number; voiceStyle: VoiceStyle | null } {
    const version = this.db.prepare("SELECT value FROM core_meta WHERE key='schema_version'").get() as { value: string };
    const chats = this.db.prepare('SELECT COUNT(*) AS count FROM chats').get() as { count: number };
    const hasMemories = this.db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_memories'").get();
    const memories = hasMemories
      ? (this.db.prepare("SELECT COUNT(*) AS count FROM core_memories WHERE sensitive=0 AND (expires_at IS NULL OR julianday(expires_at)>julianday('now'))").get() as { count: number }).count
      : 0;
    return { version: version.value, chats: chats.count, memories, voiceStyle: this.getVoiceStyle() };
  }

  close(): void { this.db.close(); }
  listTasks() { return this.tasks.list(); }
  readTask(id: string) { return this.tasks.get(id); }
  listPlans() { return this.tasks.plans(); }
  readPlan(id: string) { return this.tasks.plan(id); }
  listSchedules() { return this.tasks.schedules(); }
  listHandoffs(): CoreHandoffSummary[] {
    const version = this.db.prepare("SELECT value FROM core_meta WHERE key='handoff_version'").get() as {value: string} | undefined;
    if (version?.value !== '1') throw new Error('Versión de desarrollo incompatible o no inicializada.');
    const rows = this.db.prepare(`SELECT id,substr(project,1,64) AS project,status,priority,updated_at
      FROM core2_handoffs ORDER BY updated_at DESC LIMIT 50`).all() as unknown as CoreHandoffSummary[];
    return rows.map(row => ({...row, project: publicCoreLabel(row.project)}));
  }

  setActivity(clientId: string, state: CoreState): void {
    if (!/^[0-9a-f]{32}$/.test(clientId) || !['IDLE','LISTENING','TRANSCRIBING','THINKING','SPEAKING','ERROR'].includes(state))
      throw new Error('Actividad Core inválida.');
    this.db.prepare(`INSERT INTO core_activity VALUES (?,?,?,?) ON CONFLICT(client_id)
      DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at`)
      .run(clientId, 'pet', state, Date.now() / 1000);
    this.db.prepare('DELETE FROM core_activity WHERE updated_at<?').run(Date.now() / 1000 - 86400);
  }

  clearActivity(clientId: string): void {
    this.db.prepare('DELETE FROM core_activity WHERE client_id=?').run(clientId);
  }

  activities(): CoreActivity[] {
    const now = Date.now() / 1000;
    return this.db.prepare('SELECT client_id,interface,state,updated_at FROM core_activity WHERE updated_at>? AND updated_at<=? ORDER BY interface,client_id')
      .all(now - 15, now + 1) as unknown as CoreActivity[];
  }
}
