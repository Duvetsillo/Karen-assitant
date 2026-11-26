import { afterEach, describe, expect, it } from 'vitest';
import { mkdtempSync, readFileSync, rmSync, existsSync, realpathSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { tmpdir } from 'node:os';
import { DatabaseSync } from 'node:sqlite';
import { CoreTaskReader } from '../electron/core-tasks';

const directories: string[] = [];
afterEach(() => { for (const folder of directories.splice(0)) {
  const target = realpathSync(folder);
  expect(dirname(target)).toBe(realpathSync(tmpdir()));
  expect(basename(target)).toMatch(/^karen-tasks-read-/);
  rmSync(target, { recursive: true, force: true });
} });
function fixture() {
  const folder = mkdtempSync(join(tmpdir(), 'karen-tasks-read-'));
  directories.push(folder);
  const path = join(folder, 'tasks.sqlite3');
  const db = new DatabaseSync(path);
  db.exec(`CREATE TABLE task_jobs(id TEXT, status TEXT, cursor INTEGER, created_at TEXT,
    updated_at TEXT, cancel_requested INTEGER, plan_hash TEXT);
    CREATE TABLE task_steps(task_id TEXT, ordinal INTEGER, tool TEXT, permission TEXT,
    status TEXT, args_hash TEXT);`);
  const id = 'a'.repeat(32);
  db.prepare('INSERT INTO task_jobs VALUES(?,?,?,?,?,?,?)').run(id, 'running', 0, '2026-10-31', '2026-10-31', 0, 'PRIVATE-HASH');
  db.prepare('INSERT INTO task_steps VALUES(?,?,?,?,?,?)').run(id, 0, 'cpu_sample', 'read', 'running', 'PRIVATE-ARGS-HASH');
  db.close();
  return { folder, path, id };
}

describe('persistent task read adapter', () => {
  it('reads versioned schedules without recipes, mutation or execution', () => {
    const {path, id} = fixture();
    const db = new DatabaseSync(path);
    db.exec(`CREATE TABLE core2_meta(key TEXT PRIMARY KEY,value TEXT);
      INSERT INTO core2_meta VALUES('automation_version','1');
      CREATE TABLE core2_schedules(id TEXT,name TEXT,next_run TEXT,interval_seconds INTEGER,retries INTEGER,
      enabled INTEGER,last_status TEXT,payload TEXT);`);
    db.prepare('INSERT INTO core2_schedules VALUES(?,?,?,?,?,?,?,?)').run(id,'Bearer synthetic-label','2100-01-01',null,0,1,null,'PRIVATE_RECIPE');
    db.close();
    const before = readFileSync(path);
    const rows = new CoreTaskReader(path).schedules();
    expect(rows[0]).toMatchObject({id, enabled:1, name:'Bearer [redactado]'});
    expect(JSON.stringify(rows)).not.toMatch(/PRIVATE_RECIPE|synthetic-label|payload/);
    expect(readFileSync(path)).toEqual(before);
    const policy = new DatabaseSync(path);
    policy.exec(`INSERT INTO core2_meta VALUES('automation_policy_version','1');
      CREATE TABLE core2_schedule_policy(schedule_id TEXT,event_topic TEXT);`);
    policy.prepare('INSERT INTO core2_schedule_policy VALUES(?,?)').run(id,'memory.conflict');
    policy.close();
    expect(new CoreTaskReader(path).schedules()[0].event_topic).toBe('memory.conflict');
  });
  it('reads bounded metadata and leaves task state and private fields untouched', () => {
    const { path, id } = fixture();
    const before = readFileSync(path);
    const reader = new CoreTaskReader(path);
    expect(reader.list()[0]).toMatchObject({ id, status: 'running', cursor: 0 });
    expect(reader.get(id)).toMatchObject({ id, status: 'running', cancel_requested: false,
      steps: [{ ordinal: 0, tool: 'cpu_sample', permission: 'read', status: 'running' }] });
    expect(JSON.stringify(reader.get(id))).not.toContain('PRIVATE');
    expect(readFileSync(path)).toEqual(before);
    const writer = new DatabaseSync(path);
    writer.exec("UPDATE task_jobs SET status='completed',cursor=1; UPDATE task_steps SET status='step_completed';");
    writer.close();
    expect(reader.get(id)?.status).toBe('completed');
    expect(reader.get('b'.repeat(32))).toBeNull();
  });
  it('fails closed on missing configuration, invalid IDs and absent files', () => {
    const { folder, path } = fixture();
    expect(() => new CoreTaskReader().list()).toThrow('KAREN_TASKS_DB');
    expect(() => new CoreTaskReader('relative.sqlite3').list()).toThrow('absoluto');
    expect(() => new CoreTaskReader(path).get('../secret')).toThrow('inválido');
    const missing = join(folder, 'absent.sqlite3');
    expect(() => new CoreTaskReader(missing).list()).toThrow();
    expect(existsSync(missing)).toBe(false);
  });
});
