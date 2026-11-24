import { existsSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import type { CoreTaskSummary, CoreTaskDetail, CorePlanSummary, CorePlanDetail } from '../shared/core-tasks.js';

/** Read the same persistent task IDs as classic, without recovering or executing jobs. */
export class CoreTaskReader {
  constructor(private path?: string) {}

  private read<T>(query: (db: DatabaseSync) => T): T {
    if (!this.path || !isAbsolute(this.path) || !existsSync(this.path))
      throw new Error('Configura KAREN_TASKS_DB con un archivo de tareas existente y absoluto.');
    const db = new DatabaseSync(this.path, { readOnly: true });
    try {
      db.exec('PRAGMA busy_timeout=200; BEGIN');
      return query(db);
    } finally { db.close(); }
  }

  list(): CoreTaskSummary[] {
    return this.read(db => db.prepare(`SELECT id,status,cursor,created_at,updated_at FROM task_jobs
      ORDER BY updated_at DESC,id DESC LIMIT 50`).all() as unknown as CoreTaskSummary[]);
  }
  plans(): CorePlanSummary[] {
    return this.read(db => db.prepare('SELECT id,goal,status,created_at,updated_at FROM core2_plans ORDER BY created_at DESC LIMIT 50').all() as unknown as CorePlanSummary[]);
  }
  plan(id: string): CorePlanDetail | null {
    if (!/^[0-9a-f]{32}$/.test(id)) throw new Error('ID de plan inválido.');
    return this.read(db => {
      const plan = db.prepare('SELECT id,goal,status,created_at,updated_at FROM core2_plans WHERE id=?').get(id) as unknown as CorePlanSummary | undefined;
      if (!plan) return null;
      const steps = db.prepare('SELECT step_id,ordinal,tool,agent,permission,status,attempts FROM core2_plan_steps WHERE plan_id=? ORDER BY ordinal LIMIT 24').all(id) as unknown as CorePlanDetail['steps'];
      return {...plan, steps};
    });
  }

  get(id: string): CoreTaskDetail | null {
    if (!/^[0-9a-f]{32}$/.test(id)) throw new Error('ID de tarea inválido.');
    return this.read(db => {
      const task = db.prepare(`SELECT id,status,cursor,created_at,updated_at,cancel_requested
        FROM task_jobs WHERE id=?`).get(id) as unknown as (CoreTaskSummary & { cancel_requested: number }) | undefined;
      if (!task) return null;
      const steps = db.prepare('SELECT ordinal,tool,permission,status FROM task_steps WHERE task_id=? ORDER BY ordinal LIMIT 32')
        .all(id) as unknown as CoreTaskDetail['steps'];
      return { ...task, cancel_requested: Boolean(task.cancel_requested), steps };
    });
  }
}
