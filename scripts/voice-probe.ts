import { NativeVoice } from "../electron/voice";
import { defaults } from "../shared/settings";
import { writeFileSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve, join } from "node:path";
const root = resolve("..");
const voice = new NativeVoice(root, () => defaults);
mkdirSync("qa", { recursive: true });
const wav = await voice.synthesize(
  "Hola, soy Karen. Estoy aquí para ayudarte.",
);
writeFileSync("qa/voice-windows.wav", Buffer.from(wav));
const converted = spawnSync(
  join(root, "ffmpeg.exe"),
  [
    "-hide_banner",
    "-loglevel",
    "error",
    "-i",
    "pipe:0",
    "-ar",
    "16000",
    "-ac",
    "1",
    "-f",
    "s16le",
    "pipe:1",
  ],
  { input: Buffer.from(wav), windowsHide: true, timeout: 30000 },
);
if (converted.status !== 0)
  throw new Error("No se pudo convertir el audio de prueba");
const buffer = converted.stdout;
const text = await voice.transcribe(
  buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength),
);
const result = {
  time: new Date().toISOString(),
  syntheticAudio: true,
  microphoneUsed: false,
  ttsBytes: wav.byteLength,
  sttText: text,
  health: await voice.health(),
};
writeFileSync("qa/voice-results.json", JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
voice.cancel();
