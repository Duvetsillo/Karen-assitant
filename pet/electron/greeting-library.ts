import { readFileSync, realpathSync, statSync } from 'node:fs';
import { join, resolve, sep } from 'node:path';
import { INTRO_IDS, greetingCategory, type Greeting, type IntroId } from '../shared/startup-intros.js';
import type { Settings } from '../shared/types.js';

export function greetingVoiceVersion(settings: Settings, root: string): string {
  let identity = `system-speech:${process.platform}`;
  if (settings.ttsEngine === 'edge') throw new Error('Los saludos requieren un proveedor local.');
  if (settings.ttsEngine === 'local') {
    const profile = JSON.parse(readFileSync(join(root, 'voice-models/active-voice.json'), 'utf8'));
    if (!/^[a-z0-9-]{1,64}$/.test(profile.id) || !/^[a-f0-9]{64}$/.test(profile.reference_sha256)) throw new Error('Perfil de voz inválido.');
    identity = `${profile.id}:${profile.reference_sha256}`;
  } else if (settings.ttsEngine === 'fast') identity = 'kokoro-configured';
  return `${settings.ttsEngine}:${identity}:${settings.voiceStyle}:v1`;
}

/** Per-playback cache, bounded and discarded when the window closes. No synthesis path. */
export class ResourceCache {
  private audio?: Uint8Array;
  load(root: string, file: string) {
    if (!/^[a-z0-9-]{1,64}\.wav$/.test(file)) throw new Error('Archivo de saludo inválido.');
    const base = realpathSync(root), path = realpathSync(resolve(base, file));
    if (!path.startsWith(base + sep) || statSync(path).size > 4_000_000) throw new Error('Audio fuera de límites.');
    const data = readFileSync(path);
    if (data.length > 4_000_000) throw new Error('Audio fuera de límites.');
    if (data.subarray(0, 4).toString() !== 'RIFF' || data.subarray(8, 12).toString() !== 'WAVE') throw new Error('Se necesita WAV.');
    this.audio = new Uint8Array(data);
    return this.audio;
  }
  clear() { this.audio = undefined; }
}
export class GreetingLibrary {
  constructor(private root: string, private cache: ResourceCache, private voiceVersion?: string,private catalogPath?:string) {}
  private previous?:string;
  private pool(valid:Greeting[],id:IntroId,hour:number,options:{previousId?:string;category?:string;mix?:boolean}){
    const category=options.category??(id==='surprise'?'humor':greetingCategory(hour));
    let choices=valid.filter(g=>g.category===category||(options.mix&&['general','productivity','restart'].includes(g.category)));
    if(!choices.length)choices=valid.filter(g=>g.category==='general');
    const fresh=choices.filter(g=>g.id!==(options.previousId??this.previous));
    if(fresh.length)choices=fresh;
    const greeting=choices[Math.floor(Math.random()*choices.length)];this.previous=greeting?.id;return greeting;
  }
  private catalog(id:IntroId,text:string|undefined):Greeting[]{
    if(!this.catalogPath)return [];
    try{
      if(statSync(this.catalogPath).size>500000)return [];
      const catalog=JSON.parse(readFileSync(this.catalogPath,'utf8')) as {category:string;texts:string[]}[];
      const valid:Greeting[]=catalog.slice(0,16).flatMap(group=>group.texts.slice(0,20).filter(line=>typeof line==='string'&&line.length<500&&(text===undefined||line===text)).map((line,index)=>{
        const duration=Math.min(9,Math.max(2,line.length/16));return {id:`text-${group.category}-${index}`,text:line,category:group.category,file:'',voiceVersion:'text-only',intros:[id],duration,envelopeStep:.05,envelope:Array(Math.ceil(duration/.05)+1).fill(0)};
      }));
      return valid;
    }catch{return [];}
  }
  private fallback(id:IntroId,hour:number,text:string|undefined,options:{previousId?:string;category?:string;mix?:boolean}){
    const greeting=this.pool(this.catalog(id,text),id,hour,options);return greeting?{greeting}:{};
  }
  choose(id: IntroId, hour: number, text?: string,options:{previousId?:string;category?:string;mix?:boolean}={}): { greeting?: Greeting; audio?: Uint8Array } {
    try {
      const path = join(this.root, 'manifest.json');
      if (statSync(path).size > 500_000) return {};
      const manifest = JSON.parse(readFileSync(path, 'utf8'));
      if (manifest.schema !== 1 || !Array.isArray(manifest.greetings)) return this.fallback(id,hour,text,options);
      const valid = manifest.greetings.slice(0, 100).filter((g: Greeting) =>
        g && typeof g.id === 'string' && typeof g.text === 'string' && g.text.length < 500 &&
        typeof g.file === 'string' && typeof g.voiceVersion === 'string' &&
        (this.voiceVersion === undefined || g.voiceVersion === this.voiceVersion) &&
        (text === undefined || g.text === text) &&
        Array.isArray(g.intros) && g.intros.includes(id) && g.intros.every(i => INTRO_IDS.includes(i)) &&
        Number.isFinite(g.duration) && g.duration > 0 && g.duration <= 15 &&
        Number.isFinite(g.envelopeStep) && g.envelopeStep >= .01 && g.envelopeStep <= .1 &&
        Array.isArray(g.envelope) && g.envelope.length <= 1501 && g.envelope.length >= Math.floor(g.duration / g.envelopeStep) &&
        g.envelope.every(n => Number.isFinite(n) && n >= 0 && n <= 1));
      const catalog=this.catalog(id,text);
      const candidates=catalog.length?catalog.map(g=>valid.find((v:Greeting)=>v.text===g.text)??g):valid;
      const greeting=this.pool(candidates,id,hour,options);
      if(!greeting)return this.fallback(id,hour,text,options);
      return greeting.voiceVersion==='text-only'?{greeting}:{ greeting, audio: this.cache.load(this.root, greeting.file) };
    } catch { return this.fallback(id,hour,text,options); }
  }
}
