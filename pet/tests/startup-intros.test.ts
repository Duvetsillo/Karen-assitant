import { describe, expect, it } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { INTRO_IDS, IntroTimeline, introCommand, selectIntro, introDefaults, mouthAt } from '../shared/startup-intros';
import { defaults, validateSettings } from '../shared/settings';
import { canSendMessage } from '../shared/local-commands';
import { analyzeGreetingWav } from '../electron/intro-wav';
import { GreetingLibrary, ResourceCache } from '../electron/greeting-library';

const home = { x: 1260, y: 540, width: 380, height: 440 };
function wav() {
  const bytes = Buffer.alloc(44 + 16000);
  bytes.write('RIFF'); bytes.writeUInt32LE(bytes.length - 8, 4); bytes.write('WAVEfmt ', 8);
  bytes.writeUInt32LE(16, 16); bytes.writeUInt16LE(1, 20); bytes.writeUInt16LE(1, 22);
  bytes.writeUInt32LE(8000, 24); bytes.writeUInt32LE(16000, 28); bytes.writeUInt16LE(2, 32); bytes.writeUInt16LE(16, 34);
  bytes.write('data', 36); bytes.writeUInt32LE(16000, 40);
  for (let i = 2000; i < 6000; i++) bytes.writeInt16LE(Math.round(Math.sin(i * .1) * 10000), 44 + i * 2);
  return bytes;
}
describe('startup intro timeline and deterministic routing', () => {
  it('lands every choreography at the actual avatar coordinate, independent of frame count', () => {
    for (const id of INTRO_IDS) for (const hz of [30, 60]) {
      const timeline = new IntroTimeline(id, false, 3);
      for (let frame = 0; frame <= timeline.duration * hz; frame++) {
        const pose = timeline.sample(frame / hz, 1920, 1080, home);
        for (const value of Object.values(pose)) if (typeof value === 'number') expect(Number.isFinite(value)).toBe(true);
      }
      const end = timeline.sample(timeline.duration, 1920, 1080, home);
      expect(end.x).toBe(1450); expect(end.y).toBe(777.6); expect(end.scale).toBe(.8);
      expect(end.dark).toBe(0); expect(end.done).toBe(true);
      expect(timeline.leaveAt).toBeGreaterThanOrEqual(timeline.greetingAt + 3);
    }
  });
  it('has six distinct early poses and keeps reduced motion at home', () => {
    const poses = INTRO_IDS.map(id => new IntroTimeline(id, false).sample(.9, 1920, 1080, home));
    expect(new Set(poses.map(p => JSON.stringify(p))).size).toBe(6);
    for (const id of INTRO_IDS) {
      const timeline = new IntroTimeline(id, true);
      for (const t of [.1, 1, timeline.duration]) {
        const p = timeline.sample(t, 1920, 1080, home);
        expect(p.x).toBe(1450); expect(p.scale).toBe(.8); expect(p.effect).toBe(0); expect(p.tilt).toBe(0);
      }
    }
  });
  it('selects fixed, contextual and nonrepeating random entrances', () => {
    expect(selectIntro({ ...introDefaults, introSelection: 'fixed', introFixed: 'glass' }, 10)).toBe('glass');
    expect(selectIntro({ ...introDefaults, introSelection: 'contextual' }, 3)).toBe('sleepy');
    expect(selectIntro(introDefaults, 9, 'breakthrough', () => 0)).toBe('glass');
  });
  it('routes requested Spanish commands offline without matching quoted conversation', () => {
    for (const text of ['Karen, reproduce tu introducción', 'Karen, cambia tu introducción', 'Karen, reproduce Awakening', 'Karen, usa introducciones aleatorias', 'Karen, desactiva los saludos de inicio']) {
      expect(introCommand(text)).toBeDefined(); expect(canSendMessage(text, 'disconnected')).toBe(true);
    }
    expect(introCommand('Me dijo que Karen reproduce Awakening')).toBeUndefined();
    expect(introCommand('reproduce una película')).toBeUndefined();
  });
  it('validates persisted preferences and rejects malformed settings', () => {
    const settings = validateSettings({ introFixed: 'glass', introSelection: 'fixed', introVolume: .3, introFPS: 30 });
    expect(validateSettings(JSON.parse(JSON.stringify(settings)))).toMatchObject({ introFixed: 'glass', introSelection: 'fixed', introVolume: .3, introFPS: 30 });
    expect(defaults.petStyle).toBe('crystal');
    expect(() => validateSettings({ introFixed: 'unknown' as never })).toThrow();
    expect(() => validateSettings({ introVolume: NaN })).toThrow();
    expect(() => validateSettings({ introEscape: 'yes' as never })).toThrow();
    expect(() => validateSettings({ introMonitor: '../x' })).toThrow();
  });
});
describe('local greeting resources', () => {
  it('ships seventy-eight texts across the nine greeting categories', () => {
    const catalog = JSON.parse(readFileSync(new URL('../assets/startup-greetings/catalog.json', import.meta.url), 'utf8')) as { texts: string[] }[];
    expect(catalog).toHaveLength(9); expect(catalog.flatMap(c => c.texts)).toHaveLength(78);
  });
  it('extracts silence and speech envelope from real PCM samples; rejects truncation', () => {
    const metadata = analyzeGreetingWav(wav());
    expect(metadata.duration).toBe(1); expect(metadata.envelope).toHaveLength(50);
    expect(metadata.envelope[0]).toBe(0); expect(metadata.envelope[20]).toBeGreaterThan(.9);
    expect(() => analyzeGreetingWav(wav().subarray(0, 60))).toThrow();
    expect(mouthAt(undefined, 1)).toBe(0);
  });
  it('uses validated local files and degrades silently for absent, malformed or traversing resources', () => {
    const root = mkdtempSync(join(tmpdir(), 'karen-greetings-'));
    try {
      const cache = new ResourceCache(), library = new GreetingLibrary(root, cache);
      expect(library.choose('sleepy', 3)).toEqual({});
      writeFileSync(join(root, 'greeting-01.wav'), wav());
      const greeting = { id: 'greeting-01', file: 'greeting-01.wav', text: 'Hola', voiceVersion: 'test', category: 'general', intros: [...INTRO_IDS], ...analyzeGreetingWav(wav()) };
      const save = (g: object) => writeFileSync(join(root, 'manifest.json'), JSON.stringify({ schema: 1, greetings: [g] }));
      save(greeting); expect(library.choose('sleepy', 3).audio?.length).toBe(wav().length);
      expect(new GreetingLibrary(root, cache, 'different-voice').choose('sleepy', 3)).toEqual({});
      expect(mouthAt(greeting, .4)).toBeGreaterThan(.9); expect(mouthAt(greeting, 1)).toBe(0);
      save({ ...greeting, file: '../secret.wav' }); expect(library.choose('sleepy', 3)).toEqual({});
      save({ ...greeting, envelopeStep: 0 }); expect(library.choose('sleepy', 3)).toEqual({});
      save({ ...greeting, envelope: [9] }); expect(library.choose('sleepy', 3)).toEqual({});
      cache.clear();
    } finally { rmSync(root, { recursive: true, force: true }); }
  });
  it('uses expanded readable greetings without synthesizing or repeating the last one',()=>{
    const root=mkdtempSync(join(tmpdir(),'karen-greeting-text-'));
    try{
      const catalog=join(root,'catalog.json');writeFileSync(catalog,JSON.stringify([{category:'absence',texts:['Qué bueno que volviste.','Retomemos con calma.']} ]));
      const library=new GreetingLibrary(root,new ResourceCache(),'missing-voice',catalog);
      const first=library.choose('glass',12,undefined,{category:'absence'});
      const second=library.choose('glass',12,undefined,{category:'absence'});
      expect(first.greeting?.text).toBeTruthy();expect(second.greeting?.id).not.toBe(first.greeting?.id);expect(first.audio).toBeUndefined();
      expect(first.greeting?.envelope.every(value=>value===0)).toBe(true);
    }finally{rmSync(root,{recursive:true,force:true});}
  });
});
