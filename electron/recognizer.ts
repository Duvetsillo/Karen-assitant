import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

/** One offline CPU model stays warm between utterances; no recordings or text logs. */
export class LocalRecognizer {
  private child?: ChildProcessWithoutNullStreams;
  private root = '';
  private output = '';
  private pending?: { resolve(text: string): void; reject(error: Error): void };
  private timer?: ReturnType<typeof setTimeout>;
  constructor(private worker?: string) {}
  cancelActive() { if (this.pending) this.cancel(); }
  cancel() {
    const child = this.child;
    this.child = undefined;
    clearTimeout(this.timer);
    this.pending?.reject(new Error('Reconocimiento local cancelado.'));
    this.pending = undefined;
    this.output = '';
    child?.kill();
  }
  transcribe(root: string, pcm: ArrayBuffer): Promise<string> {
    if (!(pcm instanceof ArrayBuffer) || pcm.byteLength < 3200 || pcm.byteLength > 1_920_000)
      return Promise.reject(new Error('Audio inválido. Graba entre 0,1 y 60 segundos.'));
    if (this.pending) return Promise.reject(new Error('Ya hay una transcripción local en curso.'));
    if (this.root !== root) this.cancel();
    this.root = root;
    clearTimeout(this.timer);
    const python = join(root, 'voice-runtime', 'Scripts', 'python.exe');
    const worker = this.worker || join(root, 'desktop-pet', 'python', 'recognize.py');
    const model = join(root, 'voice-models', 'faster-whisper-small', 'model.bin');
    const missing = [
      !existsSync(python) && 'voice-runtime/Scripts/python.exe',
      !existsSync(model) && 'voice-models/faster-whisper-small/model.bin',
      !existsSync(worker) && 'worker recognize.py de la instalación',
    ].filter(Boolean);
    if (missing.length)
      return Promise.reject(new Error(`Reconocimiento local incompleto en ${root}: falta ${missing.join(', ')}. Revisa Voz → carpeta de recursos; si falta el worker, reinstala Karen.`));
    return new Promise((resolve, reject) => {
      this.pending = { resolve, reject };
      if (!this.child) {
        const child = spawn(python, [worker, root, '--persistent'], {
          cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
        });
        this.child = child;
        const fail = (message: string) => {
          if (this.child !== child) return;
          this.pending?.reject(new Error(message));
          this.pending = undefined;
          this.cancel();
        };
        child.on('error', (error: NodeJS.ErrnoException) => fail(`No se pudo iniciar el reconocimiento local (${error.code || 'SPAWN'}). Revisa la carpeta de recursos de voz.`));
        child.on('exit', () => fail('El reconocimiento local se cerró. Revisa su instalación.'));
        child.stderr.resume();
        child.stdin.on('error', () => fail('No se pudo enviar audio al reconocimiento local.'));
        child.stdout.on('data', (data: Buffer) => {
          if (this.child !== child) return;
          this.output += data.toString();
          if (this.output.length > 100_000) { fail('Respuesta de reconocimiento inválida.'); return; }
          const end = this.output.indexOf('\n');
          if (end < 0) return;
          const line = this.output.slice(0, end);
          this.output = this.output.slice(end + 1);
          try {
            const result = JSON.parse(line) as { text?: unknown; error?: unknown };
            if (typeof result.text !== 'string') {
              const reasons: Record<string, string> = {
                dependencies: 'Faltan dependencias del reconocimiento local en voice-runtime. Reinstala los recursos de voz.',
                model: 'No se pudo cargar el modelo de voz en voice-models/faster-whisper-small. Revisa Voz → carpeta de recursos.',
                audio: 'El fragmento de audio no es válido. Revisa el micrófono en Voz.',
                recognition: 'El reconocimiento local falló al procesar el audio. Revisa Voz y reintenta.',
                request: 'El reconocimiento local recibió una petición inválida.',
              };
              const message = typeof result.error === 'string' ? reasons[result.error] : undefined;
              fail(message || 'El reconocimiento local no pudo transcribir. Revisa el modelo y sus dependencias.');
              return;
            }
            const pending = this.pending;
            this.pending = undefined;
            clearTimeout(this.timer);
            this.timer = setTimeout(() => this.cancel(), 120_000);
            this.timer.unref();
            pending?.resolve(result.text.trim().slice(0, 16000));
          } catch { fail('Respuesta inválida del reconocimiento local. Revisa los recursos de voz.'); }
        });
      }
      this.timer = setTimeout(() => this.cancel(), 180_000);
      this.child.stdin.write(JSON.stringify({ audio: Buffer.from(pcm).toString('base64') }) + '\n');
    });
  }
}
