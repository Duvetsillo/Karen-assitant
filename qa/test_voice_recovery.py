"""Regression checks for microphone recovery without opening real hardware."""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import sounddevice as sd

from voice import VoiceListener, CHUNK


class FastStop:
    def __init__(self, stop_after_waits=None):
        self.stopped = False
        self.delays = []
        self.stop_after_waits = stop_after_waits

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.delays.append(seconds)
        if self.stop_after_waits is not None and len(self.delays) >= self.stop_after_waits:
            self.stopped = True
        return False


class SilentStream:
    def __init__(self, stop):
        self.stop = stop

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _):
        self.stop.stopped = True
        return np.zeros(CHUNK, dtype=np.int16).tobytes(), False


class HealthyStream:
    def __init__(self, busy):
        self.busy = busy

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _):
        self.busy.set()
        return np.zeros(CHUNK, dtype=np.int16).tobytes(), False


class TriggeredStream:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _):
        return np.full(CHUNK, 3000, dtype=np.int16).tobytes(), False


class VoiceRecoveryTests(unittest.TestCase):
    def listener(self, stop, states, logs):
        config = SimpleNamespace(wake_word_enabled=False, wake_mode='transcript', rms_threshold=0.02)
        return VoiceListener(config, None, stop, threading.Event(), lambda _: None,
                             states.append, logs.append)

    def test_recovers_after_transient_open_error(self):
        stop, states, logs = FastStop(), [], []
        failure = sd.PortAudioError('busy')
        with patch('voice.sd.RawInputStream', side_effect=[failure, SilentStream(stop)]) as opened:
            self.listener(stop, states, logs).run()
        self.assertEqual(opened.call_count, 2)
        self.assertIn('Recuperando micrófono', states)
        self.assertNotIn('Error', states)
        self.assertIn(1, stop.delays)

    def test_reports_error_and_stops_when_cancelled_after_three_failures(self):
        stop, states, logs = FastStop(stop_after_waits=3), [], []
        with patch('voice.sd.RawInputStream', side_effect=sd.PortAudioError('busy')) as opened:
            self.listener(stop, states, logs).run()
        self.assertEqual(opened.call_count, 3)
        self.assertEqual(states[-1], 'Error')
        self.assertEqual(stop.delays, [1, 2, 3])
        self.assertTrue(any('3 intentos' in item for item in logs))

    def test_recovers_after_more_than_three_errors(self):
        stop, states, logs = FastStop(), [], []
        busy = threading.Event()
        config = SimpleNamespace(wake_word_enabled=False, wake_mode='transcript', rms_threshold=0.02)
        def record(message):
            logs.append(message)
            if 'recuperado' in message:
                stop.stopped = True
        listener = VoiceListener(config, None, stop, busy, lambda _: None, states.append, record)
        with patch('voice.sd.RawInputStream', side_effect=[sd.PortAudioError('busy')] * 4 + [HealthyStream(busy)]) as opened:
            listener.run()
        self.assertEqual(opened.call_count, 5)
        self.assertTrue(any('recuperado' in item for item in logs))
        self.assertEqual(stop.delays[:4], [1, 2, 3, 4])

    def test_retries_new_windows_default_after_device_index_changes(self):
        stop, states, logs = FastStop(), [], []
        listener = self.listener(stop, states, logs)
        listener.device = 1
        devices = [{'max_input_channels': 0}, {'max_input_channels': 0},
                   {'max_input_channels': 1, 'name': 'Nuevo micrófono'}]
        changed = []
        listener.device_changed = lambda index, name: changed.append((index, name))
        with patch('voice.sd.query_devices', return_value=devices), \
             patch('voice.sd.default.device', (2, 0)), \
             patch('voice.sd.RawInputStream', side_effect=[sd.PortAudioError('gone'), SilentStream(stop)]) as opened:
            listener.run()
        self.assertEqual(opened.call_args_list[0].kwargs['device'], 1)
        self.assertEqual(opened.call_args_list[1].kwargs['device'], 2)
        self.assertTrue(any('predeterminado actualizado' in item for item in logs))
        self.assertEqual(changed, [(2, 'Nuevo micrófono')])

    def test_explicit_microphone_selection_is_not_changed(self):
        stop, states, logs = FastStop(stop_after_waits=1), [], []
        listener = self.listener(stop, states, logs)
        listener.config.input_device = 1
        listener.device = 1
        with patch('voice.sd.query_devices') as query, \
             patch('voice.sd.RawInputStream', side_effect=sd.PortAudioError('gone')) as opened:
            listener.run()
        self.assertEqual(opened.call_args.kwargs['device'], 1)
        query.assert_not_called()

    def test_transient_stt_error_reopens_microphone_and_recovers(self):
        stop, states, logs, submitted = FastStop(), [], [], []
        busy = threading.Event()
        config = SimpleNamespace(wake_word_enabled=False, wake_mode='transcript', rms_threshold=0.02)
        def submit(text):
            submitted.append(text)
            busy.clear()
            stop.stopped = True
        listener = VoiceListener(config, None, stop, busy, submit, states.append, logs.append)
        with patch('voice.sd.RawInputStream', side_effect=[TriggeredStream(), TriggeredStream()]) as opened, \
             patch.object(listener, '_record', return_value=np.full(CHUNK, 3000, dtype=np.int16)), \
             patch.object(listener, 'transcribe', side_effect=[OSError('transient'), 'Hola']):
            listener.run()
        self.assertEqual(opened.call_count, 2)
        self.assertEqual(submitted, ['Hola'])
        self.assertIn('Recuperando reconocimiento', states)
        self.assertTrue(any('OSError' in item for item in logs))

    def test_missing_stt_model_stops_retry_and_reports_error(self):
        stop, states, logs = FastStop(), [], []
        listener = self.listener(stop, states, logs)
        with patch('voice.sd.RawInputStream', return_value=TriggeredStream()) as opened, \
             patch.object(listener, '_record', return_value=np.full(CHUNK, 3000, dtype=np.int16)), \
             patch.object(listener, 'transcribe', side_effect=FileNotFoundError('missing')):
            listener.run()
        self.assertEqual(opened.call_count, 1)
        self.assertEqual(states[-1], 'Error')
        self.assertTrue(any('Modelo de reconocimiento no disponible' in item for item in logs))


if __name__ == '__main__':
    unittest.main()
