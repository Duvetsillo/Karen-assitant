"""Local voice identity, audio transport, authentication and per-request cancellation."""
import io
import threading
import unittest
import wave
from unittest.mock import patch

from mobile_speech import MobileSpeech, SpeechBusy
from qa import test_mobile_server as mobile_tests


def sample():
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(24000)
        stream.writeframes(b'\0\0' * 240)
    return output.getvalue()


class SpeechTests(unittest.TestCase):
    def test_uses_pinned_local_serene_voice_without_changing_profile(self):
        with (patch('expressive_voice.synthesize', return_value=sample()) as synthesize,
              patch('karen_core2.models.LocalModels') as models):
            models.return_value.request.return_value.__enter__.return_value.json.return_value = {'models': []}
            MobileSpeech().render('owner', '1' * 32, '**Hola**')
            self.assertEqual(synthesize.call_args.args[0], 'Hola.')
            self.assertEqual(synthesize.call_args.kwargs, {'style': 'serene'})

    def test_chat_releases_voice_before_reasoning(self):
        with patch('expressive_voice.release', return_value=True) as release:
            MobileSpeech().prepare_chat()
            release.assert_called_once_with()

    def test_light_cpu_chat_keeps_voice_warm_only_with_enough_ram(self):
        with (patch('expressive_voice.release', return_value=True) as release,
              patch('karen_core2.models.resources', return_value={'ram_available_bytes': 4 * 1024**3})):
            MobileSpeech().prepare_chat(lightweight=True)
            release.assert_not_called()
        with (patch('expressive_voice.release', return_value=True) as release,
              patch('karen_core2.models.resources', return_value={'ram_available_bytes': 1024**3})):
            MobileSpeech().prepare_chat(lightweight=True)
            release.assert_called_once_with()

    def test_idle_cleanup_preserves_an_active_synthesis(self):
        speech = MobileSpeech()
        with patch('expressive_voice.release', return_value=True) as release:
            speech.active = (('owner', 'id'), threading.Event())
            self.assertFalse(speech.release_idle())
            release.assert_not_called()
            speech.active = None
            self.assertTrue(speech.release_idle())
            release.assert_called_once_with()

    def test_invalid_parameters_and_invalid_audio_do_not_escape(self):
        speech = MobileSpeech(lambda text, stop: b'invalid')
        for identity, text in [('bad', 'Hola'), ('1' * 32, ''), ('2' * 32, 'x' * 1201), ('3' * 32, {})]:
            with self.assertRaises(ValueError):
                speech.render('owner', identity, text)
        with self.assertRaises(ValueError):
            speech.render('owner', '4' * 32, 'Hola')

    def test_canceled_before_start_and_duplicate_request_never_synthesize(self):
        calls = []
        speech = MobileSpeech(lambda text, stop: calls.append(text) or sample())
        speech.cancel('owner', '1' * 32)
        with self.assertRaises(InterruptedError): speech.render('owner', '1' * 32, 'Hola')
        speech.render('owner', '2' * 32, 'Hola')
        with self.assertRaises(InterruptedError): speech.render('owner', '2' * 32, 'Hola')
        self.assertEqual(len(calls), 1)

    def test_cancel_is_owned_and_overlapping_requests_do_not_queue(self):
        started, stopped = threading.Event(), threading.Event()
        errors = []
        def synthesize(text, stop):
            started.set()
            stop.wait(2)
            if stop.is_set(): stopped.set()
            return sample()
        speech = MobileSpeech(synthesize)
        def work():
            try: speech.render('one', '1' * 32, 'Hola')
            except InterruptedError: errors.append('canceled')
        thread = threading.Thread(target=work)
        thread.start()
        try:
            self.assertTrue(started.wait(1))
            speech.cancel('two', '1' * 32)
            self.assertFalse(stopped.is_set())
            with self.assertRaises(SpeechBusy): speech.render('two', '2' * 32, 'Hola')
            speech.cancel('one', '1' * 32)
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, ['canceled'])
            self.assertTrue(stopped.is_set())
        finally:
            speech.cancel('one', '1' * 32)
            thread.join(2)

    def test_timeout_propagates_to_existing_engine(self):
        def synthesize(text, stop):
            self.assertTrue(stop.wait(1))
            return sample()
        with self.assertRaises(InterruptedError):
            MobileSpeech(synthesize, timeout=.05).render('owner', '1' * 32, 'Hola')


class SpeechHttpTests(unittest.TestCase):
    setUp = mobile_tests.MobileTests.setUp
    tearDown = mobile_tests.MobileTests.tearDown
    request = mobile_tests.MobileTests.request

    def test_release_is_authenticated_and_cannot_choose_operations(self):
        with patch.object(self.app.speech, 'release_idle', return_value=True) as release:
            self.assertEqual(self.request('/api/speech/release', {}, auth=False)[0], 401)
            self.assertEqual(self.request('/api/speech/release', {'force': True})[0], 400)
            release.assert_not_called()
            self.assertEqual(self.request('/api/speech/release', {})[0], 200)
            release.assert_called_once_with()

    def test_audio_has_same_auth_origin_and_host_boundaries(self):
        calls = []
        self.app.speech = MobileSpeech(lambda text, stop: calls.append(text) or sample())
        payload = {'id': '1' * 32, 'text': 'Hola'}
        self.assertEqual(self.request('/api/speech', payload, auth=False)[0], 401)
        self.assertEqual(self.request('/api/speech', payload, origin='https://evil.example')[0], 403)
        self.assertEqual(self.request('/api/speech', payload, host='evil.example')[0], 403)
        self.assertEqual(calls, [])
        status, headers, body = self.request('/api/speech', payload)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'audio/wav')
        self.assertIn("media-src 'self' blob:", headers['Content-Security-Policy'])
        self.assertEqual(body, sample())

    def test_parameters_cannot_select_another_voice_or_provider(self):
        calls = []
        self.app.speech = MobileSpeech(lambda text, stop: calls.append(text) or sample())
        for payload in ({'id': '1' * 32, 'text': 'Hola', 'provider': 'cloud'},
                        {'id': '2' * 32, 'text': 'Hola', 'style': 'bright'},
                        {'id': 'bad', 'text': 'Hola'}, {'id': '3' * 32, 'text': 'x' * 1201}):
            self.assertEqual(self.request('/api/speech', payload)[0], 400)
        self.assertEqual(calls, [])

    def test_cancel_before_start_does_not_render(self):
        calls = []
        self.app.speech = MobileSpeech(lambda text, stop: calls.append(text) or sample())
        self.assertEqual(self.request('/api/speech/cancel', {'id': '1' * 32})[0], 200)
        self.assertEqual(self.request('/api/speech', {'id': '1' * 32, 'text': 'Hola'})[0], 409)
        self.assertEqual(calls, [])

    def test_service_failure_is_reported_without_private_exception_text(self):
        def fail(text, stop): raise RuntimeError('private runtime detail')
        self.app.speech = MobileSpeech(fail)
        status, _, body = self.request('/api/speech', {'id': '1' * 32, 'text': 'Hola'})
        self.assertEqual(status, 503)
        self.assertNotIn(b'private runtime detail', body)


if __name__ == '__main__':
    unittest.main()
