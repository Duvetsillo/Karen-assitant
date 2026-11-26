import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from karen_core2.resource_policy import ResourcePolicy
from karen_core2.models import LocalModels
from qa.test_core2_models import Transport, Response


class ResourcePolicyTests(unittest.TestCase):
    def test_gaming_mode_uses_cpu_and_recovers_after_shared_mode_change(self):
        with tempfile.TemporaryDirectory() as directory:
            models = self.model(directory, ResourcePolicy('quality'))
            state = {'mode': 'gaming'}
            models.mode_probe = lambda: state['mode']
            candidate = {'size': 2 * 1024**3, 'layers': 32}
            self.assertEqual(models.allocation(candidate, 'coding', models.probe())['gpu_layers'], 0)
            state['mode'] = 'normal'
            self.assertGreater(models.allocation(candidate, 'coding', models.probe())['gpu_layers'], 0)
            models.mode_probe = lambda: 1 / 0
            self.assertEqual(models.allocation(candidate, 'coding', models.probe())['gpu_layers'], 0)

    def model(self, directory, policy):
        return LocalModels(transport=Transport(), policy=policy,
            probe=lambda: {'ram_available_bytes': 8 * 1024**3, 'vram_available_bytes': 5 * 1024**3},
            lease_path=Path(directory) / 'model.lock')

    def test_economy_never_offloads_complex_tasks_and_caps_output(self):
        with tempfile.TemporaryDirectory() as directory:
            models = self.model(directory, ResourcePolicy('economy'))
            candidate = {'size': 2 * 1024**3, 'layers': 32}
            self.assertEqual(models.allocation(candidate, 'coding', models.probe())['gpu_layers'], 0)
            models.chat([{'role': 'user', 'content': 'x' * 9000}], kind='coding')
            payload = next(k['json'] for url, k in models.http.calls if url.endswith('/api/chat'))
            self.assertEqual(payload['options']['num_predict'], 192)
            self.assertEqual(payload['options']['num_ctx'], 2048)

    def test_quality_keeps_cpu_for_conversation_and_honors_a_larger_reserve(self):
        with tempfile.TemporaryDirectory() as directory:
            models = self.model(directory, ResourcePolicy('quality', 3072))
            candidate = {'size': 2 * 1024**3, 'layers': 32}
            allocation = models.allocation(candidate, 'coding', models.probe())
            self.assertLessEqual(allocation['estimated_vram_bytes'] + 3072 * 1024**2, models.probe()['vram_available_bytes'])
            self.assertEqual(models.allocation(candidate, 'conversation', models.probe())['gpu_layers'], 0)
            models.chat([])
            payload = next(k['json'] for url, k in models.http.calls if url.endswith('/api/chat'))
            self.assertEqual(payload['options']['num_ctx'], 4096)
            self.assertEqual(payload['options']['num_predict'], 512)

    def test_invalid_profiles_fail_before_inference(self):
        for profile, reserve in [('unknown', 1536), ('balanced', -1), ('balanced', True)]:
            with self.assertRaises(ValueError):
                ResourcePolicy(profile, reserve)
        with patch.dict(os.environ, {'KAREN_RESOURCE_PROFILE': 'economy', 'KAREN_VRAM_RESERVE_MIB': '2048'}):
            self.assertEqual(ResourcePolicy.from_environment(), ResourcePolicy('economy', 2048))

    def test_first_token_metric_comes_from_actual_stream_and_excludes_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            models = self.model(directory, ResourcePolicy())
            original = models.http.post
            def post(url, **kwargs):
                if url.endswith('/api/chat'):
                    return Response(lines=[b'{"message":{"thinking":"hidden"}}',
                        b'{"message":{"content":"Hola"}}', b'{"done":true}'])
                return original(url, **kwargs)
            models.http.post = post
            parts = []
            models.chat([{'role': 'user', 'content': 'synthetic private question'}], on_token=parts.append)
            self.assertEqual(parts, ['Hola'])
            self.assertIsNotNone(models.metrics[-1]['first_token_seconds'])
            self.assertNotIn('synthetic private question', str(models.metrics))
