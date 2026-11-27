import type { Settings } from '../shared/types.js';
import type { EnvironmentSnapshot } from '../shared/environment.js';

interface DesktopMetadata {ok:boolean;safeDesktop?:boolean;category?:EnvironmentSnapshot['category'];}
interface Observer {start():void;stop():void;context():Promise<DesktopMetadata>;}
/** Optional coarse OS metadata. Never reads titles, keys, pixels or documents. */
export class EnvironmentService {
  private timer?:ReturnType<typeof setInterval>;
  private epoch=0;
  private pending=false;
  snapshot?:EnvironmentSnapshot;
  constructor(private settings:()=>Settings,private observer:Observer,
    private sample:()=>{idleSeconds:number;onBattery:boolean},private publish:(value:EnvironmentSnapshot)=>void){}
  configure(){
    this.epoch++;clearInterval(this.timer);this.timer=undefined;this.pending=false;
    if(!this.settings().environmentObserve){
      this.observer.stop();this.snapshot={enabled:false,at:Date.now(),idleSeconds:0,onBattery:false,desktopProtected:null,category:'unknown'};
      this.publish(this.snapshot);return;
    }
    this.observer.start();void this.tick();this.timer=setInterval(()=>void this.tick(),15000);
  }
  private async tick(){
    if(this.pending||!this.settings().environmentObserve)return;
    const epoch=this.epoch;this.pending=true;
    try{
      const desktop=await this.observer.context();
      if(epoch!==this.epoch||!this.settings().environmentObserve)return;
      const sample=this.sample();
      this.snapshot={...sample,enabled:true,at:Date.now(),desktopProtected:desktop.ok?desktop.safeDesktop!==true:null,category:desktop.ok?(desktop.category??'unknown'):'unknown'};
      this.publish(this.snapshot);
    }catch{/* A failed sample never grants an action or reuses old context. */}
    finally{if(epoch===this.epoch)this.pending=false;}
  }
  dispose(){this.epoch++;clearInterval(this.timer);this.observer.stop();}
}
