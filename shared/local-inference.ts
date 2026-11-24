/** Karen Core 2 privacy boundary. The gateway and reasoning provider stay on this PC. */
export function isLocalInferenceModel(id: string): boolean {
  return id.startsWith('ollama/') && !/(^|[-:/])cloud($|[-:/])/i.test(id);
}

export function assertLoopbackGateway(value: string): void {
  const parsed = new URL(value);
  if (parsed.protocol !== 'ws:' || !['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname)
      || parsed.username || parsed.password) {
    throw new Error('Core 2 requiere OpenClaw en loopback; no usa inferencia en otros equipos.');
  }
}
