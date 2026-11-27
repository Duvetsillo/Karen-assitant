import { describe,it,expect } from 'vitest';
import { chooseModel, type ModelInspection } from '../shared/models';
import { validateSettings, defaults } from '../shared/settings';

const inspection:ModelInspection={catalog:[
  {name:'small',size:800000000,capabilities:['completion']},
  {name:'coder',size:2000000000,capabilities:['completion','vision']},
],kind:'coding',rankings:{coding:['coder','small'],conversation:['small','coder'],vision:['coder']},
budget:{ram_available_bytes:8*1073741824,vram_available_bytes:null,vram_total_bytes:null}};
describe('installed model routing',()=>{
  it('uses the Core ranking for the detected task',()=>expect(chooseModel(inspection,['ollama/small','ollama/coder'],'auto',null,null,false).id).toBe('ollama/coder'));
  it('falls back to another installed configured candidate',()=>expect(chooseModel(inspection,['ollama/small'],'auto',null,null,false).id).toBe('ollama/small'));
  it('prefers small weights for voice and economy',()=>expect(chooseModel(inspection,['ollama/small','ollama/coder'],'voice',null,null,false).id).toBe('ollama/small'));
  it('never substitutes a cloud or unconfigured candidate',()=>expect(()=>chooseModel(inspection,['ollama/cloud:cloud'],'auto',null,null,false)).toThrow(/No hay/));
  it('never silently changes an unavailable manual model',()=>expect(()=>chooseModel(inspection,['ollama/small'],'manual','ollama/missing',null,false)).toThrow(/manual/));
  it('requires vision capabilities for an attached image even in fast mode',()=>expect(chooseModel(inspection,['ollama/small','ollama/coder'],'fast',null,null,true).id).toBe('ollama/coder'));
  it('rejects vision when no configured capable model exists',()=>expect(()=>chooseModel(inspection,['ollama/small'],'auto',null,null,true)).toThrow(/No hay/));
  it('validates persisted choices and migrates existing profiles',()=>{
    expect(validateSettings({}).routingMode).toBe('auto');
    expect(validateSettings({routingMode:'manual',resourceProfile:'work'}).resourceProfile).toBe('work');
    expect(()=>validateSettings({routingMode:'remote'} as never)).toThrow();
    expect(()=>validateSettings({resourceProfile:'unlimited'} as never)).toThrow();
    expect(defaults.musicEnabled).toBe(false);
  });
});
