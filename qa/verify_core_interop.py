"""Check Python and Electron's Node runtime against one temporary Core database."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conversations import Conversations
from karen_memory import MemoryStore
from karen_alerts import AlertEngine
from core_events import read_events, read_activity
from core_local_api import read_contract
from karen_tasks import TaskEngine, ToolSpec
from contextlib import closing
import sqlite3


PET = ROOT / 'desktop-pet'
TSX = PET / 'node_modules' / '.bin' / ('tsx.cmd' if os.name == 'nt' else 'tsx')


def main():
    if not TSX.is_file():
        raise SystemExit('Falta tsx; ejecuta npm ci en desktop-pet.')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'shared.sqlite3'
        archive = Conversations(path)
        tasks_path = Path(directory) / 'tasks.sqlite3'
        engine = TaskEngine({'check': ToolSpec('read', lambda args, stop: True)}, tasks_path)
        task_steps = [{'tool': 'check', 'args': {'synthetic_private': 'NOT-FOR-NODE'}}]
        task_id = engine.create(task_steps)
        classic = archive.create()
        archive.append(classic, 'Turno clásico', 'Respuesta clásica', True)
        archive.set_voice_style('warm')
        memories = MemoryStore(path)
        memories.add('Karen', 'Prefiere respuestas breves')
        memories.add('Karen', 'Dato privado de prueba', sensitive=True, allow_sensitive=True)
        env = {**os.environ, 'KAREN_CORE_DB': str(path), 'KAREN_CLASSIC_CHAT': classic,
               'KAREN_TASKS_DB': str(tasks_path), 'KAREN_INTEROP_TASK': task_id}
        code = ("import { CoreStore } from './electron/core-store.ts'; "
                "const store = new CoreStore(process.env.KAREN_CORE_DB, process.env.KAREN_TASKS_DB); "
                "const task = store.readTask(process.env.KAREN_INTEROP_TASK); "
                "if (task.status !== 'pending' || JSON.stringify(task).includes('NOT-FOR-NODE')) throw new Error('Task bridge inválido'); "
                "if (store.getVoiceStyle() !== 'warm') throw new Error('Estilo Python no visible en Pet'); "
                "store.setVoiceStyle('bright'); "
                "store.setMode('gaming'); "
                "const classic = store.readChat(process.env.KAREN_CLASSIC_CHAT); "
                "if (classic.length !== 1 || classic[0].answer !== 'Respuesta clásica') "
                "throw new Error('Historial clásico no disponible en Pet'); "
                "store.appendOpenClawTurn('agent:main:main','interop-1','Turno Pet','Respuesta Pet'); "
                "store.setActivity('a'.repeat(32), 'THINKING'); "
                "const memories = store.listMemories('Karen'); "
                "if (memories.length !== 1 || memories[0].content !== 'Prefiere respuestas breves') "
                "throw new Error('Memoria compartida incorrecta'); "
                "store.close();")
        subprocess.run([str(TSX), '-e', code], cwd=PET, env=env,
                       check=True, capture_output=True, text=True, timeout=30)
        rows = archive.list()
        pet = next((row[0] for row in rows if row[0].startswith('openclaw-')), None)
        if not pet or archive.exchanges(pet) != [('Turno Pet', 'Respuesta Pet', 1)]:
            raise AssertionError('El turno Pet no quedó disponible para Karen clásica.')
        if read_contract(path, f'/v1/chats/{pet}/exchanges')['exchanges'][0]['answer'] != 'Respuesta Pet':
            raise AssertionError('API Core no acepta el chat Pet.')
        with closing(sqlite3.connect(path)) as db:
            events = read_events(db)['events']
            if not any(e['topic'] == 'conversation' and e['entity_id'] == pet for e in events):
                raise AssertionError('El turno Pet no produjo un evento Core.')
            if read_activity(db)['clients'][0]['state'] != 'THINKING':
                raise AssertionError('La actividad Pet no es visible en Python.')
        if archive.context(classic)[1]['content'] != 'Respuesta clásica':
            raise AssertionError('El turno clásico cambió durante la interoperabilidad.')
        if archive.get_voice_style() != 'bright':
            raise AssertionError('El estilo Pet no quedó disponible para Karen clásica.')
        with patch.dict(os.environ, {'KAREN_CORE_DB': str(path)}):
            alerts = AlertEngine(Path(directory) / 'alerts.sqlite3')
            alerts.add_rule('pc', 'disk_free_percent', '<', 10, priority='high')
            alerts.add_rule('pc', 'disk_free_percent', '<', 5, priority='critical')
            if alerts.observe('pc', 'disk_free_percent', 8):
                raise AssertionError('Gaming de Pet no aplazó la alerta normal.')
            if [a['priority'] for a in alerts.observe('pc', 'disk_free_percent', 4)] != ['critical']:
                raise AssertionError('Gaming de Pet ocultó una alerta crítica.')
        archive.set_mode('normal')
        if engine.run(task_id, task_steps)['status'] != 'completed':
            raise AssertionError('No terminó la tarea sintética de interoperabilidad.')
        subprocess.run([str(TSX), '-e',
                        "import { CoreStore } from './electron/core-store.ts'; "
                        "const store = new CoreStore(process.env.KAREN_CORE_DB, process.env.KAREN_TASKS_DB); "
                        "if (store.readTask(process.env.KAREN_INTEROP_TASK).status !== 'completed') throw new Error('Progreso de tarea no compartido'); "
                        "if (store.getMode() !== 'normal') throw new Error('Modo clásico no visible en Pet'); "
                        "store.close();"], cwd=PET, env=env,
                       check=True, capture_output=True, text=True, timeout=30)
        print('KAREN_CORE_INTEROP_OK: chats, memoria, voz, modo, eventos, actividad, API Pet y progreso de tarea compartido')


if __name__ == '__main__':
    main()
