"""Real GPU stream cancellation after gaming starts, with temporary mode storage."""
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from karen_core2.runtime import CoreRuntime
from karen_core2.models import resources


def main():
    report = {'before': resources()}
    with tempfile.TemporaryDirectory(prefix='karen-gaming-live-') as folder:
        root = Path(folder)
        runtime = CoreRuntime(archive_path=root / 'core.sqlite3', task_path=root / 'tasks.sqlite3')
        modes = Conversations(runtime.memory.path)
        modes.set_mode('normal')
        try:
            catalog = runtime.models.discover(force=True)
            assert any(row['name'] == 'qwen3.5:2b' for row in catalog), 'Requiere qwen3.5:2b ya instalado.'
            selected = next(row for row in catalog if row['name'] == 'qwen3.5:2b')
            allocation = runtime.models.allocation(selected, 'reasoning', runtime.models.probe())
            assert allocation and allocation['gpu_layers'] > 0, 'No hay presupuesto medido para probar GPU.'
            received = []
            def start_gaming(fragment):
                assert runtime.models.active_device == 'gpu'
                with runtime.models.request('/api/ps') as response:
                    running = response.json().get('models', [])
                report['provider_vram_bytes_during'] = next(row['size_vram'] for row in running if row['name'] == 'qwen3.5:2b')
                assert report['provider_vram_bytes_during'] > 0
                received.append(time.monotonic())
                modes.set_mode('gaming')
            started = time.monotonic()
            try:
                runtime.chat('Analiza y cuenta del uno al cien, una palabra por línea.', preferred='qwen3.5:2b',
                             on_token=start_gaming)
                raise AssertionError('La generación no fue cancelada al entrar en gaming.')
            except InterruptedError:
                assert len(received) == 1
            report['gpu_to_gaming_cancel_seconds'] = round(time.monotonic() - received[0], 3)
            report['total_request_seconds'] = round(time.monotonic() - started, 3)
            report['cancel_metric'] = runtime.models.metrics[-1]
            assert report['cancel_metric']['gpu_layers'] > 0
            assert report['cancel_metric']['canceled']
            assert not runtime.models.queue.status()['active']
            deadline = time.monotonic() + 15
            while True:
                with runtime.models.request('/api/ps') as response:
                    loaded = response.json().get('models', [])
                if not loaded or time.monotonic() >= deadline:
                    break
                time.sleep(.1)
            assert not loaded, 'El proveedor conserva pesos cargados.'
            report['models_loaded_after'] = []
            report['queue_released'] = True
        finally:
            runtime.close()
    report['after'] = resources()
    output = Path(__file__).resolve().parents[1] / 'docs/GAMING_METRICS_2026-11-26.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
