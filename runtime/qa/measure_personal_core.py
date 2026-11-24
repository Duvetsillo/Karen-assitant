"""One synthetic local Core 2 stream. No personal DB, text, microphone or audio."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from karen_core2.runtime import CoreRuntime
from karen_core2.models import LocalModels, resources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='gemma3:1b', help='Preference among verified installed local models; no download.')
    parser.add_argument('--output', type=Path, default=ROOT / 'tmp/personal-core-metrics.json')
    args = parser.parse_args()
    result = {'scope': 'Synthetic text, temporary database, local inference; no audio or microphone.',
              'before': resources()}
    with tempfile.TemporaryDirectory() as folder:
        models = LocalModels()
        try:
            with models.request('/api/ps') as response:
                occupied = bool(response.json().get('models'))
            if occupied:
                result['blocked'] = 'An Ollama model was already loaded; existing workload left untouched.'
            else:
                runtime = CoreRuntime(archive_path=Path(folder) / 'core.sqlite3',
                                      task_path=Path(folder) / 'tasks.sqlite3', models=models)
                parts = []
                answer = runtime.chat('Responde con una sola palabra: LISTA.', preferred=args.model,
                                      on_token=parts.append, stop=threading.Event())
                result.update(nonempty_answer=bool(answer.strip()), stream_chunks=len(parts), metrics=models.metrics)
                result['after'] = resources()
        finally:
            models.http.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    return 2 if result.get('blocked') else 0


if __name__ == '__main__':
    raise SystemExit(main())
