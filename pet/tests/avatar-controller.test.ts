import { describe, expect, it } from 'vitest';
import { AvatarController } from '../src/pet/avatar-controller';
import { AVATAR_STATES, toolVisualState } from '../shared/avatar-states';
import { PET_STATES } from '../shared/types';

describe('provider-independent avatar control', () => {
  const quiet = {capture:{kind:'voice' as const,phase:'idle' as const},music:true,focused:true};
  it('prioritizes interaction and live voice over decoration', () => {
    const controller=new AvatarController();
    expect(controller.resolve('IDLE',quiet)).toBe('FOCUSED');
    expect(controller.resolve('IDLE',{...quiet,focused:false})).toBe('MUSIC_LISTENING');
    expect(controller.resolve('READING',{...quiet,capture:{kind:'voice',phase:'speaking'}})).toBe('SPEAKING');
    expect(controller.resolve('DRAGGING',{...quiet,capture:{kind:'voice',phase:'speaking'}})).toBe('DRAGGING');
    expect(controller.resolve('ERROR',quiet)).toBe('ERROR');
  });
  it('blends an interrupted pose and stays finite for every supported state', () => {
    const controller=new AvatarController();
    for(let i=0;i<90;i++)controller.update('SEARCHING',1/60,true,.6);
    const before=controller.update('SEARCHING',0,true,.6);
    const after=controller.update('CONCERNED',0,true,.6);
    expect(after).toEqual(before);
    for(const state of PET_STATES) {
      expect(AVATAR_STATES[state].label.length).toBeGreaterThan(1);
      for(const dt of [NaN,-1,100,.016])expect(Object.values(controller.update(state,dt,true,.6)).every(Number.isFinite)).toBe(true);
    }
  });
  it('holds a static expression when motion is reduced', () => {
    const controller=new AvatarController();
    expect(controller.update('MUSIC_LISTENING',.1,false,1)).toEqual(controller.update('MUSIC_LISTENING',10,false,1));
    expect(controller.update('CODING',.1,false,1).gaze).toBe(0);
  });
  it('uses tool metadata as visual data, never as an executable instruction', () => {
    expect(toolVisualState('web_search')).toBe('SEARCHING');
    expect(toolVisualState('read_file')).toBe('READING');
    expect(toolVisualState('apply_patch')).toBe('WRITING');
    expect(toolVisualState('python_test')).toBe('CODING');
    expect(toolVisualState({command:'anything'})).toBe('WORKING');
  });
});
