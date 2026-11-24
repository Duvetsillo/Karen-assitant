"""Measure a local Ollama chat stream with a fixed, non-private prompt."""

import argparse
import json
from statistics import median
from time import perf_counter
from urllib.parse import urlparse

import requests


PROMPT = 'Responde con una sola palabra: LISTA.'


def ollama_rss():
    """Best-effort RSS snapshot for local Ollama processes, not a VRAM measure."""
    try:
        import psutil
    except ImportError:
        return None
    total = 0
    for process in psutil.process_iter(['name', 'memory_info']):
        try:
            if 'ollama' in (process.info['name'] or '').lower():
                total += process.info['memory_info'].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total or None


def measure(url, model, timeout):
    started = perf_counter()
    rss_before = ollama_rss()
    first_token = None
    final = None
    chunks = 0
    response = requests.post(
        url.rstrip('/') + '/api/chat',
        json={'model': model, 'messages': [{'role': 'user', 'content': PROMPT}],
              'stream': True, 'think': False, 'options': {'num_predict': 16}},
        stream=True, timeout=(2, timeout),
    )
    try:
        response.raise_for_status()
        for line in response.iter_lines():
            if perf_counter() - started > timeout:
                raise TimeoutError('La medición superó su límite total.')
            if not line:
                continue
            event = json.loads(line)
            if event.get('error'):
                raise ValueError('Ollama devolvió un error de generación.')
            content = event.get('message', {}).get('content', '')
            if content:
                chunks += 1
                if first_token is None:
                    first_token = round((perf_counter() - started) * 1000)
            if event.get('done'):
                final = event
                break
        if final is None:
            raise ValueError('Ollama cerró el stream sin finalizar.')
        return {
            'first_token_ms': first_token,
            'total_ms': round((perf_counter() - started) * 1000),
            'text_chunks': chunks,
            'ollama_rss_before_bytes': rss_before,
            'ollama_rss_after_bytes': ollama_rss(),
            'load_ms': round(final['load_duration'] / 1_000_000) if type(final.get('load_duration')) is int else None,
            'eval_ms': round(final['eval_duration'] / 1_000_000) if type(final.get('eval_duration')) is int else None,
        }
    finally:
        response.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:11434')
    parser.add_argument('--model', default='qwen2:0.5b')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()
    target = urlparse(args.url)
    if (target.scheme != 'http' or target.hostname not in {'localhost', '127.0.0.1'} or
            target.username or target.password or target.path not in {'', '/'} or
            target.query or target.fragment or not 1 <= args.runs <= 10 or not 1 <= args.timeout <= 120 or
            not args.model or len(args.model) > 128):
        parser.error('Solo se admite Ollama HTTP local, 1-10 corridas y timeout de 1-120 s.')
    results = []
    for run in range(1, args.runs + 1):
        try:
            result = measure(args.url, args.model, args.timeout)
            results.append(result)
            print(json.dumps({'run': run, **result}))
        except (requests.RequestException, ValueError, TimeoutError) as exc:
            print(json.dumps({'run': run, 'error': type(exc).__name__}))
    if results:
        first = [result['first_token_ms'] for result in results if result['first_token_ms'] is not None]
        print(json.dumps({'successful_runs': len(results),
                          'median_first_token_ms': median(first) if first else None,
                          'median_total_ms': median(result['total_ms'] for result in results)}))
    return 0 if len(results) == args.runs else 1


if __name__ == '__main__':
    raise SystemExit(main())
