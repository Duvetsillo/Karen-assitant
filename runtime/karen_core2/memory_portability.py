"""Portable memory as reported data. Import never trusts external verification claims."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import stat
import uuid

from .privacy import ASSIGNMENT, SECRET, fingerprint

MAX_BYTES = 8 * 1024 * 1024


def strict_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('El JSON contiene claves duplicadas.')
            result[key] = value
        return result
    try:
        value = json.loads(text, object_pairs_hook=unique)
        json.dumps(value, allow_nan=False)
        return value
    except (RecursionError, OverflowError) as exc:
        raise ValueError('El JSON es demasiado complejo.') from exc


def load_bundle(filename):
    path = Path(filename).absolute()
    if str(path).startswith(('\\\\', '//')) or path.suffix.lower() != '.json':
        raise ValueError('Selecciona un JSON local.')
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('No se importan enlaces ni reparse points.')
    with path.open('rb') as source:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('La importación supera 8 MiB.')
    return strict_json(raw.decode('utf-8-sig'))


def date(value, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Fecha de memoria inválida.')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('Fecha de memoria inválida.') from None
    if parsed.utcoffset() is None:
        raise ValueError('Las fechas deben incluir zona horaria.')
    return parsed.astimezone(timezone.utc).isoformat()


def identity(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('ID de memoria inválido.')
    return value


def safe(value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if ASSIGNMENT.search(raw) or SECRET.search(raw) or 'PRIVATE KEY' in raw:
        raise ValueError('El paquete contiene posibles credenciales.')


class MemoryPortability:
    def __init__(self, engine):
        self.engine, self.base = engine, engine.base
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT value FROM core_meta WHERE key='memory_import_version'").fetchone()
            if row:
                if row[0] != '1':
                    raise ValueError('Versión de importación incompatible.')
                return
            db.execute('''CREATE TABLE core2_memory_reported (
                memory_id TEXT NOT NULL,claim_hash TEXT NOT NULL,claims TEXT NOT NULL,
                imported_at TEXT NOT NULL,reviewed_at TEXT,PRIMARY KEY(memory_id,claim_hash))''')
            db.execute('''CREATE TRIGGER core2_memory_reported_delete AFTER DELETE ON core_memories BEGIN
                DELETE FROM core2_memory_reported WHERE memory_id=OLD.id; END''')
            db.execute("INSERT INTO core_meta VALUES('memory_import_version','1')")

    def _memory(self, row, project):
        from .memory import KINDS, STATES
        required = {'id', 'project', 'content', 'status', 'sensitive', 'created_at', 'updated_at', 'expires_at'}
        allowed = required | {'fingerprint', 'kind', 'priority', 'source', 'retired', 'state', 'confidence',
                              'tags', 'fact_key', 'details', 'last_access_at', 'access_count'}
        if not isinstance(row, dict) or required - row.keys() or row.keys() - allowed:
            raise ValueError('Esquema de recuerdo inválido.')
        identity(row['id'])
        if row['project'] != project or type(row['sensitive']) not in (bool, int) or row['sensitive'] != 0:
            raise ValueError('Solo se admiten recuerdos públicos del proyecto declarado.')
        content = self.base._content(row['content'])
        if row['status'] not in ('confirmed', 'inferred'):
            raise ValueError('Estado original inválido.')
        if row.get('fingerprint') not in (None, self.base._fingerprint(project, content)):
            raise ValueError('Huella original inválida.')
        for key in ('created_at', 'updated_at'):
            date(row[key])
        date(row['expires_at'], optional=True)
        date(row.get('last_access_at'), optional=True)
        kind = row.get('kind') or 'project'
        state = row.get('state')
        if not isinstance(kind, str) or kind not in KINDS or state is not None and (not isinstance(state, str) or state not in STATES):
            raise ValueError('Tipo o validación original inválido.')
        priority = row.get('priority') if row.get('priority') is not None else 0
        confidence = row.get('confidence') if row.get('confidence') is not None else 0
        if type(priority) is not int or not 0 <= priority <= 10 or type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise ValueError('Prioridad o confianza original inválida.')
        if row.get('retired') is not None and (type(row['retired']) is not int or row['retired'] not in (0, 1)):
            raise ValueError('Retiro original inválido.')
        if row.get('source') is not None and (not isinstance(row['source'], str) or len(row['source']) > 128):
            raise ValueError('Fuente original inválida.')
        if row.get('access_count') is not None and (type(row['access_count']) is not int or row['access_count'] < 0):
            raise ValueError('Contador original inválido.')
        tags = strict_json(row['tags']) if isinstance(row.get('tags'), str) else [] if row.get('tags') is None else row['tags']
        details = strict_json(row['details']) if isinstance(row.get('details'), str) else {} if row.get('details') is None else row['details']
        if (not isinstance(tags, list) or len(tags) > 20 or
                any(not isinstance(tag, str) or not 1 <= len(tag) <= 64 for tag in tags) or not isinstance(details, dict)):
            raise ValueError('Metadatos originales inválidos.')
        if len(json.dumps({'tags': tags, 'details': details}, ensure_ascii=False)) > 16000:
            raise ValueError('Metadatos originales demasiado extensos.')
        fact_key = row.get('fact_key')
        if fact_key is not None and (not isinstance(fact_key, str) or not re.fullmatch(r'[\w.:-]{1,128}', fact_key)):
            raise ValueError('Clave de hecho inválida.')
        return {'content': content, 'kind': kind, 'tags': tags, 'details': details, 'fact_key': fact_key}

    def _claim(self, claim):
        if not isinstance(claim, dict) or set(claim) != {'memory', 'versions', 'links', 'procedure_runs'}:
            raise ValueError('Procedencia reportada inválida.')
        project = self.base._project(claim['memory'].get('project')) if isinstance(claim['memory'], dict) else None
        self._memory(claim['memory'], project)
        origin = claim['memory']['id']
        if not isinstance(claim['versions'], list) or len(claim['versions']) > 1000:
            raise ValueError('Demasiadas versiones reportadas.')
        for version in claim['versions']:
            if (not isinstance(version, dict) or set(version) != {'revision', 'memory_id', 'project', 'content', 'status', 'sensitive', 'recorded_at', 'expires_at'}
                    or version['memory_id'] != origin or version['project'] != project or version['sensitive'] != 0
                    or type(version['revision']) is not int or version['revision'] < 1 or version['status'] not in ('confirmed', 'inferred')):
                raise ValueError('Versión reportada inválida.')
            self.base._content(version['content'])
            date(version['recorded_at']); date(version['expires_at'], optional=True)
        if not isinstance(claim['links'], list) or len(claim['links']) > 5000:
            raise ValueError('Demasiadas relaciones reportadas.')
        for link in claim['links']:
            if not isinstance(link, dict) or set(link) != {'source_id', 'target_id', 'relation'}:
                raise ValueError('Relación reportada inválida.')
            identity(link['source_id']); identity(link['target_id'])
            if origin not in (link['source_id'], link['target_id']) or link['relation'] not in ('related', 'supports', 'contradicts', 'uses', 'belongs_to', 'runs_on', 'supersedes'):
                raise ValueError('Relación reportada inválida.')
        if not isinstance(claim['procedure_runs'], list) or len(claim['procedure_runs']) > 1000:
            raise ValueError('Demasiadas ejecuciones reportadas.')
        for run in claim['procedure_runs']:
            if not isinstance(run, dict) or set(run) != {'memory_id', 'plan_id', 'executed_at', 'evidence'} or run['memory_id'] != origin:
                raise ValueError('Ejecución reportada inválida.')
            identity(run['plan_id']); date(run['executed_at'])
            if not isinstance(run['evidence'], str) or len(run['evidence']) > 16000:
                raise ValueError('Evidencia reportada inválida.')
        safe(claim)

    def _validate(self, bundle, target):
        target = self.base._project(target)
        if ASSIGNMENT.search(target) or 'PRIVATE KEY' in target.upper():
            raise ValueError('Proyecto de destino con posibles credenciales.')
        if (not isinstance(bundle, dict) or set(bundle) - {'contract', 'project', 'memories', 'versions', 'links', 'procedure_runs', 'reported'}
                or {'contract', 'project', 'memories', 'versions', 'links', 'procedure_runs'} - bundle.keys()
                or bundle['contract'] != 'memory-engine-1'):
            raise ValueError('Contrato de exportación de memoria incompatible.')
        raw = json.dumps(bundle, ensure_ascii=False, allow_nan=False)
        if len(raw.encode('utf-8')) > MAX_BYTES:
            raise ValueError('El paquete supera 8 MiB.')
        project = self.base._project(bundle['project'])
        if not isinstance(bundle['memories'], list) or len(bundle['memories']) > 1000:
            raise ValueError('Límite de 1000 recuerdos por paquete.')
        rows, claims, contents = {}, {}, set()
        for row in bundle['memories']:
            parsed = self._memory(row, project)
            if row['id'] in rows:
                raise ValueError('ID original duplicado.')
            content_hash = self.base._fingerprint(project, parsed['content'])
            if content_hash in contents:
                raise ValueError('El paquete contiene recuerdos equivalentes con metadatos ambiguos.')
            contents.add(content_hash)
            rows[row['id']] = (row, parsed)
            claims[row['id']] = [{'memory': row, 'versions': [], 'links': [], 'procedure_runs': []}]
        for field, id_key, cap in (('versions', 'memory_id', 10000), ('links', 'source_id', 5000), ('procedure_runs', 'memory_id', 1000)):
            if not isinstance(bundle[field], list) or len(bundle[field]) > cap:
                raise ValueError('Colección de procedencia inválida o demasiado grande.')
            for item in bundle[field]:
                if not isinstance(item, dict) or not isinstance(item.get(id_key), str) or item[id_key] not in rows:
                    raise ValueError('Referencia de procedencia ajena al paquete.')
                if field == 'links' and (not isinstance(item.get('target_id'), str) or item['target_id'] not in rows):
                    raise ValueError('Las relaciones deben permanecer dentro del paquete.')
                claims[item[id_key]][0][field].append(item)
        reported = bundle.get('reported', [])
        if not isinstance(reported, list) or len(reported) > 5000:
            raise ValueError('Demasiada procedencia acumulada.')
        for item in reported:
            if (not isinstance(item, dict) or set(item) != {'memory_id', 'claims'}
                    or not isinstance(item['memory_id'], str) or item['memory_id'] not in rows):
                raise ValueError('Procedencia acumulada inválida.')
            claims[item['memory_id']].append(item['claims'])
        for entries in claims.values():
            for claim in entries:
                self._claim(claim)
        return target, rows, claims, fingerprint({'target': target, 'bundle': bundle})

    def preview(self, bundle, project):
        target, rows, claims, digest = self._validate(bundle, project)
        return {'project': target, 'memories': len(rows), 'reported_claims': sum(map(len, claims.values())),
                'expected_hash': digest, 'state': 'PENDIENTE', 'applied': False,
                'relations_and_procedures': 'reported_only'}

    def apply(self, bundle, project, expected_hash):
        target, rows, claims, digest = self._validate(bundle, project)
        if not isinstance(expected_hash, str) or expected_hash != digest:
            raise ValueError('La revisión no coincide con el paquete y proyecto actuales.')
        stamp, created, duplicates = datetime.now(timezone.utc).isoformat(), [], 0
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for origin, (row, parsed) in rows.items():
                value_hash = self.base._fingerprint(target, parsed['content'])
                existing = db.execute('SELECT id,sensitive FROM core_memories WHERE fingerprint=?', (value_hash,)).fetchone()
                if existing:
                    # Do not mutate, attach claims to, resurrect or reveal local duplicates.
                    duplicates += 1
                    continue
                memory_id = uuid.uuid4().hex
                expires = date(row['expires_at'], optional=True)
                retired = int(bool(row.get('retired')) or bool(expires and expires <= stamp) or row.get('state') == 'DESACTUALIZADO')
                db.execute('INSERT INTO core_memories VALUES(?,?,?,\'inferred\',0,?,?,?,?)',
                           (memory_id, target, parsed['content'], value_hash, date(row['created_at']), stamp, expires))
                db.execute('INSERT INTO core2_memory VALUES(?,?,0,?,\'imported\')', (memory_id, parsed['kind'], retired))
                db.execute('INSERT INTO core2_memory_details VALUES(?,?,0,?,?,?)',
                           (memory_id, 'DESACTUALIZADO' if retired else 'PENDIENTE', json.dumps(parsed['tags']),
                            parsed['fact_key'], json.dumps(parsed['details'], ensure_ascii=False)))
                for claim in claims[origin]:
                    db.execute('INSERT OR IGNORE INTO core2_memory_reported VALUES(?,?,?,?,NULL)',
                               (memory_id, fingerprint(claim), json.dumps(claim, ensure_ascii=False, allow_nan=False), stamp))
                created.append(memory_id)
        if self.engine.events:
            for memory_id in created:
                self.engine.events.emit('memory.created', entity_id=memory_id, code='imported_pending')
        return {'applied': True, 'created': created, 'duplicates_skipped': duplicates, 'state': 'PENDIENTE'}

    def inspect(self, memory_id, *, db=None):
        identity(memory_id)
        if db is None:
            with self.base.connect() as connection:
                return self.inspect(memory_id, db=connection)
        row = db.execute('''SELECT m.*,c.kind,c.retired,c.source,c.priority,d.state,d.confidence,d.fact_key,d.tags,d.details FROM core_memories m
            JOIN core2_memory c ON c.memory_id=m.id JOIN core2_memory_details d ON d.memory_id=m.id
            WHERE m.id=? AND m.sensitive=0 AND c.source='imported' ''', (memory_id,)).fetchone()
        if not row:
            raise ValueError('No hay recuerdo importado público disponible.')
        reported = [dict(item) for item in db.execute(
            'SELECT claim_hash,claims,reviewed_at FROM core2_memory_reported WHERE memory_id=? ORDER BY claim_hash', (memory_id,))]
        for item in reported:
            item['claims'] = strict_json(item['claims'])
        snapshot = {'memory': dict(row), 'reported': reported, 'trust': 'reported_data'}
        return {**snapshot, 'expected_hash': fingerprint(snapshot)}

    def review(self, memory_id, expected_hash):
        conflicts = []
        with self.base.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            snapshot = self.inspect(memory_id, db=db)
            row = snapshot['memory']
            stamp = datetime.now(timezone.utc).isoformat()
            if snapshot['expected_hash'] != expected_hash:
                raise ValueError('El recuerdo cambió; vuelve a revisar.')
            if row['retired'] or row['expires_at'] and row['expires_at'] <= stamp:
                raise ValueError('No se promueven recuerdos retirados o caducados.')
            self.base._content(row['content']); safe(row)
            db.execute("UPDATE core_memories SET status='confirmed',updated_at=? WHERE id=?", (stamp, memory_id))
            db.execute("UPDATE core2_memory_details SET state='VERIFICADO',confidence=1 WHERE memory_id=?", (memory_id,))
            db.execute('UPDATE core2_memory_reported SET reviewed_at=? WHERE memory_id=?', (stamp, memory_id))
            if row['fact_key']:
                conflicts = db.execute('''SELECT m.id FROM core_memories m JOIN core2_memory c ON c.memory_id=m.id
                    JOIN core2_memory_details d ON d.memory_id=m.id WHERE m.project=? AND m.id<>? AND m.sensitive=0
                    AND m.status='confirmed' AND d.state='VERIFICADO' AND c.retired=0 AND d.fact_key=?
                    AND (m.expires_at IS NULL OR m.expires_at>?)''', (row['project'], memory_id, row['fact_key'], stamp)).fetchall()
                for other in conflicts:
                    db.execute("INSERT OR IGNORE INTO core2_memory_links VALUES(?,?,'contradicts')", (memory_id, other['id']))
        if self.engine.events:
            self.engine.events.emit('memory.updated', entity_id=memory_id, code='import_reviewed')
            if conflicts:
                self.engine.events.emit('memory.conflict', entity_id=memory_id)
        return {'id': memory_id, 'state': 'VERIFICADO', 'basis': 'explicit_user_review',
                'procedures_activated': False, 'has_conflicts': bool(conflicts)}
