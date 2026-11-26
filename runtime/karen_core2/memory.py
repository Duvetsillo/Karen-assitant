"""Typed contextual memory in the existing Core SQLite database."""
from datetime import datetime, timezone
import json
import math
import re
import unicodedata

from karen_memory import MemoryStore
from .privacy import ASSIGNMENT, SECRET

KINDS = {'episodic', 'semantic', 'procedural', 'contextual', 'temporal', 'relational', 'project',
         'user', 'autobiographical', 'prospective'}
STATES = {'VERIFICADO', 'INFERIDO', 'PENDIENTE', 'DESACTUALIZADO'}


def words(value):
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return set(re.findall(r'\w{3,}', normalized))


class ContextMemory:
    def __init__(self, path=None):
        self.base = MemoryStore(path)
        self.path = self.base.path
        self.events = None
        from .music import MusicMemory
        self.music = MusicMemory(self.base)
        with self.base.connect() as db:
            version = db.execute("SELECT value FROM core_meta WHERE key='memory2_version'").fetchone()
            if version and version[0] != '1':
                raise ValueError('Versión de memoria contextual no compatible.')
            db.executescript('''
              INSERT OR IGNORE INTO core_meta VALUES ('memory2_version','1');
              CREATE TABLE IF NOT EXISTS core2_memory (
                memory_id TEXT PRIMARY KEY, kind TEXT NOT NULL, priority INTEGER NOT NULL,
                retired INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS core2_memory_links (
                source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation TEXT NOT NULL,
                PRIMARY KEY(source_id,target_id,relation));
              CREATE TABLE IF NOT EXISTS core2_memory_details (
                memory_id TEXT PRIMARY KEY, state TEXT NOT NULL, confidence REAL NOT NULL,
                tags TEXT NOT NULL, fact_key TEXT, details TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS core2_procedure_runs (
                memory_id TEXT NOT NULL, plan_id TEXT NOT NULL, executed_at TEXT NOT NULL,
                evidence TEXT NOT NULL, PRIMARY KEY(memory_id,plan_id));
              CREATE TRIGGER IF NOT EXISTS core2_memory_delete AFTER DELETE ON core_memories BEGIN
                DELETE FROM core2_memory WHERE memory_id=OLD.id;
                DELETE FROM core2_memory_details WHERE memory_id=OLD.id;
                DELETE FROM core2_memory_links WHERE source_id=OLD.id OR target_id=OLD.id;
                DELETE FROM core2_procedure_runs WHERE memory_id=OLD.id;
              END;
            ''')
        self._retrieval_schema()
        from .memory_portability import MemoryPortability
        self.portability = MemoryPortability(self)

    def _retrieval_schema(self):
        """Additive migration; legacy writers keep the rebuildable index in sync."""
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            version = db.execute("SELECT value FROM core_meta WHERE key='memory_retrieval_version'").fetchone()
            if version:
                if version[0] != '1':
                    raise ValueError('Versión de recuperación de memoria incompatible.')
                return
            db.execute('''CREATE VIRTUAL TABLE core2_memory_search USING fts5(
                memory_id UNINDEXED,body,tokenize='unicode61 remove_diacritics 2')''')
            db.execute('''CREATE TABLE core2_memory_access (
                memory_id TEXT PRIMARY KEY,last_access_at TEXT NOT NULL,access_count INTEGER NOT NULL)''')
            db.execute('INSERT INTO core2_memory_search SELECT id,content FROM core_memories WHERE sensitive=0')
            db.execute('''CREATE TRIGGER core2_memory_search_insert AFTER INSERT ON core_memories WHEN NEW.sensitive=0 BEGIN
                INSERT INTO core2_memory_search VALUES(NEW.id,NEW.content); END''')
            db.execute('''CREATE TRIGGER core2_memory_search_update AFTER UPDATE ON core_memories BEGIN
                DELETE FROM core2_memory_search WHERE memory_id=OLD.id;
                INSERT INTO core2_memory_search SELECT NEW.id,NEW.content WHERE NEW.sensitive=0; END''')
            db.execute('''CREATE TRIGGER core2_memory_search_delete AFTER DELETE ON core_memories BEGIN
                DELETE FROM core2_memory_search WHERE memory_id=OLD.id;
                DELETE FROM core2_memory_access WHERE memory_id=OLD.id; END''')
            db.execute("INSERT INTO core_meta VALUES('memory_retrieval_version','1')")

    def reindex(self):
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM core2_memory_search')
            db.execute('INSERT INTO core2_memory_search SELECT id,content FROM core_memories WHERE sensitive=0')
            return {'indexed': db.execute('SELECT count(*) FROM core2_memory_search').fetchone()[0]}

    def add(self, project, content, *, kind='semantic', status='confirmed', temporary_days=None,
            priority=0, source='user', supersedes=None, state=None, confidence=None,
            tags=(), fact_key=None, details=None):
        project, content = self.base._project(project), self.base._content(content)
        if kind not in KINDS or status not in {'confirmed', 'hypothesis', 'temporary'}:
            raise ValueError('Tipo o estado de memoria desconocido.')
        if type(priority) is not int or not 0 <= priority <= 10:
            raise ValueError('Prioridad de memoria inválida.')
        state = state or ('VERIFICADO' if status == 'confirmed' else 'INFERIDO')
        confidence = (1.0 if state == 'VERIFICADO' else 0.5) if confidence is None else confidence
        if state not in STATES or type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError('Estado o confianza inválidos.')
        if not isinstance(tags, (list, tuple)) or len(tags) > 20 or any(not isinstance(t, str) or not 1 <= len(t) <= 64 for t in tags):
            raise ValueError('Etiquetas inválidas.')
        if fact_key is not None and (not isinstance(fact_key, str) or not re.fullmatch(r'[\w.:-]{1,128}', fact_key)):
            raise ValueError('Clave de hecho inválida.')
        if details is not None and not isinstance(details, dict):
            raise ValueError('Detalles inválidos.')
        encoded = json.dumps({'tags': tags, 'details': details or {}}, ensure_ascii=False, allow_nan=False)
        if len(encoded) > 16000 or ASSIGNMENT.search(encoded) or SECRET.search(encoded) or 'PRIVATE KEY' in encoded:
            raise ValueError('Detalles sensibles o demasiado extensos.')
        if status == 'temporary' and temporary_days is None:
            temporary_days = 1
        if ASSIGNMENT.search(content) or SECRET.search(content) or 'PRIVATE KEY' in content:
            raise ValueError('No se guardan credenciales en la memoria contextual.')
        if source not in {'user', 'verified-plan', 'local-observation'}:
            raise ValueError('Origen de memoria desconocido.')
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('''SELECT * FROM core_memories WHERE id=? AND sensitive=0
                AND (expires_at IS NULL OR expires_at>?)''', (supersedes, datetime.now(timezone.utc).isoformat())).fetchone() if supersedes else None
            if supersedes and (not old or old['project'] != project):
                raise ValueError('El recuerdo reemplazado debe existir en el mismo proyecto.')
            duplicate = db.execute('''SELECT m.*,d.state FROM core_memories m JOIN core2_memory_details d ON d.memory_id=m.id
                WHERE m.fingerprint=?''', (self.base._fingerprint(self.base._project(project), self.base._content(content)),)).fetchone()
            if duplicate:
                if duplicate['sensitive'] or duplicate['expires_at'] and duplicate['expires_at'] <= datetime.now(timezone.utc).isoformat():
                    raise ValueError('Recuerdo duplicado sensible o caducado; requiere revisión.')
                if duplicate['state'] != state:
                    raise ValueError('Recuerdo duplicado con otro estado; requiere revisión.')
            saved = self.base.add(project, content, confirmed=state == 'VERIFICADO', retention_days=temporary_days, _connection=db)
            db.execute('''INSERT INTO core2_memory VALUES (?,?,?,0,?) ON CONFLICT(memory_id) DO UPDATE SET
                          kind=excluded.kind,priority=excluded.priority,retired=0,source=excluded.source''',
                       (saved['id'], kind, priority, source))
            db.execute('INSERT OR IGNORE INTO core2_memory_details VALUES (?,?,?,?,?,?)',
                       (saved['id'], state, confidence, json.dumps(tags), fact_key, json.dumps(details or {}, ensure_ascii=False)))
            conflicts = []
            if fact_key:
                conflicts = db.execute('''SELECT d.memory_id FROM core2_memory_details d
                    JOIN core_memories m ON m.id=d.memory_id JOIN core2_memory c ON c.memory_id=m.id
                    WHERE m.project=? AND d.fact_key=? AND m.id<>? AND c.retired=0
                    AND (m.expires_at IS NULL OR m.expires_at>?)''',
                    (saved['project'], fact_key, saved['id'], datetime.now(timezone.utc).isoformat())).fetchall()
                for conflict in conflicts:
                    db.execute('INSERT OR IGNORE INTO core2_memory_links VALUES (?,?,?)',
                               (saved['id'], conflict[0], 'contradicts'))
            if old and old['id'] != saved['id']:
                db.execute('INSERT OR IGNORE INTO core2_memory_links VALUES (?,?,?)', (saved['id'], old['id'], 'supersedes'))
                db.execute('UPDATE core2_memory SET retired=1 WHERE memory_id=?', (old['id'],))
                db.execute("UPDATE core2_memory_details SET state='DESACTUALIZADO' WHERE memory_id=?", (old['id'],))
                stamp = datetime.now(timezone.utc).isoformat()
                db.execute('UPDATE core_memories SET expires_at=?,updated_at=? WHERE id=?', (stamp, stamp, old['id']))
        if self.events:
            self.events.emit('memory.updated' if duplicate else 'memory.created', entity_id=saved['id'])
            if conflicts:
                self.events.emit('memory.conflict', entity_id=saved['id'])
        return {**saved, 'kind': kind, 'state': state}

    def relate(self, source, target, relation='related'):
        if relation not in {'related', 'supports', 'contradicts', 'uses', 'belongs_to', 'runs_on'} or source == target:
            raise ValueError('Relación inválida.')
        left, right = self.base.get(source), self.base.get(target)
        if not left or not right or left['project'] != right['project']:
            raise ValueError('Ambos recuerdos públicos deben pertenecer al mismo proyecto.')
        with self.base.connect() as db:
            db.execute('INSERT OR IGNORE INTO core2_memory_links VALUES (?,?,?)', (source, target, relation))

    def retrieve(self, project, query='', *, limit=8, confirmed_only=False):
        if (type(limit) is not int or not 1 <= limit <= 20 or not isinstance(query, str)
                or len(query) > 400 or type(confirmed_only) is not bool):
            raise ValueError('Consulta contextual inválida.')
        project = self.base._project(project)
        terms = sorted(words(query))[:16]
        if query.strip() and not terms:
            return []
        expression = ' OR '.join('"' + term.replace('"', '""') + '"' for term in terms)
        with self.base.connect() as db:
            joins = ' JOIN core2_memory_search ON core2_memory_search.memory_id=m.id' if terms else ''
            match = ' AND core2_memory_search MATCH ?' if terms else ''
            order = 'bm25(core2_memory_search),' if terms else ''
            params = [project, datetime.now(timezone.utc).isoformat(), int(confirmed_only)] + ([expression] if terms else [])
            rows = [self.base._row(row) for row in db.execute('''SELECT m.* FROM core_memories m
                LEFT JOIN core2_memory c ON c.memory_id=m.id LEFT JOIN core2_memory_details d ON d.memory_id=m.id'''
                + joins + ''' WHERE m.project=? AND m.sensitive=0 AND (m.expires_at IS NULL OR m.expires_at>?)
                AND COALESCE(c.retired,0)=0 AND COALESCE(d.state,'')!='DESACTUALIZADO'
                AND (?=0 OR m.status='confirmed' AND COALESCE(d.state,'VERIFICADO')='VERIFICADO')'''
                + match + ' ORDER BY ' + order + 'm.updated_at DESC,m.id DESC LIMIT 200', params)]
            if not rows:
                return []
            ids = [row['id'] for row in rows]
            placeholders = ','.join('?' for _ in ids)
            metadata = {row['memory_id']: dict(row) for row in db.execute(
                'SELECT * FROM core2_memory WHERE memory_id IN (' + placeholders + ')', ids)}
            details = {row['memory_id']: dict(row) for row in db.execute(
                'SELECT * FROM core2_memory_details WHERE memory_id IN (' + placeholders + ')', ids)}
            conflicts = set()
            for link in db.execute('''SELECT l.source_id,l.target_id FROM core2_memory_links l
                JOIN core_memories a ON a.id=l.source_id JOIN core_memories b ON b.id=l.target_id
                WHERE a.project=? AND b.project=a.project AND l.relation='contradicts' AND a.sensitive=0 AND b.sensitive=0
                AND (a.expires_at IS NULL OR a.expires_at>?) AND (b.expires_at IS NULL OR b.expires_at>?)
                AND (l.source_id IN (''' + placeholders + ') OR l.target_id IN (' + placeholders + '))',
                [project, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()] + ids + ids):
                conflicts.update(link)
        terms, scored = set(terms), []
        for index, row in enumerate(rows):
            if ASSIGNMENT.search(row['content']) or SECRET.search(row['content']) or 'PRIVATE KEY' in row['content']:
                continue
            meta = metadata.get(row['id'], {'kind': 'project', 'priority': 0, 'retired': 0, 'source': 'user'})
            detail = details.get(row['id'], {})
            state = detail.get('state', 'VERIFICADO' if row['status'] == 'confirmed' else 'INFERIDO')
            if meta['retired'] or state == 'DESACTUALIZADO' or (confirmed_only and (row['status'] != 'confirmed' or state != 'VERIFICADO' or row['id'] in conflicts)):
                continue
            overlap = len(terms & words(row['content']))
            if terms and not overlap:
                continue
            score = overlap * 20 + meta['priority'] + (10 if row['status'] == 'confirmed' else 0) + 1 / (index + 1)
            scored.append((score, {**row, 'kind': meta['kind'], 'source': meta['source'],
                                   'relevance': score, 'priority': meta['priority'],
                                   'state': state, 'confidence': detail.get('confidence', 1.0 if row['status'] == 'confirmed' else .5),
                                   'tags': json.loads(detail.get('tags', '[]')), 'has_contradictions': row['id'] in conflicts}))
        result = [row for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
        stamp = datetime.now(timezone.utc).isoformat()
        visible = []
        with self.base.connect() as db:
            for row in result:
                current = db.execute('SELECT content,status,sensitive,expires_at FROM core_memories WHERE id=?', (row['id'],)).fetchone()
                if (not current or current['sensitive'] or current['content'] != row['content'] or
                        current['expires_at'] and current['expires_at'] <= stamp or confirmed_only and current['status'] != 'confirmed'):
                    continue
                db.execute('''INSERT INTO core2_memory_access VALUES(?,?,1) ON CONFLICT(memory_id)
                    DO UPDATE SET last_access_at=excluded.last_access_at,access_count=access_count+1''', (row['id'], stamp))
                row.update(dict(db.execute('SELECT last_access_at,access_count FROM core2_memory_access WHERE memory_id=?', (row['id'],)).fetchone()))
                visible.append(row)
        return visible

    def record_procedure(self, plan, project='Karen'):
        if (plan.get('status') != 'completed' or not plan.get('id') or not plan.get('steps') or
                not all(step['status'] == 'completed' and step.get('result') is not None for step in plan['steps'])):
            raise ValueError('Solo se recuerdan procedimientos terminados y verificados.')
        from .privacy import fingerprint
        shape = [{'tool': s['tool'], 'arguments': s.get('arguments', {}), 'depends': s.get('depends', [])} for s in plan['steps']]
        description = ('Procedimiento verificado: ' + plan['goal'][:300] + '. Herramientas: ' +
                       ', '.join(step['tool'] for step in plan['steps']) + '. Referencia: ' + fingerprint(shape)[:16])
        details = {'name': plan['goal'][:120], 'objective': plan['goal'],
                   'steps': [{'tool': s['tool'], 'label': s.get('label', s['tool']), 'depends': s.get('depends', [])} for s in plan['steps']],
                   'tools': list(dict.fromkeys(s['tool'] for s in plan['steps'])),
                   'prerequisites': ['Herramientas registradas y disponibles'],
                   'permissions': list(dict.fromkeys(s.get('permission', 'unknown') for s in plan['steps'])),
                   'risks': ['Revisar riesgos y permisos antes de cada ejecución'],
                   'expected_result': 'Todos los verificadores de pasos deben aprobar',
                   'actual_result': 'Plan completado con evidencia de cada paso',
                   'software_versions': {'karen_core': 2}}
        saved = self.add(project, description, kind='procedural', source='verified-plan', priority=5, details=details)
        # Store hashes, not potentially private outputs. Re-saving a plan never counts as another execution.
        evidence = [{'tool': s['tool'], 'result_hash': fingerprint(s['result'])} for s in plan['steps']]
        with self.base.connect() as db:
            db.execute('INSERT OR IGNORE INTO core2_procedure_runs VALUES (?,?,?,?)',
                       (saved['id'], plan['id'], plan.get('updated_at', datetime.now(timezone.utc).isoformat()), json.dumps(evidence)))
        return saved

    def procedure(self, memory_id):
        row = self.base.get(memory_id)
        if not row:
            return None
        with self.base.connect() as db:
            meta = db.execute('SELECT kind FROM core2_memory WHERE memory_id=?', (memory_id,)).fetchone()
            detail = db.execute('SELECT details FROM core2_memory_details WHERE memory_id=?', (memory_id,)).fetchone()
            if not meta or meta['kind'] != 'procedural' or not detail:
                return None
            runs = [dict(r) for r in db.execute('SELECT plan_id,executed_at,evidence FROM core2_procedure_runs WHERE memory_id=? ORDER BY executed_at', (memory_id,))]
        return {**json.loads(detail['details']), **row, 'successful_runs': len(runs), 'executions': runs,
                'verified': bool(runs), 'basis': 'local_verified_runs' if runs else 'reported_or_user_data'}

    def history(self, memory_id):
        # Current sensitivity gates all historical versions, including previously public content.
        with self.base.connect() as db:
            rows = db.execute('''SELECT v.* FROM core_memory_versions v JOIN core_memories m ON m.id=v.memory_id
                WHERE v.memory_id=? AND m.sensitive=0 AND v.sensitive=0 ORDER BY v.revision''', (memory_id,))
            return [dict(r) for r in rows if not SECRET.search(r['content']) and not ASSIGNMENT.search(r['content']) and 'PRIVATE KEY' not in r['content']]

    def graph(self, project):
        nodes = self.retrieve(project, limit=20)
        ids = {n['id'] for n in nodes}
        with self.base.connect() as db:
            links = [dict(r) for r in db.execute('''SELECT l.* FROM core2_memory_links l
                JOIN core_memories m ON m.id=l.source_id WHERE m.project=?''', (project,))
                if r['source_id'] in ids and r['target_id'] in ids]
        return {'nodes': nodes, 'links': links, 'limit': 20}

    def timeline(self, project, *, since=None, until=None, kind=None, limit=100):
        project = self.base._project(project)
        if type(limit) is not int or not 1 <= limit <= 500 or kind is not None and kind not in KINDS:
            raise ValueError('Filtro temporal inválido.')
        for value in (since, until):
            if value is not None and (not isinstance(value, str) or datetime.fromisoformat(value).utcoffset() is None):
                raise ValueError('Fecha temporal requiere zona horaria.')
        since = datetime.fromisoformat(since).astimezone(timezone.utc).isoformat() if since else None
        until = datetime.fromisoformat(until).astimezone(timezone.utc).isoformat() if until else None
        with self.base.connect() as db:
            rows = db.execute('''SELECT v.*,COALESCE(c.kind,'project') AS kind FROM core_memory_versions v
                JOIN core_memories m ON m.id=v.memory_id LEFT JOIN core2_memory c ON c.memory_id=m.id
                WHERE v.project=? AND m.sensitive=0 AND v.sensitive=0
                AND (? IS NULL OR v.recorded_at>=?) AND (? IS NULL OR v.recorded_at<=?)
                AND (? IS NULL OR COALESCE(c.kind,'project')=?) ORDER BY v.revision DESC LIMIT ?''',
                (project, since, since, until, until, kind, kind, limit))
            return [dict(r) for r in rows if not SECRET.search(r['content']) and not ASSIGNMENT.search(r['content']) and 'PRIVATE KEY' not in r['content']]

    def export_bundle(self, project):
        """Public project snapshot, including historical text and procedure hashes; no secrets."""
        project = self.base._project(project)
        with self.base.connect() as db:
            db.execute('BEGIN')
            memories = [dict(r) for r in db.execute('''SELECT m.*,c.kind,c.priority,c.source,c.retired,
                d.state,d.confidence,d.tags,d.fact_key,d.details,a.last_access_at,a.access_count FROM core_memories m
                LEFT JOIN core2_memory c ON c.memory_id=m.id LEFT JOIN core2_memory_details d ON d.memory_id=m.id
                LEFT JOIN core2_memory_access a ON a.memory_id=m.id
                WHERE m.project=? AND m.sensitive=0''', (project,))
                if not SECRET.search(r['content']) and not ASSIGNMENT.search(r['content']) and 'PRIVATE KEY' not in r['content']]
            ids = {r['id'] for r in memories}
            versions = [dict(r) for r in db.execute('SELECT * FROM core_memory_versions WHERE project=? AND sensitive=0', (project,))
                        if r['memory_id'] in ids and not SECRET.search(r['content']) and not ASSIGNMENT.search(r['content']) and 'PRIVATE KEY' not in r['content']]
            links = [dict(r) for r in db.execute('''SELECT l.* FROM core2_memory_links l
                JOIN core_memories m ON m.id=l.source_id WHERE m.project=?''', (project,))
                if r['source_id'] in ids and r['target_id'] in ids]
            runs = [dict(r) for r in db.execute('''SELECT r.* FROM core2_procedure_runs r
                JOIN core_memories m ON m.id=r.memory_id WHERE m.project=?''', (project,)) if r['memory_id'] in ids]
            reported = [{'memory_id': r['memory_id'], 'claims': json.loads(r['claims'])} for r in db.execute('''
                SELECT r.memory_id,r.claims FROM core2_memory_reported r JOIN core_memories m ON m.id=r.memory_id
                WHERE m.project=? AND m.sensitive=0 ORDER BY r.memory_id,r.claim_hash''', (project,)) if r['memory_id'] in ids]
        result = {'contract': 'memory-engine-1', 'project': project, 'memories': memories,
                  'versions': versions, 'links': links, 'procedure_runs': runs}
        if reported:
            result['reported'] = reported
        return result

    def consolidate(self, project):
        """Read-only proposals. Never merges, deletes, or promotes claims automatically."""
        graph = self.graph(project)
        return {'mode': 'propose', 'requires_review': True,
                'contradictions': [l for l in graph['links'] if l['relation'] == 'contradicts'],
                'pending': [n['id'] for n in graph['nodes'] if n['state'] in {'PENDIENTE', 'INFERIDO'}]}
