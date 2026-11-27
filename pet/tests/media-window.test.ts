import { afterEach, describe, expect, it, vi } from 'vitest';
import { MediaWindowController } from '../electron/media-window';
import { defaults } from '../shared/settings';
import { classifyMusic, type MusicSnapshot } from '../shared/music';

afterEach(()=>vi.useRealTimers());
const snapshot=(status:'playing'|'paused'='playing'):MusicSnapshot=>({enabled:true,status:'ready',sessions:[{sessionId:'qa',trackId:'track',title:'Synthetic music',artist:'QA',album:'QA',source:'fixture.exe',mediaType:'music',status,evidence:'native',updatedAt:0,controls:[]}]});
function setup(){
  const settings={...defaults,musicEnabled:true,musicAutoHideSeconds:2};
  const show=vi.fn(),hide=vi.fn(),blocked=vi.fn(()=>false),safe=vi.fn(async()=>true);
  return {settings,show,hide,blocked,safe,controller:new MediaWindowController({settings:()=>settings,show,hide,blocked,safe})};
}
describe('discreet media window lifecycle',()=>{
  it('opens only for confirmed playback and hides after a bounded pause',async()=>{
    vi.useFakeTimers();const t=setup();t.controller.update(snapshot());await vi.advanceTimersByTimeAsync(0);expect(t.show).toHaveBeenCalledOnce();
    t.controller.update(snapshot('paused'));await vi.advanceTimersByTimeAsync(1999);expect(t.hide).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);expect(t.hide).toHaveBeenCalledOnce();
    t.controller.update(snapshot());await vi.advanceTimersByTimeAsync(0);expect(t.show).toHaveBeenCalledTimes(2);t.controller.dispose();
  });
  it('does not reappear over an explicit dismissal or a protected desktop',async()=>{
    vi.useFakeTimers();const t=setup();t.controller.update(snapshot());await vi.advanceTimersByTimeAsync(0);t.controller.dismiss();
    await vi.advanceTimersByTimeAsync(9000);expect(t.show).toHaveBeenCalledOnce();
    t.controller.openManual();expect(t.show).toHaveBeenCalledTimes(2);t.blocked.mockReturnValue(true);t.controller.update(snapshot());await vi.advanceTimersByTimeAsync(3000);expect(t.controller.visibleRequested).toBe(false);t.controller.dispose();
  });
  it('treats unknown safety as blocked and discards late checks after disposal',async()=>{
    vi.useFakeTimers();const t=setup();t.safe.mockResolvedValue(false);t.controller.update(snapshot());await vi.advanceTimersByTimeAsync(0);expect(t.show).not.toHaveBeenCalled();
    let resolve!:(value:boolean)=>void;t.safe.mockImplementation(()=>new Promise(done=>{resolve=done;}));t.controller.update(snapshot());t.controller.dispose();resolve(true);await vi.advanceTimersByTimeAsync(0);expect(t.show).not.toHaveBeenCalled();
  });
  it('hides immediately when metadata no longer identifies music',async()=>{
    vi.useFakeTimers();const t=setup();t.controller.update(snapshot());await vi.advanceTimersByTimeAsync(0);t.controller.update({enabled:true,status:'ready',sessions:[]});expect(t.controller.visibleRequested).toBe(false);t.controller.dispose();
  });
  it('recognizes generic native music without promoting ambiguous browser video',()=>{
    const music=snapshot().sessions[0];expect(classifyMusic(music)).toBe('windows');
    expect(classifyMusic({...music,source:'msedge.exe'})).toBeUndefined();
    expect(classifyMusic({...music,category:'video'})).toBeUndefined();
    expect(classifyMusic({...music,evidence:'browser'})).toBeUndefined();
  });
});
