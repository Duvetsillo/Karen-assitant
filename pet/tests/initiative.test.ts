import {afterEach,describe,it,expect} from 'vitest';
import {mkdtempSync,rmSync,readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {defaults,validateSettings} from '../shared/settings';
import {freshInitiativeJournal,localDay,proposeInitiative,quietHour,type InitiativeContext} from '../shared/initiative-policy';
import {InitiativeService} from '../electron/initiative';
const directories:string[]=[];
afterEach(()=>directories.splice(0).forEach(p=>rmSync(p,{recursive:true,force:true})));
const settings={...defaults,initiativeEnabled:true};
const now=new Date(2026,10,2,12).getTime();
function context(patch:Partial<InitiativeContext>={}):InitiativeContext{
  return {now,hour:12,day:localDay(now),present:true,visible:true,busy:false,lastInteraction:now-90000,disconnectedSince:0,taskChanges:[],...patch};
}
function service(){const dir=mkdtempSync(join(tmpdir(),'karen-initiative-test-'));directories.push(dir);const published:unknown[]=[];
  return {dir,published,make:()=>new InitiativeService(dir,(...state)=>published.push(state))};}
describe('iniciativa local con límites persistentes',()=>{
  it('migra una configuración anterior sin activar conversaciones inesperadas',()=>{
    const migrated=validateSettings({voiceEnabled:true,petStyle:'aurora'});
    expect(migrated.initiativeEnabled).toBe(false);expect(migrated.initiativeSpeak).toBe(false);
    expect(migrated.voiceEnabled).toBe(true);
    expect(validateSettings({initiativeInterval:0,initiativeDailyLimit:99,initiativeQuietStart:22.8})).toMatchObject({initiativeInterval:15,initiativeDailyLimit:12,initiativeQuietStart:23});
    expect(()=>validateSettings({initiativeEnabled:'yes' as never})).toThrow();
    expect(()=>validateSettings({initiativeInterval:NaN})).toThrow();
  });
  it('respeta horarios que cruzan medianoche y horas iguales',()=>{
    expect([21,22,0,8,9].map(h=>quietHour(h,22,9))).toEqual([false,true,true,true,false]);
    expect([8,9,16,17].map(h=>quietHour(h,9,17))).toEqual([false,true,true,false]);
    expect(quietHour(12,9,9)).toBe(false);
  });
  it.each([{present:false},{visible:false},{busy:true}])('no interrumpe ni habla estando ausente: %j',patch=>{
    expect(proposeInitiative(settings,freshInitiativeJournal(),context(patch))).toBeNull();
    expect(proposeInitiative(settings,freshInitiativeJournal(),context(patch),true)).toBeNull();
  });
  it.each(['gaming','do_not_disturb'] as const)('ni siquiera una sugerencia manual ignora %s',mode=>{
    expect(proposeInitiative({...settings,mode},freshInitiativeJournal(),context(),true)).toBeNull();
  });
  it('espera tras interacción, horario silencioso y bloqueo de cuota',()=>{
    const j=freshInitiativeJournal();
    expect(proposeInitiative(settings,j,context({lastInteraction:now-89999}))).toBeNull();
    expect(proposeInitiative(settings,j,context({hour:23}))).toBeNull();
    j.day=localDay(now);j.count=4;
    expect(proposeInitiative(settings,j,context())).toBeNull();
    expect(proposeInitiative(settings,j,context(),true)?.kind).toBe('greeting');
  });
  it('saluda una sola vez, persiste cuota/cooldown al reiniciar, conserva avisos',()=>{
    const x=service(),first=x.make();
    const greeting=first.tick(settings,context());expect(greeting?.kind).toBe('greeting');
    expect(x.published).toHaveLength(1);
    const second=x.make();expect(second.tick(settings,context({now:now+1000}))).toBeNull();
    expect(second.snapshot(now).todayCount).toBe(1);
    second.act('dismiss',greeting!.id,now);
    const notice=second.tick(settings,context({now:now+45*60000}));expect(notice?.kind).toBe('check-in');
    expect(second.snapshot(now).notices.map(n=>n.dismissed)).toEqual([true,false]);
    expect(x.make().snapshot(now).notices).toHaveLength(2);
  });
  it('persiste silencio y reanuda sin ejecutar acciones',()=>{
    const x=service(),j=x.make();j.act('snooze',undefined,now);
    expect(x.make().tick(settings,context())).toBeNull();
    j.act('resume',undefined,now);expect(j.tick(settings,context())?.kind).toBe('greeting');
    expect(()=>j.act('dismiss','unknown',now)).toThrow();
  });
  it('renueva cuota diaria pero no duplica el saludo de un día ya registrado',()=>{
    const x=service(),s=x.make();s.tick(settings,context());
    const tomorrow=now+86400000;
    expect(s.snapshot(tomorrow).todayCount).toBe(0);
    expect(s.tick(settings,context({now:tomorrow,day:localDay(tomorrow),lastInteraction:tomorrow-90000}))?.kind).toBe('greeting');
  });
  it('sólo describe un cambio de tarea real, deduplica y prepara consulta de lectura',()=>{
    const x=service(),s=x.make(),id='a'.repeat(32),task={key:id+':failed:1',id,status:'failed'};
    const n=s.tick(settings,context({taskChanges:[task]}));
    expect(n).toMatchObject({kind:'task',command:`/tareas estado ${id}`});
    expect(n?.text).toContain('problema');
    s.act('dismiss',n!.id,now);
    expect(x.make().tick(settings,context({now:now+46*60000,taskChanges:[task]}))?.kind).toBe('greeting');
    expect(JSON.stringify(s.snapshot(now))).not.toContain('password');
  });
  it('no anuncia éxito ante resultado incierto y rechaza IDs o claves no confiables',()=>{
    const j=freshInitiativeJournal(),task={key:'key',id:'b'.repeat(32),status:'uncertain'};
    expect(proposeInitiative(settings,j,context({taskChanges:[task]}))?.text).toContain('revisión');
    expect(proposeInitiative(settings,j,context({taskChanges:[{...task,id:';shutdown'}]}))?.kind).toBe('greeting');
    expect(proposeInitiative(settings,j,context({taskChanges:[{...task,key:'x'.repeat(200)}]}))?.kind).toBe('greeting');
  });
  it('no oculta ni reemplaza un diario corrupto o de otra versión',()=>{
    const x=service();const raw='{"version":2,"notices":[]}';writeFileSync(join(x.dir,'initiative.json'),raw);
    expect(()=>x.make()).toThrow();expect(readFileSync(join(x.dir,'initiative.json'),'utf8')).toBe(raw);
  });
  it('un reloj atrasado no permite saltarse el intervalo',()=>{
    const j=freshInitiativeJournal();j.lastAt=now+1;
    expect(proposeInitiative(settings,j,context())).toBeNull();
  });
  it('cierra el globo tras dos minutos y conserva su motivo en el historial',()=>{
    const x=service(),s=x.make();s.tick(settings,context());s.expire(now+120000);
    expect(s.snapshot(now+120000).notices[0]).toMatchObject({dismissed:true,kind:'greeting'});
    expect(s.snapshot(now+120000).notices[0].reason).toContain('Primer saludo');
  });
  it('no repite una desconexión durante el mismo día',()=>{
    const x=service(),s=x.make();s.tick(settings,context());
    const later=now+46*60000;
    const n=s.tick(settings,context({now:later,disconnectedSince:now}));expect(n?.kind).toBe('connection');
    expect(s.tick(settings,context({now:later+46*60000,disconnectedSince:now}))?.kind).toBe('check-in');
  });
});
