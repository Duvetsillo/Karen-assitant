import{describe,it,expect}from'vitest';
import{IDLE_CLIPS,idlePose,type IdleClip}from'../shared/idle-clips';
import{IdleActivities}from'../src/pet/idle-activities';
import{defaults}from'../shared/settings';
describe('idle variety',()=>{
 it('plays every clip before repeating the round',()=>{const scheduler=new IdleActivities(()=>.47);let now=30000;const seen:string[]=[];
  for(let n=0;n<Object.keys(IDLE_CLIPS).length;n++){const frame=scheduler.update({settings:defaults,state:'IDLE',lastActivity:0,blocked:false,reducedMotion:false},now);expect(frame.kind).not.toBe('none');seen.push(frame.kind);scheduler.update({settings:defaults,state:'IDLE',lastActivity:0,blocked:false,reducedMotion:false},now+IDLE_CLIPS[frame.kind as IdleClip].duration+1);now+=200000;}
  expect(new Set(seen).size).toBe(Object.keys(IDLE_CLIPS).length);
 });
 it.each(Object.keys(IDLE_CLIPS)as IdleClip[])('%s has finite bounded poses and neutral endpoints',kind=>{
  for(const p of[0,.1,.5,.9,1])for(const value of Object.values(idlePose(kind,p)))expect(Number.isFinite(value)).toBe(true);
  expect(Math.abs(idlePose(kind,1).x)).toBeLessThan(.001);expect(idlePose(kind,.5).eye).toBeGreaterThan(.05);
 });
});
