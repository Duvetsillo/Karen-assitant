"""Speech streaming regressions without audio hardware or network access."""
import unittest

from response_stream import FinalSentences


class FinalSentencesTests(unittest.TestCase):
    def test_finish_is_idempotent_and_rejects_late_chunks(self):
        spoken = []
        stream = FinalSentences(spoken.append)
        stream.add('Respuesta final.')
        self.assertEqual(stream.finish(), 'Respuesta final.')
        self.assertEqual(stream.finish(), 'Respuesta final.')
        self.assertEqual(spoken, ['Respuesta final.'])
        with self.assertRaises(ValueError):
            stream.add('Texto tardío')

    def test_large_chunk_does_not_exhaust_python_stack(self):
        spoken = []
        stream = FinalSentences(spoken.append)
        text = 'Hola. ' * 3000 + 'Fin.'
        stream.add(text)
        self.assertEqual(stream.finish(), text)
        self.assertEqual(spoken, ['Hola.'] * 3000 + ['Fin.'])

    def test_decimal_split_across_chunks_stays_together(self):
        spoken = []
        stream = FinalSentences(spoken.append)
        stream.add('Cuesta 3.')
        stream.add('14 euros. Sigue')
        stream.finish()
        self.assertEqual(spoken, ['Cuesta 3.14 euros.', 'Sigue'])

    def test_multiple_chunks_emit_each_sentence_once(self):
        spoken = []
        stream = FinalSentences(spoken.append)
        for chunk in ('Hola. Otra', ' frase. Una', ' más.'):
            stream.add(chunk)
        stream.finish()
        self.assertEqual(spoken, ['Hola.', 'Otra frase.', 'Una más.'])
