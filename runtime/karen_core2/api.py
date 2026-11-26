"""Read-only public Core v1 extension; never decrypt plan arguments or results."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from .privacy import public


def read_metadata(path, route):
    """Metadata only: no schema changes, decryption, recovery, or task execution."""
    definitions = {
        '/v1/schedules': ('core2_meta', 'automation_version', 'schedules',
                         '''SELECT id,substr(name,1,100) AS name,next_run,interval_seconds,retries,enabled,last_status
                            FROM core2_schedules ORDER BY next_run LIMIT 50'''),
        '/v1/handoffs': ('core_meta', 'handoff_version', 'handoffs',
                        '''SELECT id,substr(project,1,64) AS project,status,priority,updated_at
                           FROM core2_handoffs ORDER BY updated_at DESC LIMIT 50'''),
    }
    if route not in definitions:
        return None
    table, version_key, key, query = definitions[route]
    with closing(sqlite3.connect(Path(path).resolve(strict=True).as_uri() + '?mode=ro', uri=True, timeout=.5)) as db:
        db.row_factory = sqlite3.Row
        version = db.execute('SELECT value FROM ' + table + ' WHERE key=?', (version_key,)).fetchone()
        if not version or version[0] != '1':
            raise ValueError('Versión de metadatos incompatible o módulo no inicializado.')
        if route == '/v1/schedules':
            policy = db.execute("SELECT value FROM core2_meta WHERE key='automation_policy_version'").fetchone()
            if policy and policy[0] != '1':
                raise ValueError('Versión de políticas de automatización incompatible.')
            if policy:
                query = '''SELECT s.id,substr(s.name,1,100) AS name,s.next_run,s.interval_seconds,s.retries,s.enabled,s.last_status,
                    p.event_topic FROM core2_schedules s LEFT JOIN core2_schedule_policy p ON p.schedule_id=s.id
                    ORDER BY s.next_run LIMIT 50'''
        rows = [public(dict(row)) for row in db.execute(query)]
    return {'contract': 1, key: rows, 'limit': 50, 'read_only': True}


def read_plans(path, route):
    with closing(sqlite3.connect(Path(path).resolve(strict=True).as_uri() + '?mode=ro', uri=True, timeout=.5)) as db:
        db.row_factory = sqlite3.Row
        if route == '/v1/plans':
            rows = db.execute('SELECT id,goal,status,created_at,updated_at FROM core2_plans ORDER BY created_at DESC LIMIT 50')
            return {'contract': 1, 'extension': 'planning2', 'plans': [dict(row) for row in rows]}
        if re.fullmatch(r'/v1/plans/[0-9a-f]{32}', route):
            identity = route.rsplit('/', 1)[-1]
            row = db.execute('SELECT id,goal,status,created_at,updated_at FROM core2_plans WHERE id=?', (identity,)).fetchone()
            if not row:
                return None
            result = dict(row)
            result['steps'] = [dict(step) for step in db.execute('SELECT step_id,ordinal,tool,agent,permission,status,attempts FROM core2_plan_steps WHERE plan_id=? ORDER BY ordinal LIMIT 24', (identity,))]
            return {'contract': 1, 'extension': 'planning2', 'plan': result}
    return None
