"""Read-only public Core v1 extension; never decrypt plan arguments or results."""
from contextlib import closing
from pathlib import Path
import re
import sqlite3


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
