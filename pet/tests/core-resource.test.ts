import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { MicrophoneArbiter } from '../electron/core-resource';

let directory: string;
const arbiters: MicrophoneArbiter[] = [];
beforeEach(() => {
  directory = mkdtempSync(join(tmpdir(), 'karen-resource-'));
  vi.stubEnv('KAREN_RESOURCE_DIR', directory);
});
afterEach(async () => {
  for (const arbiter of arbiters.splice(0)) arbiter.close();
  vi.unstubAllEnvs();
  // Windows process termination closes its file handles asynchronously.
  await vi.waitFor(() => rmSync(directory, { recursive: true, force: true }), { timeout: 2000 });
});
function arbiter() {
  const value = new MicrophoneArbiter(() => process.env.KAREN_TEST_PYTHON || 'python',
    resolve('python/core_resource.py'), vi.fn());
  arbiters.push(value);
  return value;
}

describe('shared microphone OS ownership with real Python workers', () => {
  it('excludes another process and releases before granting its next claim', async () => {
    const classic = arbiter(), pet = arbiter();
    const token = await classic.claim(1);
    await expect(pet.claim(2)).rejects.toThrow('Otra interfaz');
    classic.release(999, token); // A different renderer cannot release ownership.
    await expect(pet.claim(2)).rejects.toThrow('Otra interfaz');
    classic.release(1, token);
    // classic waits for its exiting worker before a new hardware claim.
    const next = await classic.claim(1);
    expect(next).not.toBe(token);
    classic.release(1, next);
  });

  it('retains ownership until all claims from its renderer have closed', async () => {
    const value = arbiter(), other = arbiter();
    const [first, second] = await Promise.all([value.claim(1), value.claim(1)]);
    await expect(value.claim(2)).rejects.toThrow('Otra ventana');
    value.release(1, first);
    await expect(other.claim(2)).rejects.toThrow('Otra interfaz');
    value.releaseOwner(1);
    const replacement = await value.claim(2);
    expect(replacement).not.toBe(second);
    value.release(2, replacement);
  });

  it('cancels a pending claim when the renderer closes', async () => {
    const value = arbiter();
    const pending = value.claim(1);
    value.releaseOwner(1);
    await expect(pending).rejects.toThrow('cancelada');
    const token = await value.claim(2);
    value.release(2, token);
  });
});
