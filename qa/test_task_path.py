"""The executor and read API must select the same explicit task database."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core_local_api import read_contract
from karen_tasks import TaskEngine, ToolSpec, task_database_path


class TaskPathTests(unittest.TestCase):
    def test_executor_and_api_share_environment_path_without_running_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tasks.sqlite3'
            calls = []
            with patch.dict(os.environ, {'KAREN_TASKS_DB': str(path)}):
                engine = TaskEngine({'check': ToolSpec('read', lambda args, stop: calls.append(True))})
                task_id = engine.create([{'tool': 'check', 'args': {'private': 'not-for-api'}}])
                state = read_contract(Path(directory) / 'core.sqlite3', f'/v1/tasks/{task_id}')
                self.assertEqual(state['task']['status'], 'pending')
                self.assertNotIn('not-for-api', str(state))
                self.assertEqual(calls, [])
                self.assertEqual(task_database_path(), path)

    def test_relative_environment_path_is_rejected_before_creating_data(self):
        with patch.dict(os.environ, {'KAREN_TASKS_DB': 'relative/tasks.sqlite3'}):
            with self.assertRaisesRegex(ValueError, 'absoluta'):
                TaskEngine({})

    def test_explicit_path_wins_over_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            explicit = Path(directory) / 'explicit.sqlite3'
            with patch.dict(os.environ, {'KAREN_TASKS_DB': 'invalid-relative'}):
                self.assertEqual(TaskEngine({}, explicit).path, explicit)


if __name__ == '__main__':
    unittest.main()
