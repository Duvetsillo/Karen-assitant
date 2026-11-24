import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { join } from "node:path";

export class LoopbackRecorder {
  private child?: ChildProcessWithoutNullStreams;
  private epoch = 0;
  constructor(private root: () => string, private worker: string, private energy: (value: number) => void) {}
  async start(onAudio: (pcm: ArrayBuffer) => void, onError: (message: string) => void) {
    this.cancel();
    const epoch = this.epoch;
    const child = spawn(join(this.root(), "voice-runtime/Scripts/python.exe"), [this.worker], { windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
    this.child = child;
    let pending = "", pcm: Buffer | undefined, ready = false, failed = false;
    await new Promise<void>((resolve, reject) => {
      const fail = () => {
        if (failed || epoch !== this.epoch) return;
        failed = true;
        const message = "No se pudo capturar la salida de Windows. Revisa el dispositivo y PyAudioWPatch en tu runtime de voz.";
        if (!ready) reject(new Error(message)); else onError(message);
        child.kill();
      };
      const timer = setTimeout(fail, 15000);
      const hardLimit = setTimeout(fail, 75000);
      child.on("error", fail);
      child.stderr.on("data", () => {});
      child.stdin.on("error", () => {});
      child.stdout.on("data", (chunk: Buffer) => {
        if (epoch !== this.epoch) return;
        pending += chunk.toString("utf8");
        if (pending.length > 4_000_000) { fail(); return; }
        let end: number;
        while ((end = pending.indexOf("\n")) >= 0) {
          const line = pending.slice(0, end); pending = pending.slice(end + 1);
          try {
            const event = JSON.parse(line);
            if (event.ready) { ready = true; clearTimeout(timer); resolve(); }
            if (typeof event.energy === "number" && Number.isFinite(event.energy)) this.energy(Math.max(0, Math.min(1, event.energy)));
            if (typeof event.audio === "string") pcm = Buffer.from(event.audio, "base64");
            if (event.error) fail();
          } catch { fail(); }
        }
      });
      child.on("close", code => {
        clearTimeout(timer);
        clearTimeout(hardLimit);
        if (epoch !== this.epoch) { if (!ready) resolve(); return; }
        this.child = undefined;
        this.energy(0);
        if (code !== 0 || !pcm || pcm.length < 3200 || pcm.length > 1_920_000) { fail(); return; }
        onAudio(pcm.buffer.slice(pcm.byteOffset, pcm.byteOffset + pcm.byteLength) as ArrayBuffer);
      });
    });
  }
  finish() { this.child?.stdin.end("stop\n"); }
  cancel() { this.epoch++; this.child?.kill(); this.child = undefined; this.energy(0); }
}
