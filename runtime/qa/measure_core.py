"""Synthetic local Core timing. Never reads user data or opens audio hardware."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from core_events import read_events
from core_resources import microphone_guard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=100)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 10 <= args.runs <= 10000:
        parser.error('Usa entre 10 y 10000 repeticiones.')
    measurements = {name: [] for name in ('commit_ms', 'events_read_ms', 'os_lock_ms')}
    with tempfile.TemporaryDirectory() as directory:
        archive = Conversations(Path(directory) / 'core.sqlite3')
        chat = archive.create()
        for index in range(args.runs):
            start = time.perf_counter()
            archive.append(chat, f'Synthetic turn {index}', 'Synthetic reply', True)
            measurements['commit_ms'].append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            with closing(sqlite3.connect(archive.path)) as db: read_events(db)
            measurements['events_read_ms'].append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            with microphone_guard(Path(directory) / 'test.lock'): pass
            measurements['os_lock_ms'].append((time.perf_counter() - start) * 1000)
    result = {'platform': platform.platform(), 'python': sys.version.split()[0], 'runs': args.runs,
              'scope': 'Temporary SQLite and direct OS lock only. No STT, LLM, TTS, GPU, or UI measurements.',
              'measurements': {name: {'median': statistics.median(values),
                                       'p95': sorted(values)[int(len(values) * .95) - 1],
                                       'max': max(values)} for name, values in measurements.items()}}
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
