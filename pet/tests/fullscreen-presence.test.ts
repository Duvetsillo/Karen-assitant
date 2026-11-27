import {describe,it,expect,vi} from 'vitest';
import {FullscreenPresence} from '../electron/fullscreen-presence';
function fixture(){let finish:()=>void=()=>{};let blocked=false;
 const pet={visible:vi.fn(()=>true),leave:vi.fn(()=>new Promise<void>(resolve=>{finish=resolve;})),hide:vi.fn(),show:vi.fn(),reset:vi.fn()};
 return {pet,controller:new FullscreenPresence(pet,()=>blocked),finish:()=>finish(),block:(value:boolean)=>{blocked=value;}};}
describe('fullscreen presence ownership',()=>{
 it('retries when the first sample arrives before the pet is ready',async()=>{const t=fixture();t.pet.visible.mockReturnValue(false);await t.controller.update(true,true);t.pet.visible.mockReturnValue(true);const run=t.controller.update(true,true);t.finish();await run;expect(t.pet.hide).toHaveBeenCalledOnce();});
 it('waits for the departure then hides and restores only its own pet',async()=>{const t=fixture();const run=t.controller.update(true,true);expect(t.pet.hide).not.toHaveBeenCalled();t.finish();await run;expect(t.pet.hide).toHaveBeenCalledOnce();await t.controller.update(false,true);expect(t.pet.show).toHaveBeenCalledOnce();});
 it('cancels a departure if fullscreen exits before it finishes',async()=>{const t=fixture();const run=t.controller.update(true,true);await t.controller.update(false,true);t.finish();await run;expect(t.pet.hide).not.toHaveBeenCalled();});
 it('does not resurrect a manually hidden pet',async()=>{const t=fixture();const run=t.controller.update(true,true);t.finish();await run;t.controller.userHide();await t.controller.update(false,true);expect(t.pet.show).not.toHaveBeenCalled();});
 it('retries after an intro blocks and defers restoration while locked',async()=>{const t=fixture();t.block(true);await t.controller.update(true,true);expect(t.pet.leave).not.toHaveBeenCalled();t.block(false);const run=t.controller.update(true,true);t.finish();await run;t.block(true);await t.controller.update(false,true);expect(t.pet.show).not.toHaveBeenCalled();t.block(false);await t.controller.update(false,true);expect(t.pet.show).toHaveBeenCalledOnce();});
 it('ignores failed samples and stops hiding when disabled',async()=>{const t=fixture();await t.controller.update(null,true);expect(t.pet.leave).not.toHaveBeenCalled();const run=t.controller.update(true,true);t.finish();await run;await t.controller.update(null,false);expect(t.pet.show).toHaveBeenCalledOnce();});
});
