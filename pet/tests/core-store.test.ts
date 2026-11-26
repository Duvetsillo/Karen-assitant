import { afterEach, describe, expect, it, vi } from 'vitest';
import { DatabaseSync } from 'node:sqlite';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { CoreStore } from '../electron/core-store';
import { applyCoreMode, applyCoreVoiceStyle } from '../electron/core-style-sync';
import { defaults } from '../shared/settings';

const directories: string[] = [];
afterEach(() => {
  for (const directory of directories.splice(0)) rmSync(directory, { recursive: true, force: true });
});

function legacyArchive() {
  const directory = mkdtempSync(join(tmpdir(), 'karen-core-test-'));
  directories.push(directory);
  const path = join(directory, 'conversations.sqlite3');
  const db = new DatabaseSync(path);
  db.exec(`
    CREATE TABLE chats (id TEXT PRIMARY KEY, title TEXT NOT NULL,
      updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE exchanges (id INTEGER PRIMARY KEY, chat_id TEXT NOT NULL,
      prompt TEXT NOT NULL, answer TEXT NOT NULL, ok INTEGER NOT NULL);
    CREATE TABLE preferences (key TEXT PRIMARY KEY, value TEXT);
  `);
  db.close();
  return path;
}

describe('Karen Core SQLite v1', () => {
  it('lists handoff metadata while keeping context, criteria, payload and hashes private', () => {
    const path = legacyArchive();
    const core = new CoreStore(path);
    try {
      const db = new DatabaseSync(path);
      db.exec(`INSERT INTO core_meta VALUES('handoff_version','1');
        CREATE TABLE core2_handoffs(id TEXT,project TEXT,status TEXT,priority TEXT,updated_at TEXT,hash TEXT,payload TEXT);`);
      db.prepare('INSERT INTO core2_handoffs VALUES(?,?,?,?,?,?,?)').run('a'.repeat(32),'Karen','pending','normal','2026-11-26','PRIVATE_HASH','PRIVATE_CONTEXT');
      db.close();
      expect(core.listHandoffs()).toEqual([{id:'a'.repeat(32),project:'Karen',status:'pending',priority:'normal',updated_at:'2026-11-26'}]);
      expect(JSON.stringify(core.listHandoffs())).not.toContain('PRIVATE_');
    } finally { core.close(); }
  });
  it('persiste eventos sin contenido y elimina la actividad al cerrar ordenadamente', () => {
    const path = legacyArchive();
    const core = new CoreStore(path);
    core.appendOpenClawTurn('agent:main:main', 'event-run', 'Private prompt', 'Private answer');
    core.setActivity('a'.repeat(32), 'THINKING');
    expect(core.activities()).toEqual([expect.objectContaining({ interface: 'pet', state: 'THINKING' })]);
    const db = new DatabaseSync(path);
    try {
      const count = (db.prepare('SELECT COUNT(*) n FROM core_events').get() as { n: number }).n;
      core.setActivity('a'.repeat(32), 'THINKING');
      expect((db.prepare('SELECT COUNT(*) n FROM core_events').get() as { n: number }).n).toBe(count);
      expect(JSON.stringify(db.prepare('SELECT * FROM core_events').all())).not.toContain('Private');
      db.prepare('UPDATE core_activity SET updated_at=?').run(Date.now() / 1000 - 20);
      expect(core.activities()).toEqual([]);
      core.clearActivity('a'.repeat(32));
      expect(db.prepare('SELECT * FROM core_activity').all()).toEqual([]);
    } finally { db.close(); core.close(); }
  });
  it('guarda un turno de OpenClaw una sola vez en el archivo clásico', () => {
    const path = legacyArchive();
    const core = new CoreStore(path);
    core.appendOpenClawTurn('agent:main:main', 'run-1', 'Revisa el servidor', 'Está activo');
    core.appendOpenClawTurn('agent:main:main', 'run-1', 'Revisa el servidor', 'Está activo');
    core.close();
    const reopened = new CoreStore(path);
    reopened.appendOpenClawTurn('agent:main:main', 'run-1', 'Revisa el servidor', 'Está activo');
    reopened.close();
    const db = new DatabaseSync(path);
    try {
      const chats = db.prepare('SELECT id,title FROM chats').all() as { id: string; title: string }[];
      expect(chats).toHaveLength(1);
      expect(chats[0].title).toBe('Revisa el servidor');
      expect(db.prepare('SELECT prompt,answer,ok FROM exchanges').all()).toEqual([
        { prompt: 'Revisa el servidor', answer: 'Está activo', ok: 1 },
      ]);
      expect(db.prepare("SELECT value FROM core_meta WHERE key='schema_version'").get()).toEqual({ value: '1' });
    } finally { db.close(); }
  });

  it('lee chats clásicos localmente sin alterar sus turnos', () => {
    const path = legacyArchive();
    const db = new DatabaseSync(path);
    const chatId = 'a'.repeat(32);
    db.prepare('INSERT INTO chats (id,title) VALUES (?,?)').run(chatId, 'Proyecto Karen');
    db.prepare('INSERT INTO exchanges (chat_id,prompt,answer,ok) VALUES (?,?,?,1)').run(chatId, 'Hola', 'Hola de nuevo');
    db.prepare('INSERT INTO exchanges (chat_id,prompt,answer,ok) VALUES (?,?,?,0)').run(chatId, 'Falló', 'Error');
    db.close();
    const core = new CoreStore(path);
    expect(core.listChats()[0]).toMatchObject({ id: chatId, title: 'Proyecto Karen' });
    expect(core.readChat(chatId)).toEqual([{ prompt: 'Hola', answer: 'Hola de nuevo' }]);
    expect(() => core.readChat('../privado')).toThrow('inválido');
    core.close();
  });

  it('comparte solo estilos de voz permitidos mediante la preferencia existente', () => {
    const path = legacyArchive();
    const core = new CoreStore(path);
    expect(core.getVoiceStyle()).toBeNull();
    core.setVoiceStyle('warm');
    expect(core.getVoiceStyle()).toBe('warm');
    expect(() => core.setVoiceStyle('invalid' as 'warm')).toThrow('desconocido');
    core.close();
    const reopened = new CoreStore(path);
    expect(reopened.getVoiceStyle()).toBe('warm');
    reopened.close();
  });

  it('comparte solo modos válidos sin cambiar preferencias visuales', () => {
    const path = legacyArchive();
    const core = new CoreStore(path);
    expect(core.getMode()).toBeNull();
    core.setMode('gaming');
    expect(core.getMode()).toBe('gaming');
    expect(() => core.setMode('invalid' as 'gaming')).toThrow('desconocido');
    core.close();
    const reopened = new CoreStore(path);
    expect(reopened.getMode()).toBe('gaming');
    reopened.close();
  });

  it('aplica un modo externo sin escribirlo de vuelta', () => {
    const core = new CoreStore(legacyArchive());
    core.setMode('do_not_disturb');
    const writeBack = vi.spyOn(core, 'setMode');
    let current = { ...defaults };
    const save = vi.fn((patch: Partial<typeof defaults>) => (current = { ...current, ...patch }));
    const notify = vi.fn();
    expect(applyCoreMode(core, current, save, notify)).toBe(true);
    expect(current.mode).toBe('do_not_disturb');
    expect(notify).toHaveBeenCalledWith(current);
    expect(applyCoreMode(core, current, save, notify)).toBe(false);
    expect(writeBack).not.toHaveBeenCalled();
    core.close();
  });

  it('aplica un estilo externo una vez y notifica sin escribir de vuelta', () => {
    const core = new CoreStore(legacyArchive());
    core.setVoiceStyle('warm');
    const writeBack = vi.spyOn(core, 'setVoiceStyle');
    let current = { ...defaults };
    const save = vi.fn((patch: Partial<typeof defaults>) => (current = { ...current, ...patch }));
    const notify = vi.fn();
    expect(applyCoreVoiceStyle(core, current, save, notify)).toBe(true);
    expect(current.voiceStyle).toBe('warm');
    expect(notify).toHaveBeenCalledWith(current);
    expect(applyCoreVoiceStyle(core, current, save, notify)).toBe(false);
    expect(save).toHaveBeenCalledTimes(1);
    expect(writeBack).not.toHaveBeenCalled();
    core.close();
  });

  it('informa estado real sin contar recuerdos sensibles', () => {
    const path = legacyArchive();
    const db = new DatabaseSync(path);
    db.exec(`CREATE TABLE core_memories (id TEXT, sensitive INTEGER, expires_at TEXT);
      INSERT INTO core_memories VALUES ('visible',0,NULL),('privado',1,NULL),('caducado',0,'2020-01-01');`);
    db.close();
    const core = new CoreStore(path);
    expect(core.status()).toEqual({ version: '1', chats: 0, memories: 1, voiceStyle: null });
    core.close();
  });

  it('rechaza una versión de esquema incompatible antes de escribir turnos', () => {
    const path = legacyArchive();
    const db = new DatabaseSync(path);
    db.exec("CREATE TABLE core_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL); INSERT INTO core_meta VALUES ('schema_version','99');");
    db.close();
    expect(() => new CoreStore(path)).toThrow('no compatible');
    const unchanged = new DatabaseSync(path);
    expect(unchanged.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='core_external_turns'").get()).toBeUndefined();
    unchanged.close();
  });

  it('consulta recuerdos locales y excluye sensibles sin enviarlos al modelo', () => {
    const path = legacyArchive();
    const db = new DatabaseSync(path);
    db.exec(`CREATE TABLE core_memories (
      id TEXT, project TEXT, content TEXT, status TEXT, sensitive INTEGER,
      expires_at TEXT, updated_at TEXT);
      INSERT INTO core_memories VALUES
        ('visible','Karen','Respuesta breve','confirmed',0,NULL,'2026-10-27'),
        ('privado','Karen','Clave privada','confirmed',1,NULL,'2026-10-27'),
        ('otro','Estudio','Tesis','inferred',0,NULL,'2026-10-27');`);
    db.close();
    const core = new CoreStore(path);
    expect(core.listMemories('Karen', 'breve')).toEqual([
      { id: 'visible', content: 'Respuesta breve', status: 'confirmed' },
    ]);
    expect(core.listMemories('Karen')).toHaveLength(1);
    core.close();
  });
});
