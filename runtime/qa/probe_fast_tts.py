"""Hardware experiment: original pinned Qwen voice with CUDA-graph inference.

Writes synthetic audio only. Never plays audio, captures a microphone, downloads
models or changes the active voice profile/service configuration.
"""
import argparse
import io
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'desktop-pet' / 'python'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dtype', choices=['float32', 'float16'], default='float32')
    parser.add_argument('--mode', choices=['stream', 'complete'], default='stream')
    parser.add_argument('--codec-device', choices=['cpu', 'cuda'], default='cpu')
    args = parser.parse_args()
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel
    from faster_qwen3_tts import FasterQwen3TTS
    from faster_qwen3_tts.predictor_graph import PredictorGraph
    from faster_qwen3_tts.talker_graph import TalkerGraph
    from voice_profile import load_profile
    profile = load_profile(ROOT)
    dtype = getattr(torch, args.dtype)
    torch.set_num_threads(4)
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(str(profile.model), device_map='cpu',
        dtype=dtype, attn_implementation='sdpa', local_files_only=True)
    model.model.talker.to('cuda:0')
    model.model.speaker_encoder.to('cuda:0')
    model.device = torch.device('cuda:0')
    # The existing Turing-compatible decoder remains FP32 on CPU.
    model.model.speech_tokenizer.model.to(device='cpu', dtype=torch.float32)
    model.model.speech_tokenizer.device = torch.device('cpu')
    talker = model.model.talker
    predictor = PredictorGraph(talker.code_predictor, talker.code_predictor.model.config,
        model.model.config.talker_config.hidden_size, device='cuda:0', dtype=dtype,
        do_sample=True, top_k=50, temperature=0.55)
    graph = TalkerGraph(talker.model, model.model.config.talker_config,
                       device='cuda:0', dtype=dtype, max_seq_len=512)
    fast = FasterQwen3TTS(model, predictor, graph, device='cuda:0', dtype=dtype, max_seq_len=512)
    prompt = model.create_voice_clone_prompt(ref_audio=str(profile.reference),
        ref_text=profile.reference_text, x_vector_only_mode=True)
    if args.codec_device == 'cuda':
        # Only the decoder is needed after extracting the pinned speaker vector.
        model.model.speech_tokenizer.model.decoder.to('cuda:0')
        model.model.speech_tokenizer.device = torch.device('cuda:0')
    fast._warmup(100)
    loaded = time.perf_counter() - started
    results = []
    for index, text in enumerate(['Hola. Soy Karen y estoy lista para ayudarte.',
                                 'Hola. Soy Karen y estoy lista para ayudarte.',
                                 'Podemos conversar con calma y revisar tus pendientes.']):
        chunks, first, start = [], None, time.perf_counter()
        torch.manual_seed(42)
        with torch.inference_mode():
            if args.mode == 'complete':
                waves, rate = fast.generate_voice_clone(text=text, language='Spanish',
                    voice_clone_prompt=prompt, max_new_tokens=160, temperature=0.55, top_p=0.9)
                chunks.extend(waves)
                first = time.perf_counter() - start
            else:
              for audio, rate, timing in fast.generate_voice_clone_streaming(text=text,
                language='Spanish', voice_clone_prompt=prompt, max_new_tokens=160,
                temperature=0.55, top_p=0.9, chunk_size=8):
                if first is None: first = time.perf_counter() - start
                if not np.isfinite(audio).all(): raise ValueError('Non-finite audio')
                chunks.append(np.asarray(audio, dtype=np.float32))
        elapsed = time.perf_counter() - start
        audio = np.concatenate(chunks)
        output = ROOT / 'qa' / f'tts-graphs-{args.dtype}-{args.mode}-{args.codec_device}-{index}.wav'
        sf.write(output, audio, rate)
        item = {'text': text, 'dtype': args.dtype, 'codec_device': args.codec_device, 'load_seconds': loaded,
            'first_audio_seconds': first, 'total_seconds': elapsed,
            'audio_seconds': len(audio)/rate, 'rtf': elapsed/(len(audio)/rate),
            'rms': float(np.sqrt(np.mean(audio**2))), 'peak': float(np.max(np.abs(audio))),
            'cuda_allocated_mb': torch.cuda.memory_allocated()/1024**2,
            'cuda_peak_mb': torch.cuda.max_memory_allocated()/1024**2, 'sample': str(output)}
        results.append(item)
        print(json.dumps(item), flush=True)
    (ROOT/'qa'/f'tts-graphs-{args.dtype}-{args.mode}-{args.codec_device}-20261031.json').write_text(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
