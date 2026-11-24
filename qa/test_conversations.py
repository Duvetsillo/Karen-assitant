"""Offline regression checks for persisted context and the Ollama chat contract."""
import json
import gc
from dataclasses import replace
import threading
import time
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversations import Conversations
from karen_app import KarenClient
from karen_app import KarenApp
from config import load_config
from qa.ui_helpers import wait_archive, close_app, pump_until


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'history.db'
        self.archive = Conversations(self.path)
        self.chat_id = self.archive.current()
        self.client = KarenClient('http://localhost:11434')
        self.client.archive = self.archive
        self.client.chat_id = self.chat_id

    def tearDown(self):
        # Tk variables must be finalized on the thread that created the root.
        gc.collect()
        self.temp.cleanup()

    def test_restore_isolation_and_failed_turns(self):
        self.archive.append(self.chat_id, 'Mi nombre es Ana', 'Hola Ana', True)
        self.archive.append(self.chat_id, 'Pregunta fallida', 'Error de conexión:', False)
        restored = Conversations(self.path)
        self.assertEqual(restored.current(), self.chat_id)
        self.assertEqual(len(restored.exchanges(self.chat_id)), 2)
        self.assertEqual(len(restored.context(self.chat_id)), 2)
        other = restored.create()
        self.assertEqual(restored.context(other), [])
        self.assertEqual(restored.current(), other)
        restored.activate(self.chat_id)
        self.assertEqual(Conversations(self.path).current(), self.chat_id)
        self.assertEqual(restored.context(self.chat_id, max_chars=3), [])

    @patch('admin_tools.route_local', return_value=None)
    @patch('karen_app.requests.post')
    def test_chat_context_and_success_commit(self, post, route):
        self.archive.append(self.chat_id, 'Mi nombre es Ana', 'Hola Ana', True)
        post.return_value.json.return_value = {'message': {'content': 'Te llamas Ana', 'thinking': 'PRIVATE'}}
        self.assertEqual(self.client.ask('¿Cómo me llamo?'), 'Te llamas Ana')
        payload = post.call_args.kwargs['json']
        self.assertTrue(post.call_args.args[0].endswith('/api/chat'))
        self.assertEqual([m['role'] for m in payload['messages']], ['system','user','assistant','user'])
        self.assertEqual(payload['messages'][1]['content'], 'Mi nombre es Ana')
        self.assertEqual(len(self.archive.context(self.chat_id)), 4)
        self.assertNotIn('PRIVATE', str(self.archive.exchanges(self.chat_id)))

    @patch('admin_tools.route_local', return_value=None)
    @patch('karen_app.requests.post')
    def test_stream_and_failure(self, post, route):
        post.return_value.iter_lines.return_value = [json.dumps({'message': {'content': 'Hola.', 'thinking': 'PRIVATE'}, 'done': True}).encode()]
        spoken = []
        self.assertEqual(self.client.ask('Hola', spoken.append), 'Hola.')
        self.assertEqual(spoken, ['Hola.'])
        post.return_value.iter_lines.return_value = [b'{"message":{"content":"Incomplete"}}']
        self.assertTrue(self.client.ask('Falla', spoken.append).startswith('Error de conexión:'))
        self.assertEqual(len(self.archive.context(self.chat_id)), 2)

    @patch('admin_tools.route_local', return_value=None)
    @patch('karen_app.requests.post')
    def test_cancel_stream_discards_partial_answer_and_history(self, post, route):
        spoken = []
        def lines():
            yield json.dumps({'message': {'content': 'Primera. Continuación'}, 'done': False}).encode()
            self.assertTrue(self.client.cancel_generation())
            yield json.dumps({'message': {'content': ' obsoleta.'}, 'done': True}).encode()
        post.return_value.iter_lines.return_value = lines()
        answer = self.client.ask('Hola', spoken.append)
        self.assertEqual(answer, 'Respuesta cancelada.')
        self.assertEqual(spoken, ['Primera.'])
        self.assertEqual(self.archive.exchanges(self.chat_id), [])
        post.return_value.close.assert_called()

    @patch('admin_tools.route_local', return_value='Estado real del PC')
    def test_local_result_is_available_in_context(self, route):
        self.client.ask('Revisa mi PC')
        self.assertEqual(self.archive.context(self.chat_id)[1]['content'], 'Estado real del PC')

    @patch('admin_tools.route_local', return_value=None)
    @patch('karen_app.requests.post')
    def test_personalized_contract_unchanged(self, post, route):
        self.client.backend = 'karen'
        post.return_value.json.return_value = {'respuesta': 'Hola'}
        self.client.ask('Hola')
        self.assertEqual(post.call_args.kwargs['json'], {'mensaje': 'Hola', 'session_id': self.client.session_id})

    def test_desktop_restore_new_chat_and_pending_guard(self):
        self.archive.append(self.chat_id, 'Mi nombre es Ana', 'Hola Ana', True)
        with patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)), patch.object(KarenApp, 'load_catalog'), patch.object(KarenApp, 'connect_benchmark'):
            app = KarenApp(load_config())
            try:
                wait_archive(app)
                self.assertIn('Hola Ana', app.chat.get('1.0', 'end'))
                self.assertEqual(app.client.chat_id, self.chat_id)
                app.request_pending = True
                app.change_conversation(new=True)
                self.assertEqual(app.chat_id, self.chat_id)
                app.request_pending = False
                old_session = app.client.session_id
                app.change_conversation(new=True)
                wait_archive(app)
                self.assertNotEqual(app.client.session_id, old_session)
                self.assertNotIn('Hola Ana', app.chat.get('1.0', 'end'))
                index = next(i for i, row in enumerate(app.chat_choices) if row[0] == self.chat_id)
                app.conversation_selector.current(index)
                app.change_conversation()
                wait_archive(app)
                self.assertEqual(app.client.session_id, old_session)
                self.assertIn('Hola Ana', app.chat.get('1.0', 'end'))
                app.root.geometry('1180x850')
                app.root.update()
                self.assertGreater(app.conversation_selector.winfo_width(), 150)
                import threading
                import tkinter as tk
                event, decision = threading.Event(), {'approved': False}
                request = {'tool':'admin_power','target':'Este PC','reason':'Confirmar cambio crítico.', 'arguments':{'operation':'shutdown'}}
                app.show_admin_confirmation(request, event, decision)
                app.root.update()
                dialog = next(child for child in app.root.winfo_children() if isinstance(child,tk.Toplevel))
                controls = dialog.winfo_children()[-1]
                cancel = next(child for child in controls.winfo_children() if child.cget('text') == 'Cancelar')
                cancel.invoke()
                self.assertTrue(event.is_set())
                self.assertFalse(decision['approved'])
                event.clear()
                app.show_admin_confirmation(request,event,decision)
                app.root.update()
                dialog = next(child for child in app.root.winfo_children() if isinstance(child,tk.Toplevel))
                controls = dialog.winfo_children()[-1]
                approve = next(child for child in controls.winfo_children() if child.cget('text') == 'Aprobar esta operación')
                approve.invoke()
                self.assertTrue(event.is_set())
                self.assertTrue(decision['approved'])
            finally:
                close_app(app)

    def test_desktop_streams_text_without_tts_and_clears_preview(self):
        with (patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)),
              patch.object(KarenApp, 'load_catalog'),
              patch.object(KarenApp, 'connect_benchmark'),
              patch.object(KarenApp, 'ensure_target', return_value=True)):
            app = KarenApp(replace(load_config(), tts_enabled=False))
            try:
                wait_archive(app)
                seen = []
                def answer(prompt, on_sentence=None):
                    self.assertIsNotNone(on_sentence)
                    on_sentence('Respuesta progresiva.')
                    seen.append(prompt)
                    return 'Respuesta progresiva.'
                app.client.archive_error = None
                with patch.object(app.client, 'ask', side_effect=answer):
                    app.send_prompt('Hola')
                    app.request_thread.join(timeout=2)
                    time.sleep(0.06)
                    app.root.update()
                self.assertEqual(seen, ['Hola'])
                self.assertIn('Respuesta progresiva.', app.chat.get('1.0', 'end'))
                self.assertEqual(app.stream_preview.cget('text'), '')
            finally:
                close_app(app)

    def test_desktop_local_mode_works_without_model_catalog(self):
        with (patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)),
              patch.object(KarenApp, 'load_catalog'),
              patch.object(KarenApp, 'connect_benchmark'),
              patch.object(KarenApp, 'ensure_target', return_value=False) as target,
              patch('karen_app.requests.post') as post):
            app = KarenApp(replace(load_config(), tts_enabled=False))
            try:
                wait_archive(app)
                app.send_prompt('/modo gaming')
                app.request_thread.join(timeout=2)
                time.sleep(0.06)
                app.root.update()
                self.assertEqual(self.archive.get_mode(), 'gaming')
                target.assert_not_called()
                post.assert_not_called()
                app.send_prompt('Hola')
                target.assert_called_once()
                post.assert_not_called()
            finally:
                close_app(app)

    def test_queued_voice_transcript_cannot_overlap_finishing_request(self):
        with (patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)),
              patch.object(KarenApp, 'load_catalog'),
              patch.object(KarenApp, 'connect_benchmark'),
              patch.object(KarenApp, 'ensure_target') as target):
            app = KarenApp(replace(load_config(), tts_enabled=False, wake_auto_start=False))
            try:
                wait_archive(app)
                app.request_pending = True
                app.busy.set()
                with patch.object(app.client, 'ask') as ask:
                    app.send_prompt('Segunda orden', from_voice=True)
                self.assertFalse(app.busy.is_set())
                self.assertTrue(app.request_pending)
                self.assertIsNone(app.request_thread)
                self.assertEqual(self.archive.exchanges(self.chat_id), [])
                target.assert_not_called()
                ask.assert_not_called()
                self.assertIn('repite el comando', app.chat.get('1.0', 'end'))
            finally:
                app.request_pending = False
                close_app(app)

    def test_desktop_cancel_button_stops_stream_without_saving_turn(self):
        started, released = threading.Event(), threading.Event()
        def lines():
            started.set()
            yield json.dumps({'message': {'content': 'Parcial. Continuación'}, 'done': False}).encode()
            released.wait(2)
            yield json.dumps({'message': {'content': ' obsoleta.'}, 'done': True}).encode()
        with (patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)),
              patch.object(KarenApp, 'load_catalog'),
              patch.object(KarenApp, 'connect_benchmark'),
              patch.object(KarenApp, 'ensure_target', return_value=True),
              patch('karen_app.requests.post') as post):
            post.return_value.iter_lines.side_effect = lines
            post.return_value.close.side_effect = released.set
            app = KarenApp(replace(load_config(), tts_enabled=False))
            try:
                wait_archive(app)
                app.send_prompt('Hola')
                self.assertTrue(started.wait(1))
                pump_until(app, lambda: app.cancel_generation_button.cget('state') == 'normal')
                self.assertEqual(app.cancel_generation_button.cget('state'), 'normal')
                app.cancel_generation_button.invoke()
                app.request_thread.join(2)
                time.sleep(0.06)
                app.root.update()
                self.assertFalse(app.request_thread.is_alive())
                self.assertIn('Respuesta cancelada.', app.chat.get('1.0', 'end'))
                self.assertEqual(self.archive.exchanges(self.chat_id), [])
                self.assertEqual(app.cancel_generation_button.cget('state'), 'disabled')
            finally:
                released.set()
                close_app(app)

    def test_shared_chat_updates_from_other_process_without_switching(self):
        with (patch.dict('os.environ', {'KAREN_CORE_DB': str(self.path)}),
              patch('karen_app.open_archive', return_value=(self.archive, self.chat_id, None)),
              patch.object(KarenApp, 'load_catalog'),
              patch.object(KarenApp, 'connect_benchmark')):
            app = KarenApp(replace(load_config(), tts_enabled=False, wake_auto_start=False))
            try:
                wait_archive(app)
                app.root.after_cancel(app.core_chat_timer)
                other = Conversations(self.path)
                external_id = other.create()
                other.append(external_id, 'Desde Pet', 'Primera respuesta', True)
                app.poll_core_chats()
                wait_archive(app)
                self.assertEqual(app.chat_id, self.chat_id)
                index = next(i for i, row in enumerate(app.chat_choices) if row[0] == external_id)
                app.conversation_selector.current(index)
                app.change_conversation()
                wait_archive(app)
                self.assertIn('Primera respuesta', app.chat.get('1.0', 'end'))
                other.append(external_id, 'Segundo turno', 'Segunda respuesta', True)
                app.root.after_cancel(app.core_chat_timer)
                app.poll_core_chats()
                wait_archive(app)
                self.assertIn('Segunda respuesta', app.chat.get('1.0', 'end'))
            finally:
                close_app(app)


if __name__ == '__main__':
    unittest.main()
