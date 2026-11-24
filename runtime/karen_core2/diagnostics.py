"""Bounded measured trends, not unsupported predictions."""
from datetime import datetime, timezone
import json
import math
import statistics
import time

from karen_task_tools import cpu_sample, memory_sample, disk_sample
from .models import resources
from .privacy import public


class Diagnostics:
    def __init__(self, engine):
        self.engine = engine
        with engine._connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS core2_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT, observed REAL NOT NULL, metrics TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS core2_service_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT, observed REAL NOT NULL, service TEXT NOT NULL, event_id INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS core2_process_samples (
                observed REAL NOT NULL,pid INTEGER NOT NULL,name TEXT NOT NULL,working_set INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS core2_service_seen (record_id TEXT PRIMARY KEY);''')

    def sample(self, stop):
        result = {'observed_at': datetime.now(timezone.utc).isoformat()}
        for reader in (cpu_sample, memory_sample, disk_sample):
            if stop.is_set():
                raise InterruptedError()
            result.update(reader({}, stop))
        result.update({key: value for key, value in resources().items() if value is not None})
        # These fixed read-only scripts are trusted code, never model-generated shell.
        from .skills import cancellable_process
        flags = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command']
        process_script = 'Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Id,ProcessName,WorkingSet64 | ConvertTo-Json -Compress'
        try:
            processes = json.loads(cancellable_process(flags + [process_script], stop, 6) or '[]')
            if isinstance(processes, dict): processes = [processes]
            with self.engine._connect() as db:
                for process in processes[:10]:
                    db.execute('INSERT INTO core2_process_samples VALUES (?,?,?,?)',
                               (time.time(), int(process['Id']), str(process['ProcessName'])[:100], int(process['WorkingSet64'])))
                db.execute('DELETE FROM core2_process_samples WHERE rowid NOT IN (SELECT rowid FROM core2_process_samples ORDER BY rowid DESC LIMIT 7200)')
        except (OSError, ValueError, KeyError, RuntimeError):
            result['process_probe'] = 'unavailable'
        event_script = "$ErrorActionPreference='Stop'; Get-WinEvent -FilterHashtable @{LogName='System';Id=7031,7034;StartTime=(Get-Date).AddDays(-1)} -MaxEvents 20 -ErrorAction SilentlyContinue | ForEach-Object { [pscustomobject]@{record_id=$_.RecordId; event_id=$_.Id;service=[string]$_.Properties[0].Value} } | ConvertTo-Json -Compress"
        try:
            events = json.loads(cancellable_process(flags + [event_script], stop, 6) or '[]')
            self.record_service_failures([events] if isinstance(events, dict) else events)
        except (OSError, ValueError, KeyError, RuntimeError):
            result['service_probe'] = 'unavailable'
        self.record(result)
        return result

    def record(self, sample, observed=None):
        allowed = {'cpu_percent', 'ram_total_bytes', 'ram_available_bytes', 'disk_total_bytes', 'disk_free_bytes',
                   'vram_total_bytes', 'vram_available_bytes'}
        metrics = {key: value for key, value in sample.items() if key in allowed and type(value) in (int, float) and math.isfinite(value)}
        if not metrics:
            raise ValueError('La muestra no contiene mediciones finitas.')
        with self.engine._connect() as db:
            db.execute('INSERT INTO core2_samples (observed,metrics) VALUES (?,?)', (time.time() if observed is None else observed, json.dumps(metrics, allow_nan=False)))
            db.execute('DELETE FROM core2_samples WHERE id NOT IN (SELECT id FROM core2_samples ORDER BY id DESC LIMIT 720)')

    def record_service_failures(self, rows):
        with self.engine._connect() as db:
            for row in rows[:100]:
                if row.get('event_id') not in {7031, 7034} or not isinstance(row.get('service'), str):
                    continue
                record_id = str(row.get('record_id', ''))
                if not record_id or db.execute('SELECT 1 FROM core2_service_seen WHERE record_id=?', (record_id,)).fetchone():
                    continue
                db.execute('INSERT INTO core2_service_seen VALUES (?)', (record_id,))
                db.execute('INSERT INTO core2_service_failures (observed,service,event_id) VALUES (?,?,?)',
                           (time.time(), row['service'][:120], row['event_id']))
            db.execute('DELETE FROM core2_service_failures WHERE id NOT IN (SELECT id FROM core2_service_failures ORDER BY id DESC LIMIT 500)')
            db.execute('DELETE FROM core2_service_seen WHERE rowid NOT IN (SELECT rowid FROM core2_service_seen ORDER BY rowid DESC LIMIT 5000)')

    def report(self):
        with self.engine._connect() as db:
            samples = [dict(row) for row in db.execute('SELECT observed,metrics FROM core2_samples ORDER BY id DESC LIMIT 60')]
            failures = [dict(row) for row in db.execute('''SELECT service,COUNT(*) AS failures FROM core2_service_failures
                WHERE observed>? GROUP BY service HAVING COUNT(*)>=3''', (time.time() - 86400,))]
            growing = [dict(row) for row in db.execute('''SELECT pid,name,COUNT(*) AS samples,
                MAX(working_set)-MIN(working_set) AS range_bytes FROM core2_process_samples
                WHERE observed>? GROUP BY pid,name HAVING COUNT(*)>=5 AND
                MAX(working_set)-MIN(working_set)>536870912 AND MAX(observed)-MIN(observed)>=60''', (time.time() - 3600,))]
        samples.reverse()
        metrics = [json.loads(item['metrics']) for item in samples]
        notices = []
        cpu = [item['cpu_percent'] for item in metrics if 'cpu_percent' in item]
        ram = [item['ram_available_bytes'] for item in metrics if 'ram_available_bytes' in item]
        if len(cpu) >= 5 and statistics.mean(cpu[-5:]) > 85:
            notices.append('CPU superior al 85% de media en las últimas cinco muestras; consulta procesos antes de actuar.')
        if len(ram) >= 5 and ram[-1] < 2 * 1024**3 and ram[-1] < ram[0]:
            notices.append('RAM disponible baja y descendente en las muestras; esto no demuestra una fuga de memoria.')
        if metrics and metrics[-1].get('disk_total_bytes', 0) > 0:
            ratio = metrics[-1].get('disk_free_bytes', 0) / metrics[-1]['disk_total_bytes']
            if ratio < .1:
                notices.append('Menos del 10% de espacio libre medido; revisa archivos antes de borrar.')
        for item in failures:
            notices.append(f"Servicio {item['service']}: {item['failures']} eventos de fallo observados en 24 horas; la causa no está confirmada.")
        for item in growing:
            notices.append(f"Proceso {item['name']} (PID {item['pid']}): variación de RAM superior a 512 MiB en {item['samples']} muestras; no demuestra un fallo.")
        stale = bool(samples and time.time() - samples[-1]['observed'] > 300)
        return {'samples': len(samples), 'stale': stale, 'latest': metrics[-1] if metrics else None,
                'cpu_mean': round(statistics.mean(cpu), 2) if cpu else None,
                'process_variations': growing,
                'recommendations': notices, 'basis': 'Mediciones locales; no predicción causal ni garantía de fallo futuro.'}
