import { describe, expect, it } from 'vitest';
import { assertLoopbackGateway, isLocalInferenceModel } from '../shared/local-inference';

describe('Core 2 local inference policy', () => {
  it('permits only local Ollama model identifiers, excluding Ollama Cloud proxies', () => {
    expect(isLocalInferenceModel('ollama/qwen3.5:4b')).toBe(true);
    for (const id of ['openai/gpt-test', 'anthropic/test', 'ollama/beam:cloud', 'ollama/gemma4:31b-cloud'])
      expect(isLocalInferenceModel(id)).toBe(false);
  });
  it('requires loopback gateway without URL credentials', () => {
    expect(() => assertLoopbackGateway('ws://127.0.0.1:18789')).not.toThrow();
    for (const value of ['ws://192.168.1.2:18789', 'wss://example.com', 'ws://secret@localhost:18789'])
      expect(() => assertLoopbackGateway(value)).toThrow();
  });
});
