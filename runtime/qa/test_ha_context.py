import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from ha_dashboard import redesign

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ha_context', ROOT / 'integrations/home_assistant/custom_components/karen/context.py')
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


def state(entity, value, **attrs):
    return SimpleNamespace(entity_id=entity, state=value, attributes=attrs)


class HomeContextTests(unittest.TestCase):
    def test_context_is_relevant_bounded_and_omits_private_attributes(self):
        states = [state('sensor.token', 'secret'), state('sensor.other', 'private text'),
                  state('device_tracker.phone', 'home', latitude=12),
                  state('light.room', 'on', friendly_name='Habitación', token='secret', entity_picture='/private')]
        result = context.snapshot(states, '¿Qué luces hay?')
        self.assertEqual([x['entity_id'] for x in result], ['light.room'])
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn('latitude', json.dumps(result))
        many = [state('sensor.temperature_' + str(i), '25', friendly_name='a' * 160) for i in range(500)]
        self.assertLessEqual(len(json.dumps(context.snapshot(many, 'temperatura'), ensure_ascii=False)), 3000)

    def test_real_light_readings_and_unknown_states(self):
        answer = context.direct_answer([state('light.a', 'on', friendly_name='Mesa'), state('light.b', 'unavailable'), state('switch.room', 'on', friendly_name='Luz del cuarto')], '¿Qué luces están encendidas?')
        self.assertIn('Mesa', answer)
        self.assertIn('Luz del cuarto', answer)
        self.assertIn('sin estado confirmado', answer)
        self.assertIsNone(context.direct_answer([], 'Enciende las luces'))
        self.assertIsNone(context.direct_answer([], '¿Qué dispositivos están disponibles?'))
        self.assertIn('no disponibles', context.direct_answer([state('switch.a', 'unavailable')], '¿Qué dispositivos están desconectados?'))

    def test_layout_preserves_previous_cards_and_is_idempotent(self):
        old = {'views': [{'path': 'panorama', 'cards': [{'type': 'vertical-stack', 'cards': [
            {'type': 'custom:karen-home-card', 'agent_id': 'conversation.karen'},
            {'type': 'custom:karen-location-card', 'sources': []}]}]},
            {'path': 'homelab', 'sections': [{'cards': [{'type': 'tile', 'entity': 'sensor.custom_existing'}]}]}]}
        result = redesign(old)
        self.assertEqual(old['views'][1]['sections'][0]['cards'][0]['entity'], 'sensor.custom_existing')
        retained = result['views'][1]['cards'][0]['groups'][-1]
        self.assertTrue(retained['collapsed'])
        self.assertEqual(retained['cards'][0]['entity'], 'sensor.custom_existing')
        self.assertEqual(result, redesign(result))
