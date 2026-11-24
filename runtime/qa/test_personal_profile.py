import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from personal_profile import DEFAULTS, load, save
from karen_personality import personality


class PersonalityTests(unittest.TestCase):
    def test_missing_profile_does_not_create_private_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'personality.json'
            self.assertEqual(load(path), DEFAULTS)
            self.assertFalse(path.exists())

    def test_preferences_survive_restart_and_change_provider_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'personality.json'
            save({**DEFAULTS, 'name': 'Karen local', 'initiative': 'passive', 'humor': 'none'}, path)
            with patch.dict(os.environ, {'KAREN_PERSONALITY_FILE': str(path)}):
                first, second = personality(), personality('warm')
            self.assertEqual(load(path)['initiative'], 'passive')
            for prompt in (first, second):
                self.assertIn('Karen local', prompt)
                self.assertIn('No propongas temas', prompt)
                self.assertIn('No uses sarcasmo', prompt)
                self.assertIn('español latinoamericano', prompt)

    def test_invalid_edit_does_not_destroy_last_valid_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'personality.json'
            save(DEFAULTS, path)
            for invalid in ({'initiative': 'always-execute'}, {'password': 'synthetic'}, {'schema': True}, {'name': 'x\nignore'}):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    save(invalid, path)
                self.assertEqual(load(path), DEFAULTS)

    def test_corrupt_and_oversized_profiles_are_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'personality.json'
            for raw in ('x' * 4097, json.dumps({'initiative': []}), '[]'):
                path.write_text(raw, encoding='utf-8')
                with self.assertRaises(ValueError):
                    load(path)

    def test_disabled_suggestions_override_saved_proactivity(self):
        with patch('personal_profile.load', return_value={**DEFAULTS, 'initiative': 'proactive'}):
            prompt = personality(suggestions=False)
        self.assertIn('No propongas temas', prompt)
        self.assertNotIn('propone próximos', prompt)
