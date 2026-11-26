"""Real Python-created SQLite read by the built Pet adapters; no gateway or live data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karen_core2.runtime import CoreRuntime


def main():
    root = Path(__file__).resolve().parents[1]
    pet = root.parent / 'pet' if (root.parent / 'pet/package.json').is_file() else root / 'desktop-pet'
    adapter = pet / 'dist-electron/electron/core-store.js'
    if not adapter.is_file():
        raise ValueError('Compila primero desktop-pet con npm run build.')
    with tempfile.TemporaryDirectory(prefix='karen-metadata-interop-') as directory:
        folder = Path(directory)
        runtime = CoreRuntime(archive_path=folder / 'core.sqlite3', task_path=folder / 'tasks.sqlite3')
        try:
            recipe = {'goal': 'PRIVATE_INTEROP_RECIPE', 'steps': [
                {'id': 'ram', 'label': 'Read RAM', 'tool': 'memory_sample', 'args': {}, 'depends': []}]}
            schedule = runtime.automations.create(name='Interop routine', recipe=recipe, due_at='2100-01-01T00:00:00+00:00')
            handoff = runtime.handoffs.create(project='Karen', description='PRIVATE_INTEROP_DESCRIPTION',
                                               context='PRIVATE_INTEROP_CONTEXT', acceptance=['PRIVATE_INTEROP_ACCEPTANCE'])
            event_job = runtime.automations.create(name='Event metadata', recipe=recipe, event={'topic': 'memory.conflict'})
            before = runtime.plans.path.read_bytes()
            code = ('const {CoreStore} = await import(' + json.dumps(adapter.as_uri()) + ');\n'
                    'const core=new CoreStore(process.argv[1],process.argv[2]);\n'
                    'try {console.log(JSON.stringify({schedules:core.listSchedules(),handoffs:core.listHandoffs()}));}\n'
                    'finally {core.close();}')
            result = subprocess.run(['node', '--input-type=module', '-e', code, str(runtime.memory.path), str(runtime.plans.path)],
                                    capture_output=True, text=True, timeout=10, check=True)
            data = json.loads(result.stdout)
            assert {row['id'] for row in data['schedules']} == {schedule['id'], event_job['id']}
            assert next(row for row in data['schedules'] if row['id'] == event_job['id'])['event_topic'] == 'memory.conflict'
            assert data['handoffs'][0]['id'] == handoff['task']['id']
            assert 'PRIVATE_' not in result.stdout and 'payload' not in result.stdout and 'hash' not in result.stdout
            assert runtime.plans.path.read_bytes() == before
            assert runtime.automations.history() == []
            assert runtime.plans.list() == []
            print(json.dumps({'python_sqlite_to_pet': True, 'schedule_metadata': True, 'handoff_metadata': True,
                              'private_payloads_returned': False, 'tasks_database_unchanged': True,
                              'plans_executed': 0, 'event_metadata': True, 'gateway_required': False}))
        finally:
            runtime.close()


if __name__ == '__main__':
    main()
