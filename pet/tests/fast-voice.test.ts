import {describe,expect,it,vi} from 'vitest';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve, sep } from 'node:path';
import {FastVoice} from '../electron/fast-voice';
import {NativeVoice} from '../electron/voice';
import {defaults} from '../shared/settings';
import {validateSettings} from '../shared/settings';
describe('voz rápida explícita',()=>{
  it('conserva la selección y el estilo sin sustituir la voz original',()=>{
    expect(validateSettings({ttsEngine:'fast',voiceStyle:'serene'})).toMatchObject({ttsEngine:'fast',voiceStyle:'serene'});
    expect(validateSettings({ttsEngine:'local'}).ttsEngine).toBe('local');
  });
  it('rechaza recursos ausentes con un error útil',async()=>{
    const worker=new FastVoice('nonexistent-worker.py');
    await expect(worker.synthesize('nonexistent-resources','Hola','serene')).rejects.toThrow('Kokoro');
    worker.close();
  });
});

describe('voz neural femenina en línea',()=>{
  function fixture() {
    const root=mkdtempSync(join(process.cwd(), '.edge-voice-test-'));
    const worker=join(root,'python','edge_voice.py');
    mkdirSync(join(root,'voice-runtime','Scripts'),{recursive:true});
    mkdirSync(join(root,'python'),{recursive:true});
    writeFileSync(join(root,'voice-runtime','Scripts','python.exe'),'fixture');
    writeFileSync(worker,'fixture');
    const voice=new NativeVoice(root,()=>({...defaults,ttsEngine:'edge',voiceRoot:root}),undefined,join(root,'python','shared_voice_service.py'));
    const close=()=>{
      voice.dispose();
      if (!root.startsWith(resolve(process.cwd())+sep)) throw new Error('Fixture fuera del repositorio');
      rmSync(root,{recursive:true,force:true});
    };
    return {voice,close};
  }
  it('conserva la selección explícita',()=>{
    expect(validateSettings({ttsEngine:'edge'}).ttsEngine).toBe('edge');
  });
  it('muestra un error útil si faltan los recursos de voz',async()=>{
    const voice=new NativeVoice('nonexistent-voice-root',()=>({...defaults,ttsEngine:'edge'}));
    await expect(voice.synthesize('Hola')).rejects.toThrow('Edge TTS');
    voice.dispose();
  });
  it('reintenta un fallo temporal sin cambiar de voz',async()=>{
    const {voice,close}=fixture();
    const mp3=Buffer.concat([Buffer.from('ID3'),Buffer.alloc(128)]).toString('base64');
    const run=vi.fn().mockRejectedValueOnce(new Error('El motor de voz se detuvo.')).mockResolvedValueOnce(mp3);
    (voice as unknown as {run: typeof run}).run=run;
    try {
      expect(Buffer.from(await voice.synthesize('Hola')).subarray(0,3).toString()).toBe('ID3');
      expect(run).toHaveBeenCalledTimes(2);
    } finally {close();}
  });
  it('no reintenta después de cancelar la voz',async()=>{
    const {voice,close}=fixture();
    let fail!: (error: Error)=>void;
    const run=vi.fn(()=>new Promise<string>((_resolve,reject)=>{fail=reject;}));
    (voice as unknown as {run: typeof run}).run=run;
    try {
      const pending=voice.synthesize('Hola');
      await vi.waitFor(()=>expect(run).toHaveBeenCalledTimes(1));
      voice.cancelSynthesis();
      fail(new Error('El motor de voz se detuvo.'));
      await expect(pending).rejects.toThrow('cancelada');
      expect(run).toHaveBeenCalledTimes(1);
    } finally {close();}
  });
});
