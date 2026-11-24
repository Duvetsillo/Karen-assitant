"""Real loopback REST/WebSocket test server; no household device is contacted."""
import asyncio
import json
from pathlib import Path
import tempfile
import threading
import unittest

try:
    from aiohttp import web
except ImportError:
    web = None

from karen_core2.home import HomeAssistant, save_config, validate_config


@unittest.skipIf(web is None, 'Optional requirements-home.txt not installed')
class HomeEngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = 'off'
        self.calls = []
        self.ws_count = 0
        self.disconnect_once = False
        self.auth_fail = False
        self.bad_rest = False
        self.volume = .1
        app = web.Application()
        app.router.add_get('/api/states', self.states)
        app.router.add_post('/api/services/{domain}/{service}', self.control)
        app.router.add_get('/api/websocket', self.socket)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.config = {'url': f'http://127.0.0.1:{port}', 'token': 'synthetic-private-token',
                       'allowed': {'light.test': ['turn_on', 'turn_off'], 'media_player.test': ['volume_set']}, 'blocked': []}
        self.client = HomeAssistant(self.config)

    async def asyncTearDown(self):
        self.client.http.close()
        await self.runner.cleanup()

    async def states(self, request):
        self.assertEqual(request.headers.get('Authorization'), 'Bearer synthetic-private-token')
        if self.bad_rest:
            return web.Response(status=503, text='synthetic-private-token')
        return web.json_response([{'entity_id': 'light.test', 'state': self.state},
            {'entity_id': 'media_player.test', 'state': 'on', 'attributes': {'volume_level': self.volume}},
            {'entity_id': 'lock.test', 'state': 'locked'}])

    async def control(self, request):
        body = await request.json()
        self.calls.append(body)
        if request.match_info['service'] == 'volume_set':
            self.volume = body['volume_level']
        else:
            self.state = {'turn_on': 'on', 'turn_off': 'off'}[request.match_info['service']]
        return web.json_response([])

    async def socket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_count += 1
        await ws.send_json({'type': 'auth_required'})
        auth = await ws.receive_json()
        self.assertEqual(auth, {'type': 'auth', 'access_token': 'synthetic-private-token'})
        await ws.send_json({'type': 'auth_invalid' if self.auth_fail else 'auth_ok'})
        if self.auth_fail:
            await ws.close()
            return ws
        async for message in ws:
            data = json.loads(message.data)
            if data['type'] == 'subscribe_events':
                await ws.send_json({'id': data['id'], 'type': 'result', 'success': True, 'result': None})
                if self.disconnect_once and self.ws_count == 1:
                    await ws.close()
                    break
                for entity in ('sensor.ignore', 'light.test'):
                    await ws.send_json({'id': data['id'], 'type': 'event', 'event': {'time_fired': '2026-11-20T12:00:00Z',
                        'data': {'entity_id': entity, 'old_state': {'state': 'off'},
                                 'new_state': {'state': 'on', 'attributes': {'private_data': 'never-retain'}}}}})
            else:
                registry = {'config/area_registry/list': [{'area_id': 'room', 'name': 'Room'}],
                            'config/device_registry/list': [{'id': 'dev', 'area_id': 'room'}],
                            'config/entity_registry/list': [{'entity_id': 'light.test', 'device_id': 'dev'}]}
                await ws.send_json({'id': data['id'], 'type': 'result', 'success': True, 'result': registry[data['type']]})
        return ws

    async def test_discovery_control_and_postcondition_use_real_http(self):
        rows = await asyncio.to_thread(self.client.states)
        self.assertEqual(len(rows), 3)
        self.assertTrue(self.client.status()['rest_connected'])
        result = await asyncio.to_thread(self.client.control, 'light.test', 'turn_on', approve=lambda _: True)
        self.assertTrue(result['verified'])
        self.assertEqual(self.calls, [{'entity_id': 'light.test'}])
        result = await asyncio.to_thread(self.client.control, 'media_player.test', 'volume_set', {'volume_level': .3}, approve=lambda _: True)
        self.assertTrue(result['verified'])

    async def test_denials_never_send_services(self):
        for entity, service, data, approve in (
            ('lock.test', 'unlock', None, lambda _: True),
            ('light.unknown', 'turn_on', None, lambda _: True),
            ('light.test', 'turn_on', None, None),
            ('light.test', 'turn_on', {'entity_id': 'lock.test'}, lambda _: True),
            ('media_player.test', 'volume_set', {'volume_level': float('nan')}, lambda _: True)):
            with self.subTest(entity=entity), self.assertRaises((ValueError, PermissionError)):
                await asyncio.to_thread(self.client.control, entity, service, data, approve=approve)
        self.client.config['blocked'] = ['light.test']
        with self.assertRaises(PermissionError):
            self.client.control('light.test', 'turn_on', approve=lambda _: True)
        self.assertEqual(self.calls, [])

    async def test_unavailable_entity_and_unknown_postcondition_never_confirm_success(self):
        self.state = 'unavailable'
        with self.assertRaises(ValueError):
            await asyncio.to_thread(self.client.control, 'light.test', 'turn_on', approve=lambda _: True)
        self.assertEqual(self.calls, [])

    async def test_rest_failure_is_sanitized_and_subsequent_read_recovers(self):
        self.bad_rest = True
        with self.assertRaises(ConnectionError) as error:
            await asyncio.to_thread(self.client.states)
        self.assertNotIn(self.config['token'], str(error.exception))
        self.assertFalse(self.client.status()['rest_connected'])
        self.bad_rest = False
        await asyncio.to_thread(self.client.states)
        self.assertTrue(self.client.status()['rest_connected'])
        self.assertNotIn(self.config['token'], json.dumps(self.client.status()))

    async def test_registry_discovery_and_relationship_fields(self):
        result = await self.client.registries()
        self.assertEqual(result['entities'][0]['device_id'], result['devices'][0]['id'])
        self.assertEqual(result['devices'][0]['area_id'], result['areas'][0]['area_id'])

    async def test_events_filter_reconnect_and_cancel(self):
        self.disconnect_once = True
        stop, events = threading.Event(), []
        def receive(event):
            events.append(event)
            stop.set()
        await asyncio.wait_for(self.client.watch(stop, receive, entities={'light.test'}), 8)
        self.assertGreaterEqual(self.ws_count, 2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['entity_id'], 'light.test')
        self.assertNotIn('private_data', json.dumps(events))
        self.assertFalse(self.client.status()['events_connected'])

    async def test_invalid_auth_stops_without_retries_or_secrets(self):
        self.auth_fail = True
        await self.client.watch(threading.Event(), lambda _: None, entities={'light.test'})
        self.assertEqual(self.ws_count, 1)
        self.assertEqual(self.client.status()['last_error'], 'auth_failed')
        self.assertNotIn(self.config['token'], json.dumps(self.client.status()))

    async def test_core_plan_enforces_approval_and_records_verified_procedure(self):
        from karen_core2.runtime import CoreRuntime
        from qa.test_core2_mobile import FakeModels
        with tempfile.TemporaryDirectory() as folder:
            runtime = CoreRuntime(archive_path=Path(folder) / 'core.db', task_path=Path(folder) / 'tasks.db', models=FakeModels())
            runtime._home = self.client
            plan = runtime.plans.create({'goal': 'Encender entidad de prueba local', 'steps': [
                {'id': 'light', 'label': 'Controlar luz sintética', 'tool': 'home_control',
                 'args': {'entity_id': 'light.test', 'service': 'turn_on'}, 'depends': []}]})
            denied = await asyncio.to_thread(runtime.run, plan['id'])
            self.assertEqual(denied['status'], 'awaiting_approval')
            self.assertEqual(self.calls, [])
            result = await asyncio.to_thread(runtime.run, plan['id'], approve=lambda _: True)
            self.assertEqual(result['status'], 'completed')
            self.assertTrue(result['steps'][0]['result']['verified'])
            memory = runtime.memory.record_procedure(result)
            self.assertEqual(runtime.memory.procedure(memory['id'])['successful_runs'], 1)


