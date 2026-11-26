import { readFileSync, writeFileSync, mkdirSync, renameSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { NativeVoice } from '../electron/voice.js';
import { validateSettings } from '../shared/settings.js';
import { INTRO_IDS, type Greeting } from '../shared/startup-intros.js';
import { analyzeGreetingWav } from '../electron/intro-wav.js';
import { greetingVoiceVersion } from '../electron/greeting-library.js';

const here = dirname(fileURLToPath(import.meta.url));
function argument(name: string) {
  const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : undefined;
}
const settingsPath = argument('--settings'), destination = argument('--output');
if (!settingsPath || !destination) throw new Error('Uso: npm run generate:intro-greetings -- --settings RUTA_SETTINGS --output DIRECTORIO [--resume]');
const raw = JSON.parse(readFileSync(resolve(settingsPath), 'utf8'));
// Refuse a cloud provider BEFORE effectiveSettings can substitute it.
if (raw.ttsEngine === 'edge') throw new Error('El proveedor configurado usa servicios externos. No se sustituirá por otra voz.');
const settings = validateSettings(raw);
const root = settings.voiceRoot || process.env.KAREN_PROJECT_ROOT;
if (!root && settings.ttsEngine !== 'system') throw new Error('Configura la carpeta de la voz existente.');
const voiceRoot = resolve(root || dirname(settingsPath));
const voiceVersion = greetingVoiceVersion(settings, voiceRoot);
const catalog = JSON.parse(readFileSync(argument('--catalog') ? resolve(argument('--catalog')!) : join(here, '../assets/startup-greetings/catalog.json'), 'utf8')) as { category: string; texts: string[] }[];
const total = catalog.reduce((count, category) => count + category.texts.length, 0);
const output = resolve(destination); mkdirSync(output, { recursive: true });
const manifestPath = join(output, 'manifest.json');
let existing: Greeting[] = [];
if (process.argv.includes('--resume') && existsSync(manifestPath)) existing = JSON.parse(readFileSync(manifestPath, 'utf8')).greetings;
const voice = new NativeVoice(voiceRoot, () => settings, undefined, join(here, '../python/shared_voice_service.py'));
const greetings: Greeting[] = [];
const stop = () => { voice.dispose(); process.exitCode = 130; };
process.once('SIGINT', stop);
try {
  let number = 0;
  for (const category of catalog) for (const text of category.texts) {
    if (process.exitCode) throw new Error('Generación cancelada.');
    const id = `greeting-${String(++number).padStart(2, '0')}`, file = `${id}.wav`;
    const previous = existing.find(g => g.id === id && g.voiceVersion === voiceVersion && g.text === text);
    if (previous && existsSync(join(output, file))) {
      const metadata = analyzeGreetingWav(readFileSync(join(output, file)));
      greetings.push({ ...previous, ...metadata });
    } else {
      const bytes = new Uint8Array(await voice.synthesize(text));
      const metadata = analyzeGreetingWav(bytes);
      writeFileSync(join(output, `${id}.tmp`), bytes);
      renameSync(join(output, `${id}.tmp`), join(output, file));
      greetings.push({ id, file, text, category: category.category, intros: [...INTRO_IDS], voiceVersion, ...metadata });
    }
    // Incremental atomic manifest: interruption leaves a usable, honest partial library.
    const manifest = { schema: 1, voiceVersion, generatedAt: new Date().toISOString(),
      settingsFingerprint: createHash('sha256').update(voiceVersion).digest('hex'), greetings };
    writeFileSync(manifestPath + '.tmp', JSON.stringify(manifest, null, 2));
    renameSync(manifestPath + '.tmp', manifestPath);
    console.log(`${number}/${total} ${id} ${greetings.at(-1)!.duration.toFixed(2)}s`);
  }
} finally { voice.dispose(); }
