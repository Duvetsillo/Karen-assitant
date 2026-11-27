import { expect, it } from 'vitest';
import { introDefaults, shouldPlayIntro } from '../shared/startup-intros';
import { validateSettings } from '../shared/settings';
import { IdleActivities } from '../src/pet/idle-activities';
import { defaults } from '../shared/settings';

it('separates preview, startup, daily and explicit return greetings',()=>{
  const morning=new Date(2026,10,26,9).getTime(), evening=new Date(2026,10,26,20).getTime(), tomorrow=new Date(2026,10,27,9).getTime();
  expect(shouldPlayIntro({...introDefaults,introFrequency:'daily'},'startup',morning,0)).toBe(true);
  expect(shouldPlayIntro({...introDefaults,introFrequency:'daily'},'startup',evening,morning)).toBe(false);
  expect(shouldPlayIntro({...introDefaults,introFrequency:'daily'},'startup',tomorrow,morning)).toBe(true);
  expect(shouldPlayIntro({...introDefaults,introFrequency:'after-away'},'startup',morning,0)).toBe(false);
  expect(shouldPlayIntro({...introDefaults,introFrequency:'after-away'},'return',morning,0)).toBe(true);
  expect(shouldPlayIntro({...introDefaults,introFrequency:'manual'},'startup',morning,0)).toBe(false);
  expect(shouldPlayIntro({...introDefaults,introEnabled:false},'return',morning,0)).toBe(false);
  expect(()=>validateSettings({introFrequency:'every-second' as never})).toThrow();
});

it('varies idle activities without immediately repeating the previous clip',()=>{
  const input={settings:defaults,state:'IDLE' as const,lastActivity:0,blocked:false,reducedMotion:false};
  const low=new IdleActivities(()=>0), high=new IdleActivities(()=>.999);
  expect(low.update(input,30000).kind).toBe('play');
  expect(high.update(input,30000).kind).toBe('orbit');
  low.update(input,40000);
  expect(low.update(input,200000).kind).not.toBe('play');
});
