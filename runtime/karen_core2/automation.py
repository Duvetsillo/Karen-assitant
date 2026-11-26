"""Opt-in persistent read-only schedules over Plans; no generated shell or new service."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import threading
import time
import uuid

from core_resources import microphone_guard, ResourceBusy
from .privacy import ASSIGNMENT, seal, unseal
from .automation_policy import conditions as validate_conditions, window, in_window, metrics_needed, evaluate, read_metrics

TRIGGER_TOPICS = frozenset({'memory.conflict', 'obsidian.note.changed', 'obsidian.index.updated', 'resource.pressure', 'gaming.ended'})


def instant(value):
    if not isinstance(value, str):
        raise ValueError('La fecha debe ser texto ISO con zona horaria.')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('Fecha de automatización inválida.') from None
    if parsed.utcoffset() is None:
        raise ValueError('La fecha debe incluir zona horaria.')
    return parsed.astimezone(timezone.utc)


class Automations:
    def __init__(self, plans, *, mode=lambda: 'normal', events=None, clock=None, probe=read_metrics):
        self.plans, self.mode, self.events = plans, mode, events
        self._stop = threading.Event()
        self._thread = None
        self._active = None
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.probe = probe
        self._subscriptions = []
        with plans.engine._connect() as db:
            row = db.execute("SELECT value FROM core2_meta WHERE key='automation_version'").fetchone()
            if row and row[0] != '1':
                raise ValueError('Versión de automatizaciones incompatible.')
            db.execute("INSERT OR IGNORE INTO core2_meta VALUES('automation_version','1')")
            db.execute('''CREATE TABLE IF NOT EXISTS core2_schedules (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, next_run TEXT NOT NULL, interval_seconds INTEGER,
                retries INTEGER NOT NULL, enabled INTEGER NOT NULL, payload TEXT NOT NULL, last_status TEXT)''')
            db.execute('''CREATE TABLE IF NOT EXISTS core2_schedule_runs (
                schedule_id TEXT NOT NULL, due_at TEXT NOT NULL, attempt INTEGER NOT NULL,
                plan_id TEXT, status TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(schedule_id,due_at))''')
            version = db.execute("SELECT value FROM core2_meta WHERE key='automation_policy_version'").fetchone()
            if version and version[0] != '1':
                raise ValueError('Versión de políticas de automatización incompatible.')
            db.execute("INSERT OR IGNORE INTO core2_meta VALUES('automation_policy_version','1')")
            db.execute('''CREATE TABLE IF NOT EXISTS core2_schedule_policy (
                schedule_id TEXT PRIMARY KEY,conditions TEXT NOT NULL,event_topic TEXT,event_code TEXT,event_entity TEXT,
                cooldown_seconds INTEGER NOT NULL,pending_at TEXT,accepted_at TEXT)''')
            db.execute('''CREATE TABLE IF NOT EXISTS core2_schedule_event_seen (
                schedule_id TEXT,event_id TEXT,received_at TEXT NOT NULL,PRIMARY KEY(schedule_id,event_id))''')
            db.execute('CREATE TABLE IF NOT EXISTS core2_automation_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')

    @staticmethod
    def _event_config(value):
        if value is None:
            return None
        if (not isinstance(value, dict) or set(value) - {'topic', 'code', 'entity_id', 'cooldown_seconds'}
                or not isinstance(value.get('topic'), str) or value['topic'] not in TRIGGER_TOPICS):
            raise ValueError('Trigger fuera de los eventos permitidos.')
        if 'code' in value and (not isinstance(value['code'], str) or not re.fullmatch('[a-z][a-z0-9_]{0,39}', value['code'])):
            raise ValueError('Filtro de código inválido.')
        if 'entity_id' in value and (not isinstance(value['entity_id'], str) or not re.fullmatch('[0-9a-f]{32,64}', value['entity_id'])):
            raise ValueError('Filtro de entidad inválido.')
        seconds = value.get('cooldown_seconds', 60)
        if type(seconds) is not int or not 60 <= seconds <= 86400:
            raise ValueError('Cooldown permitido: 60 a 86400 segundos.')
        return {**value, 'cooldown_seconds': seconds}

    def quiet(self, *, start=None, end=None, offset_minutes=None):
        config = None
        if start is not None or end is not None or offset_minutes is not None:
            config = window({'start': start, 'end': end, **({'offset_minutes': offset_minutes} if offset_minutes is not None else {})})
        with self.plans.engine._connect() as db:
            if config is None:
                db.execute("DELETE FROM core2_automation_settings WHERE key='quiet_hours'")
            else:
                db.execute("INSERT OR REPLACE INTO core2_automation_settings VALUES('quiet_hours',?)", (json.dumps(config),))
        return {'quiet_hours': config}

    def policy(self, *, id):
        with self.plans.engine._connect() as db:
            if not isinstance(id, str) or not db.execute('SELECT 1 FROM core2_schedules WHERE id=?', (id,)).fetchone():
                raise ValueError('Automatización desconocida.')
            row = db.execute('SELECT * FROM core2_schedule_policy WHERE schedule_id=?', (id,)).fetchone()
        return dict(row) if row else {'schedule_id': id, 'conditions': '{}', 'event_topic': None}

    def simulate(self, recipe):
        plan = self.plans.validate(recipe)
        return {'simulation': True, 'executed': False, 'steps': [
            {'tool': step['tool'], 'permission': step['permission']} for step in plan['steps']]}

    def _recipe(self, recipe):
        raw = json.dumps(recipe, ensure_ascii=False, allow_nan=False)
        if len(raw.encode('utf-8')) > 65536 or ASSIGNMENT.search(raw) or 'PRIVATE KEY' in raw:
            raise ValueError('Receta demasiado grande o con posibles credenciales.')
        recipe = json.loads(raw)
        plan = self.plans.validate(recipe)
        if any(step['permission'] != 'read' for step in plan['steps']):
            raise ValueError('Solo se programan herramientas READ. Simula y ejecuta escrituras con aprobación por paso.')
        return recipe

    def create(self, *, name, recipe, due_at=None, interval_seconds=None, retries=0, conditions=None, event=None):
        if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or any(ord(c) < 32 for c in name)
                or ASSIGNMENT.search(name)):
            raise ValueError('Nombre de automatización inválido.')
        if interval_seconds is not None and (type(interval_seconds) is not int or not 60 <= interval_seconds <= 31536000):
            raise ValueError('Intervalo permitido: 60 a 31536000 segundos.')
        if type(retries) is not int or not 0 <= retries <= 2:
            raise ValueError('Reintentos permitidos: 0 a 2.')
        selected_conditions = validate_conditions(conditions)
        event = self._event_config(event)
        if event is None and due_at is None or event is not None and interval_seconds is not None:
            raise ValueError('Usa fecha/intervalo o un evento sin intervalo.')
        due = instant(due_at).isoformat() if due_at is not None else self.clock().astimezone(timezone.utc).isoformat()
        payload = seal(self._recipe(recipe))
        identity = uuid.uuid4().hex
        with self.plans.engine._connect() as db:
            if db.execute('SELECT count(*) FROM core2_schedules').fetchone()[0] >= 100:
                raise ValueError('Límite de 100 automatizaciones; reutiliza las existentes.')
            db.execute('INSERT INTO core2_schedules VALUES(?,?,?,?,?,1,?,NULL)',
                       (identity, name.strip(), due, interval_seconds, retries, payload))
            db.execute('INSERT INTO core2_schedule_policy VALUES(?,?,?,?,?,?,NULL,NULL)',
                       (identity, json.dumps(selected_conditions), event['topic'] if event else None,
                        event.get('code') if event else None, event.get('entity_id') if event else None,
                        event['cooldown_seconds'] if event else 60))
        if self.events:
            self.events.emit('task.created', entity_id=identity, code='scheduled')
        return {**next(row for row in self.list() if row['id'] == identity),
                'runner_active': bool(self._thread and self._thread.is_alive())}

    def list(self):
        with self.plans.engine._connect() as db:
            return [dict(row) for row in db.execute('''SELECT s.id,s.name,s.next_run,s.interval_seconds,s.retries,s.enabled,s.last_status,
                p.event_topic FROM core2_schedules s LEFT JOIN core2_schedule_policy p ON p.schedule_id=s.id ORDER BY s.next_run''')]

    def listen(self):
        if self.events and not self._subscriptions and not self._stop.is_set():
            self._subscriptions = [self.events.subscribe(topic, self.capture_event) for topic in sorted(TRIGGER_TOPICS)]

    def capture_event(self, event):
        if (not isinstance(event, dict) or set(event) != {'id', 'topic', 'entity_id', 'code', 'at'}
                or not isinstance(event['topic'], str) or event['topic'] not in TRIGGER_TOPICS
                or not isinstance(event['id'], str) or not re.fullmatch('[0-9a-f]{32}', event['id'])
                or not isinstance(event['code'], str) or not re.fullmatch('[a-z][a-z0-9_]{0,39}', event['code'])
                or event['entity_id'] is not None and (not isinstance(event['entity_id'], str) or not re.fullmatch('[0-9a-f]{32,64}', event['entity_id']))):
            raise ValueError('Evento de automatización inválido.')
        instant(event['at'])
        if self._stop.is_set():
            return {'queued': 0, 'reason': 'closed'}
        stamp = self.clock().astimezone(timezone.utc).isoformat()
        with self.plans.engine._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            # Do not form loops or chains from scheduled tools, including other instances.
            if db.execute("SELECT 1 FROM core2_schedule_runs r JOIN core2_plans p ON p.id=r.plan_id WHERE r.status='running' AND p.status='running' LIMIT 1").fetchone():
                return {'queued': 0, 'reason': 'scheduled_work_active'}
            rows = db.execute('''SELECT s.id,s.next_run,p.* FROM core2_schedules s JOIN core2_schedule_policy p ON p.schedule_id=s.id
                WHERE s.enabled=1 AND p.event_topic=? AND (p.event_code IS NULL OR p.event_code=?)
                AND (p.event_entity IS NULL OR p.event_entity=?)''', (event['topic'], event['code'], event['entity_id'])).fetchall()
            queued = 0
            for row in rows:
                if row['pending_at'] or row['next_run'] > stamp:
                    continue
                if db.execute('SELECT 1 FROM core2_schedule_event_seen WHERE schedule_id=? AND event_id=?', (row['id'], event['id'])).fetchone():
                    continue
                pending = stamp
                if row['accepted_at'] and pending <= row['accepted_at']:
                    pending = (instant(row['accepted_at']) + timedelta(microseconds=1)).isoformat()
                db.execute('UPDATE core2_schedule_policy SET pending_at=?,accepted_at=? WHERE schedule_id=?', (pending, pending, row['id']))
                db.execute('UPDATE core2_schedules SET next_run=? WHERE id=?', (pending, row['id']))
                db.execute('INSERT INTO core2_schedule_event_seen VALUES(?,?,?)', (row['id'], event['id'], stamp))
                queued += 1
            db.execute('''DELETE FROM core2_schedule_event_seen WHERE rowid NOT IN
                (SELECT rowid FROM core2_schedule_event_seen ORDER BY received_at DESC LIMIT 1000)''')
        return {'queued': queued}

    def enable(self, *, id, enabled):
        if type(enabled) is not bool or not isinstance(id, str):
            raise ValueError('ID y booleano enabled requeridos.')
        with self.plans.engine._connect() as db:
            if db.execute('UPDATE core2_schedules SET enabled=? WHERE id=?', (int(enabled), id)).rowcount != 1:
                raise ValueError('Automatización desconocida.')
        if not enabled and self._active and self._active[0] == id:
            self.plans.cancel(self._active[1])
        return {'id': id, 'enabled': enabled}

    def history(self):
        with self.plans.engine._connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM core2_schedule_runs ORDER BY updated_at DESC LIMIT 100')]

    def status(self):
        with self.plans.engine._connect() as db:
            enabled = db.execute('SELECT count(*) FROM core2_schedules WHERE enabled=1').fetchone()[0]
        return {'watching': bool(self._thread and self._thread.is_alive()), 'enabled_schedules': enabled,
                'active_schedule': self._active[0] if self._active else None, 'permissions': 'read_only'}

    def tick(self, *, dry_run=False, now=None):
        if type(dry_run) is not bool:
            raise ValueError('dry_run debe ser booleano.')
        current = instant(now) if now is not None else self.clock().astimezone(timezone.utc)
        try:
            with microphone_guard(self.plans.path.with_suffix('.automation.lock')):
                mode = self.mode()
                if mode not in {'normal', 'do_not_disturb'}:
                    return {'deferred': 'gaming' if mode == 'gaming' else 'mode_unavailable', 'runs': []}
                with self.plans.engine._connect() as db:
                    quiet = db.execute("SELECT value FROM core2_automation_settings WHERE key='quiet_hours'").fetchone()
                    if quiet and in_window(current, window(json.loads(quiet[0]))):
                        return {'deferred': 'quiet_hours', 'runs': []}
                    due = [dict(row) for row in db.execute('''SELECT s.*,p.conditions,p.event_topic,p.pending_at,p.cooldown_seconds,p.accepted_at
                        FROM core2_schedules s LEFT JOIN core2_schedule_policy p ON p.schedule_id=s.id
                        WHERE s.enabled=1 AND s.next_run<=? AND (p.event_topic IS NULL OR p.pending_at IS NOT NULL)
                        ORDER BY s.next_run LIMIT 100''', (current.isoformat(),))]
                results = []
                metrics = {}
                sampled_at, attempted = 0.0, 0
                for row in due:
                    if self._stop.is_set() or attempted >= 10:
                        break
                    current = instant(now) if now is not None else self.clock().astimezone(timezone.utc)
                    mode = self.mode()
                    if mode not in {'normal', 'do_not_disturb'}:
                        return {'deferred': 'gaming' if mode == 'gaming' else 'mode_unavailable', 'runs': results}
                    with self.plans.engine._connect() as db:
                        quiet = db.execute("SELECT value FROM core2_automation_settings WHERE key='quiet_hours'").fetchone()
                        enabled = db.execute('SELECT enabled FROM core2_schedules WHERE id=?', (row['id'],)).fetchone()
                    if not enabled or not enabled[0]:
                        continue
                    if quiet and in_window(current, window(json.loads(quiet[0]))):
                        return {'deferred': 'quiet_hours', 'runs': results}
                    try:
                        selected = validate_conditions(json.loads(row['conditions'] or '{}'))
                        recipe = self._recipe(unseal(row['payload']))
                    except (ValueError, TypeError, KeyError, OSError):
                        if not dry_run:
                            self._finish(row, current, 'blocked')
                        results.append({'schedule_id': row['id'], 'status': 'blocked'})
                        continue
                    deferred = evaluate(selected, current, mode, {})
                    if deferred and deferred != 'metric_unavailable':
                        results.append({'schedule_id': row['id'], 'status': 'deferred', 'reason': deferred})
                        continue
                    if time.monotonic() - sampled_at > 1:
                        metrics.clear()
                    required = metrics_needed(selected) - metrics.keys()
                    if required:
                        try:
                            sampled = self.probe(required)
                            metrics.update({key: sampled.get(key) for key in required} if isinstance(sampled, dict) else {key: None for key in required})
                        except Exception:
                            metrics.update({key: None for key in required})
                        sampled_at = time.monotonic()
                    deferred = evaluate(selected, current, mode, metrics)
                    if deferred:
                        results.append({'schedule_id': row['id'], 'status': 'deferred', 'reason': deferred})
                        continue
                    if dry_run:
                        results.append({'schedule_id': row['id'], **self.simulate(recipe)})
                        attempted += 1
                        continue
                    results.append(self._run(row, recipe, current))
                    attempted += 1
                return {'runs': results}
        except ResourceBusy:
            return {'deferred': 'another_runner', 'runs': []}

    def _run(self, row, recipe, current):
        with self.plans.engine._connect() as db:
            prior = db.execute('SELECT attempt FROM core2_schedule_runs WHERE schedule_id=? AND due_at=?',
                               (row['id'], row['next_run'])).fetchone()
        first = prior['attempt'] if prior else 0
        result = {'status': 'failed'}
        for attempt in range(first, row['retries'] + 1):
            key = 'schedule:' + row['id'] + ':' + hashlib.sha256(row['next_run'].encode()).hexdigest()[:16] + ':' + str(attempt)
            plan = self.plans.create(recipe, request_key=key)
            with self.plans.engine._connect() as db:
                db.execute('''INSERT INTO core2_schedule_runs VALUES(?,?,?,?,?,?) ON CONFLICT(schedule_id,due_at)
                    DO UPDATE SET attempt=excluded.attempt,plan_id=excluded.plan_id,status=excluded.status,updated_at=excluded.updated_at''',
                    (row['id'], row['next_run'], attempt, plan['id'], 'running', current.isoformat()))
            self._active = (row['id'], plan['id'])
            try:
                result = self.plans.run(plan['id'], resume=True, actor='local-scheduler')
            finally:
                self._active = None
            if result['status'] == 'completed' or self._stop.is_set() or result['status'] != 'failed':
                break
        self._finish(row, current, result['status'])
        return {'schedule_id': row['id'], 'plan_id': result.get('id'), 'status': result['status']}

    def _finish(self, row, current, status):
        current = max(current, self.clock().astimezone(timezone.utc))
        due = instant(row['next_run'])
        interval = row['interval_seconds']
        # Coalesce missed occurrences. A restart never causes an unbounded catch-up storm.
        next_run = due + timedelta(seconds=interval * (int((current - due).total_seconds() // interval) + 1)) if interval else due
        enabled = bool(interval) and status not in {'blocked', 'uncertain', 'denied', 'canceled'}
        if row.get('event_topic'):
            next_run = current + timedelta(seconds=row['cooldown_seconds'])
            enabled = status not in {'blocked', 'uncertain', 'denied', 'canceled'}
        with self.plans.engine._connect() as db:
            db.execute('UPDATE core2_schedules SET next_run=?,enabled=CASE WHEN enabled=0 THEN 0 ELSE ? END,last_status=? WHERE id=?',
                       (next_run.isoformat(), int(enabled), status, row['id']))
            if row.get('event_topic'):
                db.execute('UPDATE core2_schedule_policy SET pending_at=NULL WHERE schedule_id=? AND pending_at=?', (row['id'], row['pending_at']))
            db.execute('''INSERT INTO core2_schedule_runs VALUES(?,?,0,NULL,?,?) ON CONFLICT(schedule_id,due_at)
                DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at''',
                (row['id'], row['next_run'], status, current.isoformat()))
            db.execute('''DELETE FROM core2_schedule_runs WHERE rowid NOT IN
                (SELECT rowid FROM core2_schedule_runs ORDER BY updated_at DESC LIMIT 1000)''')
        if self.events:
            self.events.emit('task.completed' if status == 'completed' else 'task.failed', entity_id=row['id'], code='scheduled_' + status)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.listen()
        def watch():
            while not self._stop.is_set():
                try:
                    self.tick()
                except Exception:
                    if self.events:
                        self.events.emit('system.error', code='automation_tick')
                self._stop.wait(30)
        self._thread = threading.Thread(target=watch, name='karen-automations', daemon=True)
        self._thread.start()

    def close(self):
        self._stop.set()
        for unsubscribe in self._subscriptions:
            unsubscribe()
        self._subscriptions.clear()
        active = self._active
        if active:
            self.plans.cancel(active[1])
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)


def command(engine, text):
    if not (text == '/automation' or text.startswith('/automation ')):
        return None
    parts = text.split(maxsplit=2)
    operation = parts[1] if len(parts) > 1 else 'list'
    args = json.loads(parts[2]) if len(parts) > 2 else {}
    handlers = {'list': engine.list, 'create': engine.create, 'enable': engine.enable,
                'history': engine.history, 'tick': engine.tick, 'simulate': engine.simulate,
                'quiet': engine.quiet, 'policy': engine.policy}
    if operation not in handlers or not isinstance(args, dict):
        raise ValueError('Operación de automatización inválida.')
    try:
        return json.dumps(handlers[operation](**args), ensure_ascii=False, indent=2)
    except TypeError as exc:
        raise ValueError('Parámetros de automatización ausentes o desconocidos.') from exc
