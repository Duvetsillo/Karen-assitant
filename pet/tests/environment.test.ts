import {afterEach,describe,expect,it,vi} from 'vitest';
import {EnvironmentService} from '../electron/environment';
import {interpretEnvironment,type EnvironmentSnapshot} from '../shared/environment';
import {defaults} from '../shared/settings';
afterEach(()=>vi.useRealTimers());
const sample:EnvironmentSnapshot={enabled:true,at:Date.now(),idleSeconds:1,onBattery:true,desktopProtected:true,category:'coding'};
describe('coarse optional environment',()=>{
  it('requires observation and a separate adaptation permission',()=>{
    expect(interpretEnvironment({...sample,at:Date.now()},false,true).quiet).toBe(false);
    expect(interpretEnvironment({...sample,at:Date.now()},true,false).focused).toBe(false);
    expect(interpretEnvironment({...sample,at:Date.now()},true,true)).toEqual({quiet:true,focused:true,conserve:true});
    expect(interpretEnvironment({...sample,at:Date.now()-60000},true,true).quiet).toBe(false);
  });
  it('does not start or poll by default',async()=>{
    vi.useFakeTimers();const observer={start:vi.fn(),stop:vi.fn(),context:vi.fn()};
    const service=new EnvironmentService(()=>defaults,observer,()=>({idleSeconds:0,onBattery:false}),vi.fn());
    service.configure();await vi.advanceTimersByTimeAsync(60000);
    expect(observer.start).not.toHaveBeenCalled();expect(observer.context).not.toHaveBeenCalled();service.dispose();
  });
  it('samples at low frequency and drops a late result after consent is revoked',async()=>{
    vi.useFakeTimers();let settings={...defaults,environmentObserve:true};
    let finish:(value:{ok:boolean;safeDesktop:boolean})=>void=()=>{};
    const observer={start:vi.fn(),stop:vi.fn(),context:vi.fn(()=>new Promise<{ok:boolean;safeDesktop:boolean}>(resolve=>{finish=resolve;}))};
    const publish=vi.fn();const service=new EnvironmentService(()=>settings,observer,()=>({idleSeconds:2,onBattery:false}),publish);
    service.configure();await vi.advanceTimersByTimeAsync(30000);expect(observer.context).toHaveBeenCalledOnce();
    settings={...settings,environmentObserve:false};service.configure();finish({ok:true,safeDesktop:true});await Promise.resolve();
    expect(publish.mock.calls).toHaveLength(1);expect(publish.mock.calls[0][0].enabled).toBe(false);service.dispose();
  });
});
