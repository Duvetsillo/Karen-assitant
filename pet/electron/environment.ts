import type { Settings } from '../shared/types.js';
import type { EnvironmentSnapshot } from '../shared/environment.js';

interface DesktopMetadata {ok:boolean;safeDesktop?:boolean;fullscreen?:boolean;category?:EnvironmentSnapshot['category'];}
interface Observer {start():void;stop():void;context(observe?:boolean):Promise<DesktopMetadata>;}
/** Optional coarse OS metadata. Never reads titles, keys, pixels or documents. */
export class EnvironmentService {
  private timer?:ReturnType<typeof setInterval>;
  private epoch=0;
  private pending=false;
  private lastObserved=0;
  snapshot?:EnvironmentSnapshot;
  constructor(private settings:()=>Settings,private observer:Observer,
    private sample:()=>{idleSeconds:number;onBattery:boolean},private publish:(value:EnvironmentSnapshot)=>void){}
  configure(){
    this.epoch++;clearInterval(this.timer);this.timer=undefined;this.pending=false;
    if(!this.settings().environmentObserve&&!this.settings().fullscreenHide){
      this.observer.stop();this.snapshot={enabled:false,at:Date.now(),idleSeconds:0,onBattery:false,desktopProtected:null,category:'unknown'};
      this.publish(this.snapshot);return;
    }
    if(!this.settings().environmentObserve){
      this.snapshot={enabled:false,at:Date.now(),idleSeconds:0,onBattery:false,desktopProtected:null,category:'unknown',fullscreen:this.snapshot?.fullscreen??null};
      this.publish(this.snapshot);
    }
    this.observer.start();void this.tick();this.timer=setInterval(()=>void this.tick(),this.settings().fullscreenHide?1000:15000);
  }
  private async tick(){
    if(this.pending||(!this.settings().environmentObserve&&!this.settings().fullscreenHide))return;
    const epoch=this.epoch;this.pending=true;
    try{
      const observe=this.settings().environmentObserve&&Date.now()-this.lastObserved>=15000;
      const desktop=await this.observer.context(observe);
      if(epoch!==this.epoch||(!this.settings().environmentObserve&&!this.settings().fullscreenHide))return;
      if(observe)this.lastObserved=Date.now();
      const sample=observe?this.sample():{idleSeconds:this.snapshot?.idleSeconds??0,onBattery:this.snapshot?.onBattery??false};
      this.snapshot={...sample,enabled:this.settings().environmentObserve,at:Date.now(),fullscreen:desktop.ok?desktop.fullscreen??null:null,
        desktopProtected:desktop.ok?desktop.safeDesktop!==true:null,category:!this.settings().environmentObserve?'unknown':observe?(desktop.ok?(desktop.category??'unknown'):'unknown'):(this.snapshot?.category??'unknown')};
      this.publish(this.snapshot);
    }catch{/* A failed sample never grants an action or reuses old context. */}
    finally{if(epoch===this.epoch)this.pending=false;}
  }
  dispose(){this.epoch++;clearInterval(this.timer);this.observer.stop();}
}
