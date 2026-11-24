"""Measure a real classic Tk loop during a real SQLite exclusive lock.

All data is synthetic and temporary. Providers, benchmark discovery, wake and
TTS are disabled. No screenshot, audio capture, or user database is used.
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import KarenConfig
from conversations import Conversations
from karen_app import KarenApp
from qa.ui_helpers import close_app, pump_until, wait_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'core.sqlite3'
        archive = Conversations(path)
        chat_id = archive.create()
        archive.append(chat_id, 'Synthetic prompt', 'Synthetic reply', True)
        with (patch('karen_app.open_archive', return_value=(archive, chat_id, None)),
              patch.object(KarenApp, 'load_catalog'),
              patch.object(KarenApp, 'connect_benchmark')):
            app = KarenApp(KarenConfig(tts_enabled=False, wake_auto_start=False))
        app.root.withdraw()
        ticks = []
        timer = None
        main_thread = threading.get_ident()
        archive_threads = set()
        original = Conversations.connect
        def traced(view):
            archive_threads.add(threading.get_ident())
            return original(view)
        def tick():
            nonlocal timer
            ticks.append(time.perf_counter())
            timer = app.root.after(5, tick)
        try:
            wait_archive(app)
            with patch.object(Conversations, 'connect', traced):
                with closing(sqlite3.connect(path)) as locked:
                    locked.execute('BEGIN EXCLUSIVE')
                    tick()
                    start = time.perf_counter()
                    app.restore_conversation()
                    submit_ms = (time.perf_counter() - start) * 1000
                    pump_until(app, lambda: app.core_chat_sync_failed)
                    locked_wait_ms = (time.perf_counter() - start) * 1000
                    locked.rollback()
                start = time.perf_counter()
                app.refresh_conversations()
                wait_archive(app)
                recovery_ms = (time.perf_counter() - start) * 1000
            gaps = [(b - a) * 1000 for a, b in zip(ticks, ticks[1:])]
            result = {
                'platform': platform.platform(), 'python': sys.version.split()[0],
                'scope': 'One real Tk window, temporary SQLite, exclusive lock. Synthetic history. No model/audio/network measurements.',
                'archive_refresh_submit_ms': submit_ms,
                'busy_result_ms': locked_wait_ms,
                'recovery_after_unlock_ms': recovery_ms,
                'timer_target_ms': 5, 'timer_ticks': len(ticks),
                'timer_gap_median_ms': statistics.median(gaps),
                'timer_gap_max_ms': max(gaps),
                'archive_sql_calls_on_tk_thread': int(main_thread in archive_threads),
                'background_archive_threads': len(archive_threads - {main_thread}),
                'recovered': not app.core_chat_sync_failed and 'Synthetic reply' in app.chat.get('1.0', 'end'),
            }
            args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            if timer: app.root.after_cancel(timer)
            close_app(app)


if __name__ == '__main__':
    main()
