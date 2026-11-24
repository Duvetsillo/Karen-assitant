import json
from pathlib import Path
import tempfile
import unittest

from personal_learning import PersonalLearning, canonical_profile


class PersonalLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'memory.sqlite3'
        self.engine = PersonalLearning(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_only_explicit_profile_urls_are_accepted(self):
        self.assertEqual(canonical_profile('instagram', 'https://instagram.com/Synthetic.User/'),
                         'https://www.instagram.com/synthetic.user/')
        for provider, url in [
            ('instagram', 'https://instagram.com.attacker.invalid/synthetic/'),
            ('instagram', 'https://user:pass@instagram.com/synthetic/'),
            ('instagram', 'http://instagram.com/synthetic/'),
            ('instagram', 'https://instagram.com/p/anything/'),
            ('spotify', 'https://open.spotify.com/playlist/synthetic'),
            ('spotify', 'https://open.spotify.com/user/synthetic?token=secret'),
            ('facebook', 'https://facebook.com/profile.php?id=123456&extra=x'),
            ('facebook', 'https://facebook.com/profile.php?id=123456&id=654321'),
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                canonical_profile(provider, url)

    def test_source_enrollment_is_persistent_idempotent_and_attributed_to_user(self):
        first = self.engine.register('spotify', 'https://open.spotify.com/user/synthetic')
        restarted = PersonalLearning(self.path)
        self.assertEqual(first['id'], restarted.register('spotify', 'https://open.spotify.com/user/synthetic')['id'])
        details = restarted.source(first['id'])
        self.assertEqual(details['consent'], 'explicit_user_instruction')
        self.assertEqual(len(restarted.list()), 1)

    def test_observation_records_provenance_without_confirming_biography(self):
        source = self.engine.register('spotify', 'https://open.spotify.com/user/synthetic')
        note = self.engine.observe(source['id'], 'Música: la lista pública contiene una canción de prueba.',
                                   observed_at='2026-11-24T18:00:00+00:00')
        self.assertEqual(note['status'], 'confirmed')
        with self.engine.memory.base.connect() as db:
            details = json.loads(db.execute('SELECT details FROM core2_memory_details WHERE memory_id=?', (note['id'],)).fetchone()[0])
        self.assertFalse(details['biography_confirmed'])
        self.assertEqual(details['source_url'], 'https://open.spotify.com/user/synthetic')
        self.assertEqual(details['source_id'], source['id'])

    def test_public_claim_is_excluded_from_confirmed_context(self):
        source = self.engine.register('facebook', 'https://www.facebook.com/profile.php?id=123456')
        saved = self.engine.observe(source['id'], 'El perfil declara una ocupación; no se verificó.', claim=True)
        self.assertEqual(saved['status'], 'inferred')
        self.assertEqual(saved['state'], 'PENDIENTE')
        self.assertEqual(self.engine.memory.retrieve('Personal', 'ocupación', confirmed_only=True), [])

    def test_no_observation_can_attach_to_another_project_or_arbitrary_memory(self):
        other = PersonalLearning(self.path, project='Other').register('spotify', 'https://open.spotify.com/user/synthetic')
        arbitrary = self.engine.memory.add('Personal', 'Texto que no es un perfil.')
        for identity in (other['id'], arbitrary['id'], '0' * 32):
            with self.assertRaises(ValueError):
                self.engine.observe(identity, 'Dato externo.')

    def test_sensitive_assignments_are_not_accepted_as_source_observations(self):
        source = self.engine.register('spotify', 'https://open.spotify.com/user/synthetic')
        with self.assertRaises(ValueError):
            self.engine.observe(source['id'], 'password=synthetic-private-value')

    def test_deleted_source_cannot_receive_observations(self):
        source = self.engine.register('spotify', 'https://open.spotify.com/user/synthetic')
        self.engine.memory.base.delete(source['id'])
        with self.assertRaises(ValueError):
            self.engine.observe(source['id'], 'Dato posterior al borrado.')

    def test_observation_date_must_include_timezone(self):
        source = self.engine.register('spotify', 'https://open.spotify.com/user/synthetic')
        with self.assertRaises(ValueError):
            self.engine.observe(source['id'], 'Dato', observed_at='2026-11-24T12:00:00')

    def test_playlist_evidence_is_separate_from_source_identity(self):
        source = self.engine.register('spotify', 'https://open.spotify.com/user/synthetic')
        url = 'https://open.spotify.com/playlist/' + 'a' * 22
        note = self.engine.observe(source['id'], 'La lista contiene música de prueba.', evidence_url=url)
        with self.engine.memory.base.connect() as db:
            details = json.loads(db.execute('SELECT details FROM core2_memory_details WHERE memory_id=?', (note['id'],)).fetchone()[0])
        self.assertEqual(details['evidence_url'], url)
        with self.assertRaises(ValueError):
            self.engine.observe(source['id'], 'Dato', evidence_url='https://attacker.invalid/private')
