import { spawn, type ChildProcess } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { randomBytes } from "node:crypto";
import { writeFileSync } from "node:fs";
import type { Settings } from "../shared/types.js";
import { LocalRecognizer } from './recognizer.js';
import { FastVoice } from './fast-voice.js';
export class NativeVoice {
  private recognizer: LocalRecognizer;
  private controller?: AbortController;
  private child?: ChildProcess;
  private synthesisEpoch = 0;
  private preparing?: Promise<void>;
  private fast: FastVoice;
  constructor(
    private defaultRoot: string,
    private settings: () => Settings,
    private worker?: string,
    private serviceWorker?: string,
  ) {
    this.recognizer = new LocalRecognizer(worker);
    this.fast = new FastVoice(join(serviceWorker ? dirname(serviceWorker) : join(this.defaultRoot, 'desktop-pet/python'), 'fast_voice.py'));
  }
  private get root() { return resolve(this.settings().voiceRoot || this.defaultRoot); }
  cancelTranscription() { this.recognizer.cancelActive(); }
  dispose() {this.cancel();this.fast.close();this.recognizer.cancel();}
  cancel() {
    this.recognizer.cancelActive();
    this.cancelSynthesis();
  }
  cancelSynthesis() {
    this.synthesisEpoch++;
    this.fast.cancelActive();
    this.controller?.abort();
    this.child?.kill();
    this.controller = undefined;
    this.child = undefined;
  }
  private profile() {
    try {
      const value = JSON.parse(readFileSync(join(this.root, "voice-models", "active-voice.json"), "utf8")) as { id?: string; reference_sha256?: string };
      if (!value.id || !/^[a-z0-9-]{1,64}$/.test(value.id) || !value.reference_sha256 || !/^[a-f0-9]{64}$/.test(value.reference_sha256)) throw new Error();
      return { profileId: value.id, referenceSha256: value.reference_sha256 };
    } catch {
      throw new Error("Configura la voz original compartida en la carpeta de recursos de voz.");
    }
  }
  private token(create: boolean) {
    const file = join(this.root, "voice-models", ".expressive-token");
    if (create && !existsSync(file)) {
      try { writeFileSync(file, randomBytes(32).toString("base64url"), { flag: "wx", mode: 0o600 }); }
      catch (error) { if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error; }
    }
    const token = readFileSync(file, "utf8").trim();
    if (!/^[\w-]{32,256}$/.test(token)) throw new Error("Credencial de voz local inválida.");
    return token;
  }
  private async speechRequest(path: "/health" | "/speech" | "/prepare", token: string, signal: AbortSignal, body?: object) {
    const response = await fetch(`http://127.0.0.1:18790${path}`, {
      method: body ? "POST" : "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.any([signal, AbortSignal.timeout(path === "/health" ? 2000 : 600000)]),
    });
    if (!response.ok)
      throw new Error(`El servicio de voz local respondió ${response.status}.`);
    return response;
  }
  private async sharedService(signal: AbortSignal, start: boolean) {
    const profile = this.profile();
    const token = this.token(start);
    const check = async () => {
      const response = await this.speechRequest("/health", token, signal);
      const value = await response.json() as { protocol?: number; profileId?: string; referenceSha256?: string; phase?: string; capabilities?: string[] };
      if (value.protocol !== 2 || value.profileId !== profile.profileId || value.referenceSha256 !== profile.referenceSha256)
        throw new Error("El servicio tiene otro perfil. No se cambiará la voz de Karen.");
      return value;
    };
    try { const value = await check(); return { token, profile, phase:value.phase, capabilities:value.capabilities }; }
    catch (error) {
      signal.throwIfAborted();
      // Only an unavailable transport can start a service; never replace a
      // reachable service that rejected credentials or the pinned identity.
      if (!start || !(error instanceof TypeError)) throw error;
    }
    const python = join(this.root, "expressive-runtime", "Scripts", "python.exe");
    const script = this.serviceWorker || join(this.root, "expressive_service.py");
    if (!existsSync(python) || !existsSync(script)) throw new Error("Falta instalar el motor de voz original y sus modelos locales.");
    const child = spawn(python, [script, this.root], { cwd: this.root, windowsHide: true, detached: true, stdio: "ignore", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } });
    let launchError = false;
    child.on("error", () => { launchError = true; });
    child.unref();
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      signal.throwIfAborted();
      if (launchError) throw new Error("No se pudo iniciar el servicio de voz original.");
      try { const value = await check(); return { token, profile, phase:value.phase, capabilities:value.capabilities }; }
      catch (error) { signal.throwIfAborted(); if (!(error instanceof TypeError)) throw error; }
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    throw new Error("El servicio de voz original no pudo iniciar.");
  }
  prepare() {
    const settings = this.settings();
    if (!settings.voiceEnabled || settings.ttsEngine !== 'local' || settings.lowPower) return Promise.resolve();
    if (!this.preparing) {
      this.preparing = (async () => {
        const signal = AbortSignal.timeout(120000);
        const {token,profile,capabilities} = await this.sharedService(signal, true);
        if (capabilities?.includes('prepare')) {
          await this.speechRequest('/prepare', token, signal, profile);
        }
      })().finally(() => {this.preparing = undefined;});
    }
    return this.preparing;
  }
  async health() {
    const stt =
      existsSync(join(this.root, "voice-runtime", "Scripts", "python.exe")) &&
      existsSync(
        join(this.root, "voice-models", "faster-whisper-small", "model.bin"),
      );
    if (this.settings().ttsEngine === 'fast') {
      const found = ['voice-runtime/Scripts/python.exe','voice-models/kokoro-v1.0.onnx','voice-models/voices-v1.0.bin'].every(file=>existsSync(join(this.root,file)));
      return `Kokoro rápido: ${found ? 'archivos encontrados; se verifica al reproducir' : 'faltan sus recursos locales'}. Usa otro timbre fijo, distinto de la voz original. STT: ${stt ? 'archivos encontrados' : 'sin configurar'}.`;
    }
    if (this.settings().ttsEngine === 'edge') {
      const found = existsSync(join(this.root, 'voice-runtime/Scripts/python.exe')) && existsSync(join(this.serviceWorker ? dirname(this.serviceWorker) : join(this.defaultRoot, 'desktop-pet/python'), 'edge_voice.py'));
      return `Dalia neural: ${found ? 'runtime encontrado; internet y reproducción se verifican al hablar' : 'falta el runtime de voz'}. STT: ${stt ? 'archivos encontrados' : 'sin configurar'}.`;
    }
    let local = "Voz original sin configurar; elige su carpeta de recursos en Voz";
    try {
      const { profile, phase } = await this.sharedService(new AbortController().signal, false);
      const state = phase === "loading" ? "; cargando modelo" : phase === "generating" ? "; generando audio, puede tardar" : phase === "error" ? "; la última síntesis falló" : "";
      local = `Voz compartida ${profile.profileId}, autenticada y con referencia verificada${state}`;
    } catch (error) {
      try {
        const profile = this.profile();
        const installed = existsSync(join(this.root, "expressive-runtime", "Scripts", "python.exe"));
        const tokenMissing = !existsSync(join(this.root, "voice-models", ".expressive-token"));
        if (!installed) local = `Perfil ${profile.profileId} configurado; falta instalar el motor local`;
        else if (error instanceof TypeError || tokenMissing) local = `Perfil ${profile.profileId} configurado; el servicio se inicia al hablar`;
        else local = error instanceof Error ? error.message : "No se pudo verificar la voz original";
      } catch {}
    }
    return `${local}. STT local: ${stt ? "archivos encontrados; ejecutar una captura para verificar inferencia" : "elige la carpeta con voice-runtime y el modelo de reconocimiento en Voz"}. TTS de Windows: se verifica al reproducir si eliges ese motor.`;
  }
  private run(
    command: string,
    args: string[],
    input: string,
    timeout: number,
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const child = spawn(command, args, {
        // Windows TTS is independent of optional local model resources.
        cwd: existsSync(this.root) ? this.root : dirname(process.execPath),
        windowsHide: true,
        stdio: ["pipe", "pipe", "pipe"],
      });
      this.child = child;
      let output = "";
      let done = false;
      const end = (error?: string) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (this.child === child) this.child = undefined;
        if (error) reject(new Error(error));
        else resolve(output.trim());
      };
      const timer = setTimeout(() => {
        child.kill();
        end("El motor de voz superó el tiempo de espera.");
      }, timeout);
      child.on("error", (error: NodeJS.ErrnoException) => end(`No se pudo iniciar el motor de voz local (${error.code || 'SPAWN'}). Revisa su carpeta de recursos.`));
      child.stdout?.on("data", (data: Buffer) => {
        output += data.toString();
        if (output.length > 32_000_000) {
          child.kill();
          end("Respuesta de voz demasiado grande.");
        }
      });
      child.stderr?.resume();
      child.on("exit", (code) =>
        end(code === 0 ? undefined : "El motor de voz se detuvo."),
      );
      child.stdin?.on("error", () => {});
      child.stdin?.end(input);
    });
  }
  async synthesize(text: string): Promise<ArrayBuffer> {
    this.cancel();
    if (typeof text !== "string" || !text.trim() || text.length > 4096)
      throw new Error("Texto de voz inválido (máximo 4096 caracteres).");
    if (this.settings().ttsEngine === 'edge') {
      const python = join(this.root, 'voice-runtime/Scripts/python.exe');
      const worker = join(this.serviceWorker ? dirname(this.serviceWorker) : join(this.defaultRoot, 'desktop-pet/python'), 'edge_voice.py');
      if (!existsSync(python) || !existsSync(worker)) throw new Error('Falta instalar Edge TTS en los recursos de voz.');
      const epoch = this.synthesisEpoch;
      const timeout = Math.min(90000, Math.max(30000, text.length * 20));
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const encoded = await this.run(python, [worker], JSON.stringify({text}), timeout);
          if (epoch !== this.synthesisEpoch) throw new Error('Síntesis cancelada.');
          const bytes = Buffer.from(encoded, 'base64');
          if (bytes.length < 100 || bytes.length > 24_000_000 ||
            !(bytes.subarray(0, 3).toString() === 'ID3' || (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)))
            throw new Error('La voz neural devolvió audio inválido.');
          return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
        } catch (error) {
          if (epoch !== this.synthesisEpoch) throw new Error('Síntesis cancelada.');
          if (attempt === 1) {
            const timedOut = error instanceof Error && error.message.includes('tiempo de espera');
            throw new Error(timedOut
              ? 'La voz neural tardó demasiado tras dos intentos. Revisa la conexión; el texto sigue disponible.'
              : 'La voz neural falló tras dos intentos. Revisa la conexión o el motor de voz; el texto sigue disponible.');
          }
          await new Promise(resolve => setTimeout(resolve, 400));
          if (epoch !== this.synthesisEpoch) throw new Error('Síntesis cancelada.');
        }
      }
      throw new Error('La voz neural no respondió.');
    }
    if (this.settings().ttsEngine === 'fast') return this.fast.synthesize(this.root,text,this.settings().voiceStyle);
    if (this.settings().ttsEngine === "local") {
      const controller = new AbortController();
      this.controller = controller;
      try {
        const { token, profile } = await this.sharedService(controller.signal, true);
        const style = this.settings().voiceStyle;
        const response = await this.speechRequest("/speech", token, controller.signal, { text, style, ...profile });
        if (response.headers.get("X-Karen-Voice-Id") !== profile.profileId || response.headers.get("X-Karen-Voice-Sha256") !== profile.referenceSha256)
          throw new Error("El audio recibido no pertenece a la voz fija de Karen.");
        if (style !== 'neutral' && response.headers.get('X-Karen-Voice-Style') !== style)
          throw new Error('Actualiza el servicio de voz compartida para usar estilos.');
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > 24_000_000 || Buffer.from(bytes).subarray(0, 4).toString() !== "RIFF") throw new Error("El servicio devolvió audio inválido.");
        return bytes;
      } finally { if (this.controller === controller) this.controller = undefined; }
    }
    const script = `$ErrorActionPreference='Stop'; [Console]::InputEncoding=[System.Text.Encoding]::UTF8; Add-Type -AssemblyName System.Speech; $r=[Console]::In.ReadToEnd()|ConvertFrom-Json; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $v=$s.GetInstalledVoices()|Where-Object {$_.VoiceInfo.Culture.Name -like 'es-*'}|Select-Object -First 1; if($v){$s.SelectVoice($v.VoiceInfo.Name)}; $m=New-Object System.IO.MemoryStream; $s.SetOutputToWaveStream($m); $s.Speak([string]$r.text); $s.Dispose(); [Console]::Out.Write([Convert]::ToBase64String($m.ToArray())); $m.Dispose()`;
    const encoded = await this.run(
      "powershell.exe",
      [
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        Buffer.from(script, "utf16le").toString("base64"),
      ],
      JSON.stringify({ text }),
      120000,
    );
    const data = Buffer.from(encoded, "base64");
    return data.buffer.slice(
      data.byteOffset,
      data.byteOffset + data.byteLength,
    ) as ArrayBuffer;
  }
  async transcribe(pcm: ArrayBuffer): Promise<string> {
    return this.recognizer.transcribe(this.root, pcm);
  }
}
