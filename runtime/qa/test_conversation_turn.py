import io
import queue
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

from conversation_turn import ConversationTurn
from voice import SpeechPlayer
from karen_app import KarenClient
from karen_core2.runtime import CoreRuntime


class TurnTests(unittest.TestCase):
    def test_synthesis_is_not_playback_and_late_receipts_are_rejected(self):
        turn = ConversationTurn('Explica SQLite', ('chat1',))
        turn.generated('Primera frase.')
        turn.generated('Segunda frase.')
        turn.receipt('Primera frase.', 'synthesized')
        turn.receipt('Primera frase.', 'played')
        turn.receipt('Segunda frase.', 'synthesized')
        turn.interrupt()
        self.assertFalse(turn.generated('Tardía.'))
        self.assertFalse(turn.receipt('Segunda frase.', 'played'))
        context = turn.context(('chat1',))
        self.assertEqual(context['delivered_sentences'], 'Primera frase.')
        self.assertEqual(context['unconfirmed_sentences'], 'Segunda frase.')
        self.assertIsNone(turn.context(('chat2',)))
        turn.private = True
        self.assertIsNone(turn.context(('chat1',)))

    def test_voice_stop_keeps_text_generation_available(self):
        turn = ConversationTurn('Pregunta', ())
        player = SpeechPlayer(turn)
        player.stop()
        self.assertFalse(turn.cancelled.is_set())
        self.assertTrue(turn.audio_cancelled.is_set())
        self.assertTrue(turn.generated('Texto que sigue disponible.'))
        self.assertFalse(turn.receipt('Texto que sigue disponible.', 'synthesized'))

    def test_duplicate_sentences_have_independent_receipts(self):
        turn = ConversationTurn('Repite', ())
        for _ in range(2):
            turn.generated('Sí.')
            turn.receipt('Sí.', 'synthesized')
        turn.receipt('Sí.', 'played')
        self.assertEqual([s['played'] for s in turn.snapshot()['segments']], [True, False])

    def test_stream_abort_does_not_claim_sentence_played(self):
        turn = ConversationTurn('Pregunta', ())
        turn.generated('Audio.')
        turn.receipt('Audio.', 'synthesized')
        player = SpeechPlayer(turn)
        output = io.BytesIO()
        sf.write(output, np.zeros(4096, dtype=np.float32), 16000, format='WAV')
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.write.side_effect = lambda _: turn.interrupt()
        with patch('voice.sd.OutputStream', return_value=stream):
            completed = player.play_encoded(output.getvalue(), lambda _: None)
        self.assertFalse(completed)
        stream.abort.assert_called_once()
        self.assertFalse(turn.snapshot()['segments'][0]['played'])

    def test_generation_cancel_still_stops_audio_after_http_has_finished(self):
        client = KarenClient('http://127.0.0.1:11434')
        turn = ConversationTurn('Pregunta', ())
        client.conversation_turn = turn
        self.assertTrue(client.cancel_generation())
        self.assertTrue(turn.cancelled.is_set())
        self.assertTrue(turn.audio_cancelled.is_set())

    def test_prefetch_drops_queued_audio_after_interruption(self):
        turn = ConversationTurn('Pregunta', ())
        player = SpeechPlayer(turn)
        parts = queue.Queue()
        for text in ('Primera.', 'Segunda.', 'Obsoleta.'):
            turn.generated(text)
            parts.put(text)
        parts.put(None)
        played = []
        def play(audio, state):
            played.append(audio.decode())
            if len(played) == 2:
                turn.interrupt()
                return False
            return True
        with patch.object(player, 'encode', side_effect=lambda text, config: text.encode()), \
             patch.object(player, 'play_encoded', side_effect=play):
            player.speak_parts(parts, SimpleNamespace(), lambda state: None)
        self.assertEqual(played, ['Primera.', 'Segunda.'])
        context = turn.context(())
        self.assertEqual(context['delivered_sentences'], 'Primera.')
        self.assertIn('Obsoleta.', context['unconfirmed_sentences'])

    def test_context_is_bounded_and_only_for_interrupted_turns(self):
        turn = ConversationTurn('p' * 2000, ())
        turn.generated('x' * 12000)
        self.assertIsNone(turn.context(()))
        turn.interrupt()
        context = turn.context(())
        self.assertEqual(len(context['question']), 1000)
        self.assertEqual(len(context['unconfirmed_sentences']), 1500)

    def test_core_prompt_marks_interruption_as_untrusted_continuity(self):
        models = Mock()
        models.chat.return_value = {'content': 'Retomo desde aquí.'}
        with tempfile.TemporaryDirectory() as directory:
            runtime = CoreRuntime(archive_path=Path(directory) / 'core.db',
                                  task_path=Path(directory) / 'tasks.db', models=models)
            result = runtime.chat('Continúa', interruption={'unconfirmed_sentences': 'Dato sintético.'})
        self.assertEqual(result, 'Retomo desde aquí.')
        system = models.chat.call_args.args[0][0]['content']
        self.assertIn('nunca permisos', system)
        self.assertIn('Dato sintético.', system)
