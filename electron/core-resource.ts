import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { randomUUID } from 'node:crypto';

/** OS lock shared with classic. No polling, TTL, audio, or model subprocess. */
export class MicrophoneArbiter {
  private child?: ChildProcessWithoutNullStreams;
  private opening?: Promise<void>;
  private claims = new Map<string, number>();
  private owner?: number;
  private epoch = 0;
  private closing?: Promise<void>;

  constructor(private python: () => string, private worker: string,
    private lost: () => void) {}

  async claim(owner: number): Promise<string> {
    if (this.owner !== undefined && this.owner !== owner)
      throw new Error('Otra ventana de Karen usa el micrófono.');
    this.owner = owner;
    const epoch = this.epoch;
    try {
      if (!this.child && !this.opening) {
        const opening = this.acquire();
        this.opening = opening;
        void opening.finally(() => {
          if (this.opening === opening) this.opening = undefined;
        }).catch(() => {});
      }
      await this.opening;
      if (epoch !== this.epoch || !this.child)
        throw new Error('La solicitud de micrófono fue cancelada.');
      const token = randomUUID();
      this.claims.set(token, owner);
      return token;
    } catch (error) {
      if (epoch === this.epoch && !this.claims.size) this.owner = undefined;
      throw error;
    }
  }

  private async acquire(): Promise<void> {
    const epoch = this.epoch;
    await this.closing;
    if (epoch !== this.epoch) throw new Error('Solicitud de micrófono cancelada.');
    return new Promise((resolve, reject) => {
      const child = spawn(this.python(), ['-u', this.worker], {
        windowsHide: true, stdio: 'pipe', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
      });
      this.child = child;
      let settled = false, output = '';
      const timer = setTimeout(() => fail('No responde el árbitro del micrófono.'), 5000);
      const fail = (message: string) => {
        clearTimeout(timer);
        if (this.child === child) {
          this.child = undefined;
          if (settled) { this.claims.clear(); this.owner = undefined; this.epoch++; this.lost(); }
        }
        child.kill();
        if (!settled) { settled = true; reject(new Error(message)); }
      };
      child.stderr.resume();
      child.stdin.on('error', () => fail('Se cerró el árbitro del micrófono.'));
      child.on('error', () => fail('No se pudo iniciar el árbitro del micrófono. Revisa Python y los recursos de voz.'));
      child.on('exit', () => fail('Se cerró el árbitro del micrófono.'));
      child.stdout.on('data', (data: Buffer) => {
        if (settled) return;
        output += data.toString();
        if (output.length > 128) return fail('Respuesta del árbitro inválida.');
        if (!output.includes('\n')) return;
        if (output.trim() !== 'ACQUIRED') return fail(
          output.trim() === 'BUSY' ? 'Otra interfaz de Karen usa el micrófono.' : 'No se pudo bloquear el micrófono.');
        settled = true;
        clearTimeout(timer);
        resolve();
      });
    });
  }

  release(owner: number, token: string): void {
    if (this.claims.get(token) !== owner) return;
    this.claims.delete(token);
    if (!this.claims.size) this.close();
  }

  releaseOwner(owner: number): void {
    if (this.owner === owner) this.close();
  }

  close(): void {
    this.epoch++;
    this.owner = undefined;
    this.claims.clear();
    const child = this.child;
    this.child = undefined;
    this.opening = undefined;
    // EOF releases the Python OS lock. kill also covers a stuck startup.
    if (child) {
      this.closing = new Promise(resolve => {
        if (!child.pid || child.exitCode !== null || child.signalCode !== null) resolve();
        else child.once('close', () => resolve());
      });
      child.stdin.end();
      child.kill();
    }
  }
}
