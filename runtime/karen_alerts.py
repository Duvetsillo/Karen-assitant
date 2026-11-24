"""Local alert rules. Only explicit, fresh numeric observations can trigger alerts."""

from datetime import datetime, timezone, timedelta
from contextlib import closing, contextmanager
import math
import os
from pathlib import Path
import re
import sqlite3
import uuid


DEFAULT_PATH = Path(__file__).resolve().parent / '.private' / 'karen-alerts.sqlite3'
PRIORITIES = {'low', 'normal', 'high', 'critical'}
OPERATORS = {'>', '>=', '<', '<='}
KEY = re.compile(r'[a-z][a-z0-9_.-]{0,63}\Z')


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('La fecha debe incluir zona horaria.')
    return value.astimezone(timezone.utc)


def _minutes(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value):
        raise ValueError('Usa horario HH:MM de 24 horas.')
    hour, minute = map(int, value.split(':'))
    return hour * 60 + minute


def _breached(operator, value, threshold):
    return {'>': value > threshold, '>=': value >= threshold,
            '<': value < threshold, '<=': value <= threshold}[operator]


class AlertEngine:
    """Persist rules and alert state, without polling devices or sending notifications."""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            meta = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alert_meta'").fetchone()
            if meta:
                version = db.execute("SELECT value FROM alert_meta WHERE key='schema_version'").fetchone()
                if not version or version[0] != '1':
                    raise ValueError('Versión de alertas no compatible.')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS alert_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT OR IGNORE INTO alert_meta VALUES ('schema_version','1');
                CREATE TABLE IF NOT EXISTS alert_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS alert_sources (source TEXT PRIMARY KEY, enabled INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY, source TEXT NOT NULL, metric TEXT NOT NULL,
                    operator TEXT NOT NULL, threshold REAL NOT NULL, priority TEXT NOT NULL,
                    cooldown_seconds INTEGER NOT NULL, label TEXT NOT NULL, enabled INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS alert_state (
                    rule_id TEXT PRIMARY KEY REFERENCES alert_rules(id), breached INTEGER NOT NULL,
                    pending INTEGER NOT NULL, last_notified_at TEXT, last_seen_at TEXT);
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY, rule_id TEXT NOT NULL REFERENCES alert_rules(id),
                    priority TEXT NOT NULL, label TEXT NOT NULL, value REAL NOT NULL,
                    observed_at TEXT NOT NULL, created_at TEXT NOT NULL,
                    status TEXT NOT NULL, resolved_at TEXT);
                CREATE INDEX IF NOT EXISTS alert_rule_source ON alert_rules(source,metric,enabled);
                CREATE INDEX IF NOT EXISTS alert_history ON alerts(created_at DESC);
            ''')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def add_rule(self, source, metric, operator, threshold, *, priority='normal',
                 cooldown_seconds=300, label=None):
        if not isinstance(source, str) or not KEY.fullmatch(source):
            raise ValueError('Fuente inválida.')
        if not isinstance(metric, str) or not KEY.fullmatch(metric):
            raise ValueError('Métrica inválida.')
        if operator not in OPERATORS or priority not in PRIORITIES:
            raise ValueError('Operador o prioridad inválidos.')
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
            raise ValueError('Umbral numérico inválido.')
        if type(cooldown_seconds) is not int or not 0 <= cooldown_seconds <= 86400:
            raise ValueError('Cooldown inválido.')
        if label is None:
            label = f'{source}.{metric} {operator} {threshold}'
        if not isinstance(label, str) or not 1 <= len(label) <= 120 or any(ord(c) < 32 for c in label):
            raise ValueError('Etiqueta inválida.')
        rule_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute('INSERT INTO alert_rules VALUES (?,?,?,?,?,?,?,?,1)',
                       (rule_id, source, metric, operator, float(threshold), priority,
                        cooldown_seconds, label))
            db.execute('INSERT INTO alert_state VALUES (?,0,0,NULL,NULL)', (rule_id,))
        return rule_id

    def set_rule_enabled(self, rule_id, enabled):
        if type(enabled) is not bool:
            raise ValueError('Estado inválido.')
        with self._connect() as db:
            updated = db.execute('UPDATE alert_rules SET enabled=? WHERE id=?',
                                 (int(enabled), rule_id)).rowcount
            if not updated:
                raise KeyError('Regla desconocida.')
            if not enabled:
                db.execute('UPDATE alert_state SET breached=0,pending=0 WHERE rule_id=?', (rule_id,))
                db.execute("UPDATE alerts SET status='resolved',resolved_at=? "
                           "WHERE rule_id=? AND status IN ('active','acknowledged')",
                           (datetime.now(timezone.utc).isoformat(), rule_id))

    def set_source_enabled(self, source, enabled):
        if not isinstance(source, str) or not KEY.fullmatch(source) or type(enabled) is not bool:
            raise ValueError('Fuente o estado inválidos.')
        with self._connect() as db:
            db.execute('INSERT OR REPLACE INTO alert_sources VALUES (?,?)', (source, int(enabled)))
            if not enabled:
                db.execute('''UPDATE alert_state SET breached=0,pending=0 WHERE rule_id IN
                    (SELECT id FROM alert_rules WHERE source=?)''', (source,))
                db.execute('''UPDATE alerts SET status='resolved',resolved_at=? WHERE rule_id IN
                    (SELECT id FROM alert_rules WHERE source=?)
                    AND status IN ('active','acknowledged')''',
                           (datetime.now(timezone.utc).isoformat(), source))

    def rules(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM alert_rules ORDER BY rowid')]

    def set_quiet_hours(self, start=None, end=None):
        if (start is None) != (end is None):
            raise ValueError('Indica inicio y fin, o ambos vacíos.')
        if start is not None:
            _minutes(start)
            _minutes(end)
        with self._connect() as db:
            if start is None:
                db.execute("DELETE FROM alert_settings WHERE key IN ('quiet_start','quiet_end')")
            else:
                db.execute("INSERT OR REPLACE INTO alert_settings VALUES ('quiet_start',?)", (start,))
                db.execute("INSERT OR REPLACE INTO alert_settings VALUES ('quiet_end',?)", (end,))

    def set_gaming(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Modo Gaming inválido.')
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO alert_settings VALUES ('gaming',?)",
                       ('1' if enabled else '0',))

    @staticmethod
    def _shared_mode():
        configured = os.getenv('KAREN_CORE_DB')
        if not configured:
            return None
        path = Path(configured)
        if not path.is_absolute() or not path.is_file():
            return None
        try:
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
                version = db.execute("SELECT value FROM core_meta WHERE key='schema_version'").fetchone()
                if not version or version[0] != '1':
                    return None
                row = db.execute("SELECT value FROM preferences WHERE key='core.mode'").fetchone()
                return row[0] if row and row[0] in {'normal', 'gaming', 'do_not_disturb'} else None
        except (OSError, sqlite3.Error):
            return None

    @staticmethod
    def _quiet(now, settings):
        if 'quiet_start' not in settings or 'quiet_end' not in settings:
            return False
        start, end = _minutes(settings['quiet_start']), _minutes(settings['quiet_end'])
        if start == end:
            return False
        current = now.hour * 60 + now.minute
        return start <= current < end if start < end else current >= start or current < end

    def observe(self, source, metric, value, *, observed_at=None, now=None):
        """Return newly emitted alerts. A stale reading cannot create or resolve one."""
        if not isinstance(source, str) or not KEY.fullmatch(source) or not isinstance(metric, str) or not KEY.fullmatch(metric):
            raise ValueError('Fuente o métrica inválida.')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Lectura numérica inválida.')
        current = _utc(now or datetime.now().astimezone())
        observed = _utc(observed_at or current)
        if current - observed > timedelta(minutes=5) or observed - current > timedelta(seconds=30):
            raise ValueError('Lectura obsoleta o futura.')
        local_now = (now or datetime.now().astimezone())
        shared_mode = self._shared_mode()
        emitted = []
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            source_state = db.execute('SELECT enabled FROM alert_sources WHERE source=?', (source,)).fetchone()
            if source_state and not source_state['enabled']:
                return []
            settings = dict(db.execute('SELECT key,value FROM alert_settings'))
            quiet = self._quiet(local_now, settings)
            gaming = settings.get('gaming') == '1' or shared_mode in {'gaming', 'do_not_disturb'}
            rows = db.execute('''SELECT r.*,s.breached,s.pending,s.last_notified_at,s.last_seen_at
                FROM alert_rules r JOIN alert_state s ON s.rule_id=r.id
                WHERE r.source=? AND r.metric=? AND r.enabled=1''', (source, metric)).fetchall()
            for row in rows:
                # Ignore out-of-order samples for this rule.
                if row['last_seen_at'] and observed.isoformat() <= row['last_seen_at']:
                    continue
                if not _breached(row['operator'], value, row['threshold']):
                    db.execute('UPDATE alert_state SET breached=0,pending=0,last_seen_at=? WHERE rule_id=?',
                               (observed.isoformat(), row['id']))
                    db.execute("UPDATE alerts SET status='resolved',resolved_at=? "
                               "WHERE rule_id=? AND status IN ('active','acknowledged')",
                               (current.isoformat(), row['id']))
                    continue
                blocked = (row['priority'] != 'critical' and (quiet or gaming))
                if row['last_notified_at']:
                    elapsed = (current - datetime.fromisoformat(row['last_notified_at'])).total_seconds()
                    blocked = blocked or elapsed < row['cooldown_seconds']
                should_emit = (not row['breached'] or row['pending']) and not blocked
                pending = (not row['breached'] or bool(row['pending'])) and blocked
                db.execute('UPDATE alert_state SET breached=1,pending=?,last_seen_at=? WHERE rule_id=?',
                           (int(pending), observed.isoformat(), row['id']))
                if should_emit:
                    alert_id = uuid.uuid4().hex
                    db.execute('''INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?,?)''',
                               (alert_id, row['id'], row['priority'], row['label'], float(value),
                                observed.isoformat(), current.isoformat(), 'active', None))
                    db.execute('UPDATE alert_state SET pending=0,last_notified_at=? WHERE rule_id=?',
                               (current.isoformat(), row['id']))
                    emitted.append({'id': alert_id, 'rule_id': row['id'], 'priority': row['priority'],
                                    'label': row['label'], 'value': float(value),
                                    'observed_at': observed.isoformat()})
        return emitted

    def acknowledge(self, alert_id):
        with self._connect() as db:
            changed = db.execute("UPDATE alerts SET status='acknowledged' WHERE id=? AND status='active'",
                                 (alert_id,)).rowcount
            if not changed and not db.execute('SELECT 1 FROM alerts WHERE id=?', (alert_id,)).fetchone():
                raise KeyError('Alerta desconocida.')
            return bool(changed)

    def history(self, *, status=None, limit=100):
        if status not in {None, 'active', 'acknowledged', 'resolved'}:
            raise ValueError('Estado inválido.')
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Límite inválido.')
        with self._connect() as db:
            if status is None:
                rows = db.execute('SELECT * FROM alerts ORDER BY created_at DESC,rowid DESC LIMIT ?', (limit,))
            else:
                rows = db.execute('SELECT * FROM alerts WHERE status=? ORDER BY created_at DESC,rowid DESC LIMIT ?',
                                  (status, limit))
            return [dict(row) for row in rows]
