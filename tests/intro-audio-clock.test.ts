import { afterEach, expect, it, vi } from 'vitest';
import { AudioCueManager } from '../src/intros/AudioCueManager';
afterEach(()=>vi.unstubAllGlobals());
it('retries a suspended greeting cue and starts the voice clock only on playback',async()=>{
  let context:any;
  class Context {
    state='running';currentTime=4;destination={};
    start=vi.fn();resume=vi.fn(async()=>{this.state='running';});
    constructor(){context=this;}
    decodeAudioData=async()=>({});
    createGain=()=>({gain:{value:0},connect:()=>({})});
    createBufferSource=()=>({buffer:undefined,connect:()=>({connect:()=>({})}),start:this.start,stop:()=>{},disconnect:()=>{}});
    close=async()=>{};
  }
  vi.stubGlobal('AudioContext',Context);
  const audio=new AudioCueManager(.4);await audio.prepare(new Uint8Array([1]));
  context.state='suspended';expect(audio.greetingElapsed).toBeUndefined();audio.greetingCue();
  await Promise.resolve();await Promise.resolve();
  expect(context.start).toHaveBeenCalledOnce();audio.greetingCue();expect(context.start).toHaveBeenCalledOnce();
  context.currentTime=4.5;expect(audio.greetingElapsed).toBe(.5);audio.dispose();
});
