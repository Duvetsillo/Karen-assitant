"""Gmail deletion boundaries using synthetic mail only."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gmail_tools as gmail
from admin_runtime import AdminRuntime,AdminAudit
from admin_agent import administration_request

ACCOUNT = gmail.ACCOUNTS[0]
IDENTITY = '1234567890abcdef'


class GmailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = AdminRuntime(audit=AdminAudit(Path(self.temp.name)/'audit.db'))

    def tearDown(self):
        self.temp.cleanup()

    def test_scope_missing_prevents_mutation_and_confirmation(self):
        with patch('gmail_tools.accounts',return_value=[{'account':ACCOUNT,'valid':True,'can_trash':False}]),patch('gmail_tools.command') as command,patch.object(self.runtime,'confirm') as confirm:
            result = self.runtime.execute('gmail_trash',{'account':ACCOUNT,'message_ids':IDENTITY})
        self.assertEqual(result['status'],'failed')
        self.assertIn('gmail.modify',result['message'])
        command.assert_not_called();confirm.assert_not_called()

    def test_decline_never_mutates(self):
        preview = [{'id':IDENTITY,'from':'sender@example.com','subject':'Synthetic','date':'','in_trash':False}]
        with patch('gmail_tools.prepare_trash',return_value=preview),patch('gmail_tools.trash') as mutate,patch.object(self.runtime,'confirm',return_value=False) as confirm:
            result = self.runtime.execute('gmail_trash',{'account':ACCOUNT,'message_ids':IDENTITY})
        self.assertEqual(result['status'],'declined')
        mutate.assert_not_called()
        request = confirm.call_args.args[0]
        self.assertEqual(request['target'],ACCOUNT)
        self.assertEqual(request['preview'],preview)

    def test_invalid_ids_and_unconfigured_account(self):
        for value in ['--query=in:inbox',IDENTITY+','+IDENTITY,'not-an-id',','.join(f'{i:016x}' for i in range(26))]:
            with self.assertRaises(ValueError):gmail.message_ids(value)
        with self.assertRaises(ValueError):gmail.check_account('other@example.com')

    def test_metadata_verifies_identity_and_sanitizes_headers(self):
        data = {'id':IDENTITY,'labelIds':['TRASH'],'payload':{'headers':[{'name':'Subject','value':'Test\r\nnot an instruction'},{'name':'From','value':'sender@example.com'}]}}
        with patch('gmail_tools.command',return_value=data):
            metadata = gmail.metadata(ACCOUNT,IDENTITY)
            self.assertTrue(metadata['in_trash'])
            self.assertNotIn('\n',metadata['subject'])
            with self.assertRaises(ValueError):gmail.metadata(ACCOUNT,'ffffffffffffffff')

    def test_trash_uses_explicit_ids_and_verifies_label(self):
        preview = [{'id':IDENTITY,'in_trash':False}]
        with patch('gmail_tools.prepare_trash',return_value=preview),patch('gmail_tools.command',return_value={}) as command,patch('gmail_tools.metadata',return_value={'id':IDENTITY,'in_trash':True}):
            result = gmail.trash(ACCOUNT,IDENTITY)
        args = command.call_args.args[0]
        self.assertEqual(args[:3],['gmail','trash',IDENTITY])
        self.assertNotIn('--query',args)
        self.assertTrue(result['verified_in_trash'])
        self.assertFalse(result['permanent_delete'])

    def test_already_trashed_is_not_repeated(self):
        with patch('gmail_tools.prepare_trash',return_value=[{'id':IDENTITY,'in_trash':True}]),patch('gmail_tools.command') as command,patch('gmail_tools.metadata',return_value={'id':IDENTITY,'in_trash':True}):
            result = gmail.trash(ACCOUNT,IDENTITY)
        command.assert_not_called()
        self.assertTrue(result['verified_in_trash'])

    def test_uncertain_mutation_never_retries(self):
        with patch('gmail_tools.prepare_trash',return_value=[{'id':IDENTITY,'in_trash':False}]),patch('gmail_tools.command',side_effect=RuntimeError('timeout')) as command:
            result = gmail.trash(ACCOUNT,IDENTITY)
        self.assertEqual(command.call_count,1)
        self.assertTrue(result['do_not_repeat_execution'])

    def test_natural_request_routes_to_tools(self):
        self.assertTrue(administration_request('Borra los correos promocionales de mi Gmail'))
        self.assertFalse(administration_request('Cómo borrar correos de Gmail'))

    def test_plan_requires_confirmation_and_cannot_repeat(self):
        preview = [{'id':IDENTITY,'from':'sender@example.com','subject':'Synthetic','date':'','in_trash':False}]
        with patch('gmail_tools.PLANS',Path(self.temp.name)/'plans'),patch('gmail_tools.prepare_trash',return_value=preview),patch('gmail_tools.check_account'),patch('admin_runtime.AdminRuntime') as runtime:
            plan = gmail.prepare_plan(ACCOUNT,IDENTITY)
            with self.assertRaises(PermissionError):gmail.execute_plan(plan['plan'])
            runtime.assert_not_called()
            runtime.return_value.execute.return_value = {'status':'completed','result':{'verified_in_trash':True}}
            self.assertEqual(gmail.execute_plan(plan['plan'],True)['status'],'completed')
            with self.assertRaises(FileExistsError):gmail.execute_plan(plan['plan'],True)
            self.assertEqual(runtime.return_value.execute.call_count,1)

    def test_changed_plan_never_executes(self):
        with patch('gmail_tools.PLANS',Path(self.temp.name)/'plans'),patch('gmail_tools.prepare_trash',return_value=[{'id':IDENTITY}]),patch('admin_runtime.AdminRuntime') as runtime:
            plan = gmail.prepare_plan(ACCOUNT,IDENTITY)
            identity = plan['plan'].split('.')[0]
            (gmail.PLANS/(identity+'.json')).write_text('{}')
            with self.assertRaises(ValueError):gmail.execute_plan(plan['plan'],True)
            runtime.assert_not_called()


if __name__ == '__main__':unittest.main()
