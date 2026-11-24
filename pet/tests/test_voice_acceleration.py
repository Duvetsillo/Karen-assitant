"""Contract tests only; no CUDA model, network, or personal reference needed."""
import json
from pathlib import Path
import sys
import tempfile
import socket
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from voice_acceleration import backend, generate, SpeechCancelled, configure_decoder


class AccelerationTests(unittest.TestCase):
    def test_release_does_not_interrupt_an_active_voice_and_preserves_identity_cache(self):
        from shared_voice_service import VoiceEngine
        with tempfile.TemporaryDirectory() as root:
            engine = VoiceEngine(root)
            engine.model = object()
            engine.prompt = object()
            engine.signature = ('original', 'reference', 'local-model')
            engine.cache['existing'] = b'cached-audio'
            torch = SimpleNamespace(cuda=SimpleNamespace(empty_cache=Mock()))
            with patch.dict(sys.modules, {'torch': torch}):
                with engine.lock:
                    self.assertFalse(engine.release())
                    self.assertIsNotNone(engine.model)
                self.assertTrue(engine.release())
            self.assertIsNone(engine.model)
            self.assertIsNone(engine.prompt)
            self.assertEqual(engine.phase, 'cold')
            self.assertEqual(engine.signature, ('original', 'reference', 'local-model'))
            self.assertEqual(engine.cache['existing'], b'cached-audio')
            torch.cuda.empty_cache.assert_called_once()

    def test_inference_error_diagnostics_do_not_include_exception_message(self):
        from shared_voice_service import VoiceEngine
        with tempfile.TemporaryDirectory() as root:
            engine = VoiceEngine(root)
            operation = Mock(side_effect=RuntimeError('synthetic-private-token-and-text'))
            with self.assertRaises(RuntimeError):
                engine.execute(operation)
            self.assertEqual(engine.phase, 'error')
            self.assertEqual(engine.last_error['type'], 'RuntimeError')
            self.assertNotIn('synthetic-private-token-and-text', json.dumps(engine.last_error))
            engine.model = object()
            with self.assertRaises(SpeechCancelled):
                engine.execute(Mock(side_effect=SpeechCancelled()))
            self.assertEqual(engine.phase, 'ready')

    def test_windows_utf8_bom_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'voice-models').mkdir()
            (root / 'voice-models/tts-runtime.json').write_text(
                json.dumps({'schema': 1, 'backend': 'cuda-graphs-fp32'}), encoding='utf-8-sig')
            self.assertEqual(backend(root), 'cuda-graphs-fp32')

    def test_decoder_oom_retries_same_tokens_once_on_cpu(self):
        class OutOfMemory(RuntimeError):
            pass
        torch = SimpleNamespace(cuda=SimpleNamespace(OutOfMemoryError=OutOfMemory, empty_cache=Mock()),
                                device=lambda name: name, float32='float32')
        original_chunks = Mock()
        decoder = SimpleNamespace(to=Mock(), chunked_decode=Mock())
        decode = Mock(side_effect=[OutOfMemory(), ('same synthetic waveform', 24000)])
        codec = SimpleNamespace(decode=decode, device='cuda:0', model=SimpleNamespace(decoder=decoder),
                                _karen_original_chunks=original_chunks)
        model = SimpleNamespace(speech_tokenizer=codec, predictor_graph=SimpleNamespace(run=Mock()))
        tokens = {'audio_codes': 'synthetic tokens'}
        model.generate_voice_clone = lambda **kwargs: codec.decode(tokens)
        with patch.dict(sys.modules, {'torch': torch}):
            result = generate(model, object(), SimpleNamespace(language='Spanish', generation={}), 'Hola.', True)
        self.assertEqual(result, ('same synthetic waveform', 24000))
        self.assertEqual(decode.call_count, 2)
        self.assertTrue(all(call.args[0] is tokens for call in decode.call_args_list))
        decoder.to.assert_called_once_with(device='cpu', dtype='float32')
        self.assertIs(decoder.chunked_decode, original_chunks)
        self.assertIs(codec.decode, decode)
        self.assertEqual(codec.device, 'cpu')

    def test_low_free_vram_keeps_decoder_on_cpu(self):
        torch = SimpleNamespace(cuda=SimpleNamespace(mem_get_info=lambda: (800*1024**2, 6*1024**3)))
        codec = Mock()
        with tempfile.TemporaryDirectory() as root:
            configure_decoder(codec, root, torch)
        codec.model.decoder.to.assert_not_called()

    def test_cancelled_request_never_loads_or_generates(self):
        from shared_voice_service import VoiceEngine
        with tempfile.TemporaryDirectory() as root:
            engine = VoiceEngine(root)
            stop = threading.Event()
            stop.set()
            with patch.object(engine, '_load') as load:
                with self.assertRaises(SpeechCancelled):
                    engine.synthesize('Synthetic text', 'test', 'a'*64, cancelled=stop)
            load.assert_not_called()
            self.assertFalse(engine.cache)

    def test_cancellation_restores_graph_and_decoder_methods(self):
        stop = threading.Event()
        predictor = SimpleNamespace(run=Mock())
        codec = SimpleNamespace(decode=Mock(), device='cpu')
        original_run, original_decode = predictor.run, codec.decode
        model = SimpleNamespace(predictor_graph=predictor, speech_tokenizer=codec)

        def generate_wave(**kwargs):
            predictor.run('first frame')
            stop.set()
            predictor.run('cancelled frame')
            self.fail('Generation continued after cancellation')

        model.generate_voice_clone = generate_wave
        with self.assertRaises(SpeechCancelled):
            generate(model, object(), SimpleNamespace(language='Spanish', generation={}), 'Hola.', True, stop)
        original_run.assert_called_once_with('first frame')
        self.assertIs(predictor.run, original_run)
        self.assertIs(codec.decode, original_decode)

    def test_socket_disconnect_cancels_only_its_own_request(self):
        from shared_voice_service import watch_disconnect
        connections = [socket.socketpair(), socket.socketpair()]
        stops = [threading.Event(), threading.Event()]
        finished = threading.Event()
        threads = [threading.Thread(target=watch_disconnect, args=(pair[0], stops[i], finished))
                   for i, pair in enumerate(connections)]
        try:
            for thread in threads:
                thread.start()
            connections[0][1].close()
            self.assertTrue(stops[0].wait(1))
            self.assertFalse(stops[1].is_set())
        finally:
            finished.set()
            for thread in threads:
                thread.join(1)
            for pair in connections:
                for connection in pair:
                    connection.close()

    def test_missing_configuration_keeps_existing_engine(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(backend(root), 'standard')

    def test_only_validated_backend_can_be_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'voice-models').mkdir()
            path = root / 'voice-models/tts-runtime.json'
            for value in [{'schema': 1, 'backend': 'cuda-graphs-fp32'},
                          {'schema': 1, 'backend': 'standard'}]:
                path.write_text(json.dumps(value))
                self.assertEqual(backend(root), value['backend'])
            for value in [{'schema': 2, 'backend': 'cuda-graphs-fp32'},
                          {'schema': 1, 'backend': 'float16'},
                          {'schema': 1, 'backend': 'cuda-graphs-fp32', 'decoder': 'invalid'}, {}]:
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    backend(root)

    def test_acceleration_keeps_prompt_language_and_sampling_without_unsupported_options(self):
        profile = SimpleNamespace(language='Spanish', generation={
            'temperature': .55, 'top_p': .9, 'subtalker_temperature': .55, 'subtalker_top_p': .9,
            'seed': 42, 'unexpected': 'never forwarded'})
        model, prompt = Mock(), object()
        generate(model, prompt, profile, 'Una frase.', True)
        model.generate_voice_clone.assert_called_once_with(text='Una frase.', language='Spanish',
            voice_clone_prompt=prompt, max_new_tokens=96, temperature=.55, top_p=.9)
        model.reset_mock()
        generate(model, prompt, profile, 'x' * 200, False)
        self.assertEqual(model.generate_voice_clone.call_args.kwargs['max_new_tokens'], 384)
        self.assertEqual(model.generate_voice_clone.call_args.kwargs['subtalker_top_p'], .9)

    def test_failed_load_does_not_publish_a_partially_loaded_model(self):
        from shared_voice_service import VoiceEngine
        with tempfile.TemporaryDirectory() as root:
            engine = VoiceEngine(root)
            torch = Mock()
            qwen = SimpleNamespace(Qwen3TTSModel=Mock())
            qwen.Qwen3TTSModel.from_pretrained.side_effect = RuntimeError('Synthetic failed load')
            profile = SimpleNamespace(id='test', reference_sha256='a' * 64, model='test-model')
            with patch.dict(sys.modules, {'torch': torch, 'qwen_tts': qwen}):
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, 'Synthetic failed load'):
                        engine._load(profile)
            self.assertEqual(qwen.Qwen3TTSModel.from_pretrained.call_count, 2)
            self.assertIsNone(engine.model)
            self.assertIsNone(engine.prompt)


if __name__ == '__main__':
    unittest.main()
