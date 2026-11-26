"""Local acceptance without private prompts, screenshots, microphone or remote APIs."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from karen_core2.runtime import CoreRuntime
from karen_core2.models import resources
from karen_core2.obsidian import ObsidianManager


def main():
    report = {'before': resources()}
    with tempfile.TemporaryDirectory(prefix='karen-master-live-') as folder:
        root = Path(folder)
        vault = root / 'vault'
        (vault / 'Projects').mkdir(parents=True)
        manager = ObsidianManager(vault, ['Projects'], root / 'index.sqlite3')
        runtime = CoreRuntime(archive_path=root / 'core.sqlite3', task_path=root / 'tasks.sqlite3', obsidian=manager)
        try:
            catalog = runtime.models.discover(force=True)
            assert any(row['name'] == 'gemma3:1b' for row in catalog), 'Requiere gemma3:1b ya instalado; no descarga modelos.'
            report['local_models'] = [row['name'] for row in catalog]
            Conversations(runtime.memory.path).set_mode('gaming')
            started = time.monotonic()
            tokens = []
            answer = runtime.chat('Responde solamente: prueba local correcta.', preferred='gemma3:1b', on_token=tokens.append)
            assert answer.strip() and tokens
            report['conversation_seconds'] = round(time.monotonic() - started, 3)
            report['first_token_seconds'] = runtime.models.metrics[-1]['first_token_seconds']
            assert runtime.models.metrics[-1]['gpu_layers'] == 0
            report['gaming_gpu_layers'] = 0
            stop = threading.Event()
            delivered = []
            def interrupt(fragment):
                delivered.append(fragment)
                stop.set()
            started = time.monotonic()
            try:
                runtime.chat('Cuenta del uno al cien, una palabra por línea.', preferred='gemma3:1b',
                             on_token=interrupt, stop=stop)
                raise AssertionError('No se respetó la cancelación real del stream.')
            except InterruptedError:
                assert delivered
            report['stream_cancel_after_first_fragment'] = True
            report['cancelled_request_seconds'] = round(time.monotonic() - started, 3)
            runtime.approve = lambda request: True  # Synthetic temporary vault only.
            result = runtime.command('/obsidian create ' + json.dumps({'path': 'Projects/Probe.md', 'content': 'Telescopio sintético.'}))
            assert 'completed' in result
            assert 'Telescopio' in runtime.command('busca en obsidian telescopio')
            report['temporary_obsidian_plan'] = True
            rows = runtime.events.status()['recent']
            assert any(row['topic'] == 'conversation.interrupted' for row in rows)
            report['event_journal'] = (root / 'logs/core-events.jsonl').exists()
            deadline = time.monotonic() + 10
            while True:
                with runtime.models.request('/api/ps') as response:
                    loaded = response.json().get('models', [])
                if not loaded or time.monotonic() >= deadline:
                    break
                time.sleep(.1)
            report['models_loaded_after'] = [row['name'] for row in loaded]
            assert not loaded, 'Ollama todavía conserva un modelo cargado.'
        finally:
            runtime.close()
    report['after'] = resources()
    output = Path(__file__).resolve().parents[1] / 'docs/MASTER_METRICS_2026-11-26.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
