"""Administration boundaries and tool orchestration without system changes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import admin_runtime
from admin_runtime import AdminRuntime, AdminAudit, ps_literal
from admin_agent import administer, administration_request
from karen_app import KarenClient


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.approvals = []
        self.runtime = AdminRuntime(confirm=lambda request: self.approvals.append(request) or True,
                                    audit=AdminAudit(self.root / 'audit.db'))

    def tearDown(self):
        self.temp.cleanup()

    def test_refused_script_never_executes(self):
        self.runtime.confirm = lambda request: False
        with patch.object(self.runtime, 'powershell') as execute:
            result = self.runtime.execute('admin_powershell', {'script':'Restart-Computer', 'purpose':'Reiniciar', 'verification':'Get-Date'})
            self.assertEqual(result['status'], 'declined')
            execute.assert_not_called()
        self.assertEqual(self.runtime.audit.recent()[0][3], 'declined')

    def test_validation_precedes_execution(self):
        for name, args in [('admin_process_stop', {'pid':'1; Stop-Computer'}),
                           ('admin_power', {'operation':'shutdown','confirmed':True}),
                           ('admin_ssh', {'alias':'untrusted','script':'id','purpose':'test','verification':'id'}),
                           ('unknown', {}), ('admin_powershell', {'script':42,'purpose':'x','verification':'x'})]:
            with patch.object(self.runtime, 'dispatch') as execute:
                self.assertEqual(self.runtime.execute(name,args)['status'], 'failed')
                execute.assert_not_called()
        self.assertEqual(self.approvals, [])

    def test_private_paths_and_remote_shares_blocked(self):
        for path in [str(admin_runtime.ROOT / '.private/conversations.sqlite3'),
                     str(Path.home() / '.ssh/id_rsa'), str(Path.home() / '.codex/auth.json'),
                     'C:\\', r'\\host\share\file', 'relative.txt']:
            with self.assertRaises(ValueError):
                self.runtime.path(path)

    def test_file_write_has_backup_and_real_verification(self):
        path = self.root / 'note.txt'
        path.write_text('old', encoding='utf-8')
        result = self.runtime.execute('admin_file_change', {'operation':'write','path':str(path),'content':'new'})
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['result']['verified'])
        self.assertEqual(Path(result['result']['backup']).read_text(), 'old')
        self.assertEqual(path.read_text(), 'new')
        self.assertEqual(len(self.approvals), 1)
        self.assertNotIn('"content": "new"', self.runtime.audit.recent()[0][2])

    def test_copy_cannot_overwrite(self):
        source, target = self.root / 'source', self.root / 'target'
        source.write_text('source'); target.write_text('target')
        result = self.runtime.execute('admin_file_change', {'operation':'copy','path':str(source),'destination':str(target)})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(target.read_text(), 'target')

    def test_general_script_confirmation_covers_verification(self):
        args = {'script':'Get-Date', 'purpose':'Test', 'verification':'Get-Process'}
        with patch.object(self.runtime, 'powershell', side_effect=['execution','verification']) as execute:
            result = self.runtime.execute('admin_powershell',args)
        self.assertEqual(self.approvals[0]['arguments'],args)
        self.assertEqual(execute.call_count,2)
        self.assertEqual(result['result']['verification_output'],'verification')

    def test_timeout_is_uncertain_and_not_retried(self):
        with patch.object(self.runtime, 'powershell', side_effect=subprocess.TimeoutExpired('powershell',120)) as execute:
            result = self.runtime.execute('admin_powershell', {'script':'x','purpose':'x','verification':'x'})
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(execute.call_count, 1)

    def test_failed_verification_does_not_repeat_mutation(self):
        with patch.object(self.runtime, 'powershell', side_effect=['done', RuntimeError('verification failed')]) as execute:
            result = self.runtime.execute('admin_powershell', {'script':'x','purpose':'x','verification':'x'})
        self.assertEqual(execute.call_count,2)
        self.assertTrue(result['result']['do_not_repeat_execution'])
        self.assertEqual(self.runtime.audit.recent()[0][3], 'verification_failed')

    def test_read_only_requires_no_confirmation(self):
        result = self.runtime.execute('admin_inventory', {'section':'targets'})
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.approvals, [])

    def test_network_scope(self):
        with patch.object(self.runtime, 'dispatch') as execute:
            result = self.runtime.execute('admin_network', {'operation':'port','host':'8.8.8.8','port':443})
            self.assertEqual(result['status'], 'failed')
            execute.assert_not_called()

    def test_shell_literal_and_ssh_input(self):
        self.assertEqual(ps_literal("a'; Stop-Computer; '"), "'a''; Stop-Computer; '''")
        completed = Mock(returncode=0, stdout='ok', stderr='')
        with patch('admin_runtime.subprocess.run', return_value=completed) as run:
            self.runtime.ssh('friday-home', 'echo "$HOME"')
        self.assertEqual(run.call_args.kwargs['input'], b'echo "$HOME"')
        self.assertIn('StrictHostKeyChecking=yes', run.call_args.args[0])

    def test_intent_routing(self):
        self.assertTrue(administration_request('Lista los procesos de mi PC'))
        self.assertTrue(administration_request('Ejecuta PowerShell como administrador'))
        self.assertTrue(administration_request('/admin Muéstrame los equipos'))
        self.assertFalse(administration_request('Cómo reiniciar mi PC'))
        self.assertFalse(administration_request('Consulta mi calendario iCloud'))

    @patch('admin_agent.requests.post')
    def test_loop_consumes_real_tool_results(self, post):
        call = {'function':{'name':'admin_inventory','arguments':{'section':'targets'}}}
        first, second = Mock(), Mock()
        first.json.return_value = {'message':{'role':'assistant','thinking':'PRIVATE','tool_calls':[call]}}
        second.json.return_value = {'message':{'content':'Destinos consultados.'}}
        post.side_effect = [first,second]
        answer = administer(KarenClient('http://localhost:11434'), '/admin Lista los destinos', self.runtime)
        self.assertIn('completed', answer)
        messages = post.call_args.kwargs['json']['messages']
        self.assertEqual(messages[-1]['role'],'tool')
        self.assertNotIn('PRIVATE',str(messages))

    @patch('admin_agent.requests.post')
    def test_loop_stops_when_approval_declined(self, post):
        self.runtime.confirm = lambda request: False
        post.return_value.json.return_value = {'message':{'tool_calls':[{'function':{'name':'admin_power','arguments':{'operation':'shutdown'}}}]}}
        with patch.object(self.runtime,'dispatch') as execute:
            answer = administer(KarenClient('http://localhost:11434'), '/admin Apaga mi PC', self.runtime)
        self.assertIn('rechazada',answer)
        execute.assert_not_called()
        self.assertEqual(post.call_count,1)

    @patch('admin_agent.requests.post')
    def test_duplicate_calls_are_not_executed_twice(self, post):
        call = {'function':{'name':'admin_file_change','arguments':{'operation':'mkdir','path':str(self.root / 'test-folder')}}}
        post.return_value.json.return_value = {'message':{'tool_calls':[call,call]}}
        with patch.object(self.runtime,'dispatch',return_value={}) as execute:
            answer = administer(KarenClient('http://localhost:11434'), '/admin Lista los destinos', self.runtime)
        self.assertIn('repetida',answer)
        self.assertEqual(execute.call_count,1)


if __name__ == '__main__':
    unittest.main()
