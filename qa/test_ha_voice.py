import base64
import io
import unittest
import wave
from unittest.mock import patch

from ha_voice import transcribe


class HAVoiceTests(unittest.TestCase):
    def test_wav_is_decoded_into_existing_worker_without_disk_audio(self):
        output = io.BytesIO()
        pcm = b'\0\0' * 1600
        with wave.open(output, 'wb') as target:
            target.setnchannels(1); target.setsampwidth(2); target.setframerate(16000)
            target.writeframes(pcm)
        with patch('voice_local.operation', return_value={'text': 'Karen prueba local'}) as worker:
            self.assertEqual(transcribe(output.getvalue()), {'text': 'Karen prueba local'})
        request = worker.call_args.args[0]
        self.assertEqual(base64.b64decode(request['audio']), pcm)
        self.assertEqual(request['engine'], 'faster-small')

    def test_limits_invalid_pcm_and_wrong_rate_are_rejected_without_models(self):
        for audio in (b'', b'odd', b'\0' * 1_920_045):
            with self.assertRaises(ValueError), patch('voice_local.operation') as worker:
                transcribe(audio)
                worker.assert_not_called()
        output = io.BytesIO()
        with wave.open(output, 'wb') as target:
            target.setnchannels(1); target.setsampwidth(2); target.setframerate(24000)
            target.writeframes(b'\0\0' * 2400)
        with self.assertRaises(ValueError):
            transcribe(output.getvalue())

    def test_silence_never_returns_a_fabricated_transcript(self):
        with patch('voice_local.operation', return_value={'text': ''}), self.assertRaises(ValueError):
            transcribe(b'\0\0' * 160)
