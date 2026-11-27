"""Metadata only. Reuse Core ranking; never load, chat, pull or delete weights."""
import json
from pathlib import Path
import sys
import time

root = Path(__file__).resolve()
for candidate in (root.parents[2] / 'runtime', root.parents[2] / 'model-core'):
    if (candidate / 'karen_core2' / 'models.py').is_file():
        sys.path.insert(0, str(candidate))
        break

from karen_core2.models import LocalModels, KINDS, task_kind
from karen_core2.resource_policy import ResourcePolicy
import requests


class MetadataTransport(requests.Session):
    def __init__(self):
        super().__init__()
        self.trust_env = False

    def request(self, method, url, **kwargs):
        kwargs['timeout'] = (2, 4)
        kwargs['allow_redirects'] = False
        return super().request(method, url, **kwargs)


def inspect(data):
    budget = data['budget']
    manager = LocalModels(data['endpoint'], transport=MetadataTransport(),
                          probe=lambda: budget,
                          policy=ResourcePolicy(data['profile']))
    # Only our main process supplies this ephemeral metadata cache, never a renderer.
    if data.get('catalog') is not None:
        manager.catalog = data['catalog']
        manager.catalog_at = time.monotonic()
    catalog = manager.discover()
    kind = 'vision' if data.get('images') else task_kind(data.get('message', ''))
    rankings = {key: [model['name'] for model in manager.rank(key, budget=budget)] for key in sorted(KINDS)}
    return {'catalog': catalog, 'kind': kind, 'rankings': rankings, 'budget': budget}


if __name__ == '__main__':
    try:
        data = json.loads(sys.stdin.buffer.read(131072))
        result = inspect(data)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    except Exception:
        # Never print endpoint configuration, prompts, tokens or tracebacks.
        print(json.dumps({'error': 'No se pudo consultar Ollama y sus recursos locales.'}))
        raise SystemExit(1)