class HomeConfigTests(unittest.TestCase):
    def test_secure_configuration_roundtrip_and_no_plaintext_token(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ha.dpapi'
            save_config({'url': 'http://127.0.0.1:8123', 'token': 'synthetic-secret'}, path)
            self.assertNotIn('synthetic-secret', path.read_text())
            self.assertEqual(HomeAssistant(path=path).config['token'], 'synthetic-secret')

    def test_remote_http_credentials_in_url_and_admin_services_rejected(self):
        for url in ('http://192.168.1.2:8123', 'https://name:secret@example.test', 'https://example.test/path'):
            with self.assertRaises(ValueError):
                validate_config({'url': url, 'token': 'synthetic'})
        with self.assertRaises(ValueError):
            validate_config({'url': 'https://example.test', 'token': 'synthetic', 'allowed': {'lock.test': ['unlock']}})

    def test_revocation_is_rechecked_after_interactive_approval(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ha.dpapi'
            config = {'url': 'http://127.0.0.1:8123', 'token': 'synthetic', 'allowed': {'light.test': ['turn_on']}}
            save_config(config, path)
            session = Mock()
            client = HomeAssistant(path=path, session=session)
            def approve(_):
                config['blocked'] = ['light.test']
                save_config(config, path)
                return True
            with self.assertRaises(PermissionError):
                client.control('light.test', 'turn_on', approve=approve)
            session.request.assert_not_called()

    def test_legacy_discovery_uses_shared_secure_configuration_without_granting_control(self):
        from unittest.mock import Mock, patch
        from ha_control import HomeAssistantDiscovery
        config = {'url': 'https://example.test', 'token': 'synthetic', 'allowed': {}}
        with patch.dict('os.environ', {'KAREN_HA_API_URL': '', 'KAREN_HA_API_TOKEN': ''}), \
                patch('karen_core2.home.HomeAssistant', return_value=Mock(config=config)):
            discovery = HomeAssistantDiscovery()
            self.assertEqual(discovery.url, config['url'])
            self.assertEqual(discovery.token, config['token'])
            self.assertEqual(config['allowed'], {})


if __name__ == '__main__':
    unittest.main()
