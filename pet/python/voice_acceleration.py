"""Opt-in acceleration of the pinned Qwen model, without changing its identity.

The overlay is deliberately separate from expressive-runtime: Qwen 0.1.1 and
Transformers 4.57 are incompatible with newer faster-qwen3-tts releases.
"""
import importlib.metadata
import json
from pathlib import Path
import sys
import time


class SpeechCancelled(Exception):
    """A client's own disconnected utterance; never a model failure."""


def check_cancelled(cancelled):
    if cancelled is not None and cancelled.is_set():
        raise SpeechCancelled()


def backend(root):
    path = Path(root) / 'voice-models/tts-runtime.json'
    if not path.exists():
        return 'standard'
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or data.get('schema') != 1 or data.get('backend') not in {'standard', 'cuda-graphs-fp32'}:
        raise ValueError('Configuración de aceleración de voz inválida')
    if data.get('decoder', 'auto') not in {'auto', 'cpu'}:
        raise ValueError('Configuración del decodificador de voz inválida')
    return data['backend']


def accelerate(model, root, generation):
    overlay = Path(root) / 'tts-fast-runtime'
    packages = overlay / ('Lib/site-packages' if sys.platform == 'win32' else
                          f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
    if not (packages / 'faster_qwen3_tts').is_dir():
        raise RuntimeError('Falta el entorno aislado de aceleración de voz')
    if str(packages) not in sys.path:
        sys.path.insert(0, str(packages))
    if importlib.metadata.version('faster-qwen3-tts') != '0.2.6':
        raise RuntimeError('Versión de aceleración de voz no validada')
    import torch
    from faster_qwen3_tts import FasterQwen3TTS
    from faster_qwen3_tts.predictor_graph import PredictorGraph
    from faster_qwen3_tts.talker_graph import TalkerGraph
    talker = model.model.talker
    config = model.model.config.talker_config
    predictor = PredictorGraph(talker.code_predictor, talker.code_predictor.model.config,
        config.hidden_size, device='cuda:0', dtype=torch.float32,
        temperature=float(generation.get('subtalker_temperature', .55)),
        # The 0.2.6 graphed predictor's nucleus sampling produced invalid audio
        # on the validated Turing runtime. Keep top-k=50 without nucleus pruning;
        # the main talker still uses the profile's top_p and the same embedding.
        top_p=1.0)
    graph = TalkerGraph(talker.model, config, device='cuda:0', dtype=torch.float32, max_seq_len=512)
    fast = FasterQwen3TTS(model, predictor, graph, device='cuda:0', dtype=torch.float32, max_seq_len=512)
    # Capturing once during prepare avoids repeating graph capture in each reply.
    fast._warmup(100)
    configure_decoder(fast.speech_tokenizer, root, torch)
    return fast


def configure_decoder(codec, root, torch):
    """Use only the FP32 decoder on CUDA when there is room; encoder stays on CPU."""
    path = Path(root) / 'voice-models/tts-runtime.json'
    policy = json.loads(path.read_text(encoding='utf-8-sig')).get('decoder', 'auto') if path.exists() else 'auto'
    if policy == 'cpu' or torch.cuda.mem_get_info()[0] < 950 * 1024**2:
        return
    decoder = codec.model.decoder
    original_chunks = decoder.chunked_decode

    def bounded_chunks(codes):
        # Bound activations for long responses on 6 GB GPUs. Keep the model's
        # supported 25-frame context across decoder chunks.
        return original_chunks(codes, chunk_size=24, left_context_size=25)

    try:
        decoder.to(device='cuda:0', dtype=torch.float32)
        decoder.chunked_decode = bounded_chunks
        codec.device = torch.device('cuda:0')
        codec._karen_original_chunks = original_chunks
    except torch.cuda.OutOfMemoryError:
        decoder.to(device='cpu', dtype=torch.float32)
        torch.cuda.empty_cache()


def generate(model, prompt, profile, text, accelerated, cancelled=None):
    check_cancelled(cancelled)
    options = {k: v for k, v in profile.generation.items() if k in {
        'temperature', 'top_p', 'subtalker_temperature', 'subtalker_top_p'}}
    if accelerated:
        options = {k: v for k, v in options.items() if not k.startswith('subtalker_')}
    if not accelerated:
        if cancelled is not None:
            from transformers import StoppingCriteriaList

            def stop_on_disconnect(*args, **kwargs):
                check_cancelled(cancelled)
                return False

            options['stopping_criteria'] = StoppingCriteriaList([stop_on_disconnect])
        return model.generate_voice_clone(text=text, language=profile.language,
            voice_clone_prompt=prompt, max_new_tokens=min(384, max(96, len(text) * 2)), **options)
    codec = model.speech_tokenizer
    decode = codec.decode
    decoder_seconds = 0.0
    predictor_run = model.predictor_graph.run

    def cancellable_predictor(*args, **kwargs):
        check_cancelled(cancelled)
        return predictor_run(*args, **kwargs)

    def measured_decode(*args, **kwargs):
        nonlocal decoder_seconds
        check_cancelled(cancelled)
        started = time.perf_counter()
        try:
            try:
                return decode(*args, **kwargs)
            except RuntimeError as error:
                import torch
                if not isinstance(error, torch.cuda.OutOfMemoryError):
                    raise
                if str(codec.device) == 'cpu':
                    raise
                # Retry the same codec tokens once on CPU, with the same voice.
                codec.model.decoder.to(device='cpu', dtype=torch.float32)
                codec.device = torch.device('cpu')
                codec.model.decoder.chunked_decode = codec._karen_original_chunks
                torch.cuda.empty_cache()
                return decode(*args, **kwargs)
        finally:
            decoder_seconds += time.perf_counter() - started

    started = time.perf_counter()
    codec.decode = measured_decode
    model.predictor_graph.run = cancellable_predictor
    try:
        return model.generate_voice_clone(text=text, language=profile.language,
            voice_clone_prompt=prompt, max_new_tokens=min(384, max(96, len(text) * 2)), **options)
    finally:
        codec.decode = decode
        model.predictor_graph.run = predictor_run
        model.last_timings = {'decoderSeconds': decoder_seconds,
                              'tokenGenerationSeconds': time.perf_counter() - started - decoder_seconds,
                              'decoderDevice': str(codec.device)}
