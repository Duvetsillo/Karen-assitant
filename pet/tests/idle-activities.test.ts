import { describe, it, expect } from 'vitest';
import { IdleActivities } from '../src/pet/idle-activities';
import { defaults, effectiveSettings, validateSettings } from '../shared/settings';
import type { PetState } from '../shared/types';

const input = () => ({settings:{...defaults}, state:'IDLE' as PetState, lastActivity:0, blocked:false, reducedMotion:false});
describe('reposo decorativo, sin acciones del asistente', () => {
  it('recalcula la espera al reactivar animaciones con un plazo más corto sin recrear el renderer',()=>{
    const scheduler=new IdleActivities(()=>0),context=input();
    scheduler.update({...context,settings:{...context.settings,animations:false}},1000);
    scheduler.update({...context,settings:{...context.settings,animations:false}},1500);
    const enabled={...context,lastActivity:2000,settings:{...context.settings,idleAfter:15}};
    expect(scheduler.update(enabled,2000).kind).toBe('none');
    expect(scheduler.update(enabled,16999).kind).toBe('none');
    expect(scheduler.update(enabled,17000).kind).toBe('play');
  });
  it('espera, termina el juego y deja una pausa antes de cambiar de actividad', () => {
    const scheduler = new IdleActivities(()=>0), context = input();
    expect(scheduler.update(context, 29999).kind).toBe('none');
    expect(scheduler.update(context, 30000)).toEqual({kind:'play',progress:0});
    expect(scheduler.update(context, 34250).progress).toBeCloseTo(.5);
    expect(scheduler.update(context, 38500).kind).toBe('none');
    expect(scheduler.update(context, 98499).kind).toBe('none');
    expect(scheduler.update(context, 114500).kind).toBe('stretch');
    expect(scheduler.update(context, 121000).kind).toBe('none');
    expect(scheduler.update(context, 197000).kind).toBe('play');
  });
  it.each(['LISTENING','THINKING','SPEAKING','ERROR','DRAGGING','SLEEPING'] as PetState[])(
    'cede inmediatamente ante %s', state => {
      const scheduler = new IdleActivities(()=>0), context = input();
      expect(scheduler.update(context, 30000).kind).toBe('play');
      expect(scheduler.update({...context,state},31000).kind).toBe('none');
      expect(scheduler.update(context,32000).kind).toBe('none');
    });
  it('suspende al capturar, modificar ajustes o reanudar una pestaña oculta', () => {
    const scheduler = new IdleActivities(()=>0), context = input();
    scheduler.update(context,30000);
    expect(scheduler.update({...context,lastActivity:31000},31000).kind).toBe('none');
    expect(scheduler.update({...context,blocked:true},90000).kind).toBe('none');
    expect(scheduler.update(context,91000).kind).toBe('none');
    scheduler.suspend(200000,30);
    expect(scheduler.update(context,200001).kind).toBe('none');
    expect(scheduler.update(context,230000).kind).toBe('stretch');
  });
  it('respeta bajo consumo, accesibilidad, actividad cero y todos los interruptores', () => {
    const context = input();
    for (const settings of [{...defaults,lowPower:true},{...defaults,animations:false},
      {...defaults,idleActivities:false},{...defaults,activity:0},
      effectiveSettings({...defaults,mode:'gaming'}),effectiveSettings({...defaults,mode:'do_not_disturb'})])
      expect(new IdleActivities(()=>0).update({...context,settings},90000).kind).toBe('none');
    expect(new IdleActivities(()=>0).update({...context,reducedMotion:true},90000).kind).toBe('none');
  });
  it('no exige extremidades para jugar con una luz; acepta preferencia y reloj corregido', () => {
    const scheduler = new IdleActivities(()=>0), context = input();
    context.settings = {...defaults,showArms:false,showLegs:false,idleActivity:'stargaze'};
    expect(scheduler.update(context,30000).kind).toBe('stargaze');
    expect(scheduler.update(context,20000).kind).toBe('none');
  });
  it('migra ajustes anteriores sin tocar voz o proveedores y rechaza valores inválidos', () => {
    expect(validateSettings({petStyle:'crystal',voiceRoot:'C:/karen'})).toMatchObject({showArms:false,showLegs:false,idleActivities:true,voiceRoot:'C:/karen'});
    expect(validateSettings({showArms:false,showLegs:false,petStyle:'midnight'})).toMatchObject({showArms:false,showLegs:false,petStyle:'midnight'});
    expect(validateSettings({showArms:true,showLegs:true})).toMatchObject({showArms:false,showLegs:false});
    expect(() => validateSettings({showArms:'no' as never})).toThrow();
    expect(() => validateSettings({idleActivity:'execute' as never})).toThrow();
    expect(validateSettings({idleAfter:0}).idleAfter).toBe(15);
  });
});
