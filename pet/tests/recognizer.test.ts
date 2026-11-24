import { afterEach, describe, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { LocalRecognizer } from '../electron/recognizer';
import { NativeVoice } from '../electron/voice';
import { defaults } from '../shared/settings';
import { existsSync } from 'node:fs';
vi.mock('node:child_process', async original => ({...await original<typeof import('node:child_process')>(), spawn:vi.fn()}));
const roots: string[] = [];
const engines: LocalRecognizer[] = [];
afterEach(()=>{ engines.splice(0).forEach(r=>r.cancel()); roots.splice(0).forEach(p=>rmSync(p,{recursive:true,force:true})); vi.clearAllMocks(); });
function fixture() {
  const root = mkdtempSync(join(tmpdir(),'karen-recognizer-'));
  roots.push(root);
  mkdirSync(join(root,'voice-runtime/Scripts'),{recursive:true});
  mkdirSync(join(root,'voice-models/faster-whisper-small'),{recursive:true});
  writeFileSync(join(root,'voice-runtime/Scripts/python.exe'),'fixture');
  writeFileSync(join(root,'voice-models/faster-whisper-small/model.bin'),'fixture');
  const worker=join(root,'recognize.py'); writeFileSync(worker,'fixture');
  const child=Object.assign(new EventEmitter(),{stdin:new PassThrough(),stdout:new PassThrough(),stderr:new PassThrough(),kill:vi.fn()});
  vi.mocked(spawn).mockReturnValue(child as never);
  const engine=new LocalRecognizer(worker); engines.push(engine);
  return {root,child,engine,pcm:new Int16Array(16000).buffer};
}
describe('reconocedor local persistente',()=>{
  it('Windows TTS no exige una carpeta de modelos locales',async()=>{
    const {child}=fixture();
    const voice=new NativeVoice(join(tmpdir(),'karen-missing-resources-fixture'),()=>({...defaults,ttsEngine:'system'}));
    const result=voice.synthesize('Hola');
    child.stdout.write(Buffer.from('RIFFsynthetic').toString('base64'));
    child.emit('exit',0);
    expect(Buffer.from(await result).toString()).toBe('RIFFsynthetic');
    expect(existsSync(vi.mocked(spawn).mock.calls[0][2].cwd as string)).toBe(true);
    voice.cancel();
  });
  it('reutiliza el proceso y fija cwd en la carpeta de recursos',async()=>{
    const {root,child,engine,pcm}=fixture();
    const first=engine.transcribe(root,pcm);
    child.stdout.write('{"text":"Caren, seguimos."}\n');
    expect(await first).toBe('Caren, seguimos.');
    const second=engine.transcribe(root,pcm);
    child.stdout.write('{"text":"Segunda frase"}\n');
    expect(await second).toBe('Segunda frase');
    expect(spawn).toHaveBeenCalledTimes(1);
    expect(spawn).toHaveBeenCalledWith(expect.any(String),expect.arrayContaining(['--persistent']),expect.objectContaining({cwd:root,windowsHide:true}));
  });
  it('explica un fallo de arranque sin exponer stderr',async()=>{
    const {root,child,engine,pcm}=fixture();
    const result=engine.transcribe(root,pcm);
    child.emit('error',Object.assign(new Error('private diagnostic'),{code:'ENOENT'}));
    await expect(result).rejects.toThrow('ENOENT');
  });
  it('cancelar una petición libera su promesa',async()=>{
    const {root,engine,pcm}=fixture();
    const result=engine.transcribe(root,pcm);
    engine.cancel();
    await expect(result).rejects.toThrow('cancelado');
  });
  it('explica el fallo del modelo sin mostrar la envoltura técnica',async()=>{
    const {root,child,engine,pcm}=fixture();
    const result=engine.transcribe(root,pcm);
    child.stdout.write('{"error":"model"}\n');
    await expect(result).rejects.toThrow('No se pudo cargar el modelo de voz');
    expect(child.kill).toHaveBeenCalled();
  });
  it('rechaza audio fuera de límites antes de iniciar Python',async()=>{
    const {root,engine}=fixture();
    await expect(engine.transcribe(root,new ArrayBuffer(2))).rejects.toThrow('Audio inválido');
    expect(spawn).not.toHaveBeenCalled();
  });
  it('identifica el recurso ausente sin confundirlo con una falta de voz',async()=>{
    const {root,engine,pcm}=fixture();
    rmSync(join(root,'voice-models/faster-whisper-small/model.bin'));
    await expect(engine.transcribe(root,pcm)).rejects.toThrow('voice-models/faster-whisper-small/model.bin');
    expect(spawn).not.toHaveBeenCalled();
  });
});
