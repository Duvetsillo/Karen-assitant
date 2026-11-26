import { afterEach, expect, it, vi } from 'vitest';
import { DepartureTimeline } from '../shared/departure';
const handlers = vi.hoisted(()=>new Map<string, (...args:any[])=>unknown>());
vi.mock('electron',()=>({ipcMain:{handle:(key:string,fn:(...args:any[])=>unknown)=>handlers.set(key,fn),removeHandler:(key:string)=>handlers.delete(key)}}));
import { PetDeparture } from '../electron/pet-departure';
afterEach(()=>{vi.useRealTimers();handlers.clear();});
function setup(visible=true) {
  const pet={isDestroyed:()=>false,isVisible:()=>visible,setIgnoreMouseEvents:vi.fn(),webContents:{id:7,mainFrame:{},isLoadingMainFrame:()=>false,send:vi.fn()}};
  const manager=new PetDeparture(()=>pet as never);
  return {pet,manager,event:{sender:pet.webContents,senderFrame:pet.webContents.mainFrame}};
}
it('accepts completion only from its own frame and matching token',async()=>{
  const {manager,pet,event}=setup();const pending=manager.play();
  const token=pet.webContents.send.mock.calls[0][1].token;
  expect(()=>handlers.get('pet-departure-complete')!({...event,senderFrame:{}},token)).toThrow(/no autorizado/);
  handlers.get('pet-departure-complete')!(event,'stale');expect(manager.active).toBe(true);
  handlers.get('pet-departure-complete')!(event,token);await pending;expect(manager.active).toBe(false);manager.dispose();
});
it('does not delay a hidden pet and bounds an unresponsive renderer',async()=>{
  vi.useFakeTimers();const hidden=setup(false);await hidden.manager.play();expect(hidden.pet.webContents.send).not.toHaveBeenCalled();hidden.manager.dispose();
  const {manager}=setup();const pending=manager.play();expect(manager.play()).toBe(pending);
  await vi.advanceTimersByTimeAsync(1200);await pending;expect(manager.active).toBe(false);manager.dispose();
});
it('ends cleanly with reduced motion and a short full goodbye',()=>{
  for(const reduced of [false,true]){const timeline=new DepartureTimeline(reduced);expect(timeline.sample(0).alpha).toBe(1);expect(timeline.sample(timeline.duration).alpha).toBe(0);expect(timeline.sample(timeline.duration).done).toBe(true);if(reduced)expect(timeline.sample(.1).y).toBe(0);}
});
