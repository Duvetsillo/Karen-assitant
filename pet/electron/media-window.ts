import type { MusicSnapshot } from '../shared/music.js';
import { chooseMusicSession } from '../shared/music.js';
import type { Settings } from '../shared/types.js';

/** Window policy only. It never controls playback, captures audio or stores tracks. */
export class MediaWindowController {
  private snapshot: MusicSnapshot = {enabled:false,status:'off',sessions:[]};
  private pauseDelay = 0;
  private pauseTimer?: ReturnType<typeof setTimeout>;
  private safetyTimer?: ReturnType<typeof setInterval>;
  private dismissed?: string;
  private checking = false;
  private requested = false;
  private manual = false;
  private disposed = false;
  constructor(private options: {
    settings: () => Settings; blocked: () => boolean; safe: () => Promise<boolean>;
    show: () => void; hide: () => void;
  }) {}
  get visibleRequested() { return this.requested; }
  update(snapshot: MusicSnapshot) {
    if(this.disposed)return;
    this.snapshot=snapshot;
    const settings=this.options.settings(), song=chooseMusicSession(snapshot.sessions,snapshot.activeId);
    if (!settings.musicPlayer || !snapshot.enabled || !song || this.options.blocked()) {
      this.hide(); this.stopSafety(); return;
    }
    if (song?.status === 'playing') {
      clearTimeout(this.pauseTimer); this.pauseTimer=undefined;
      if (settings.musicAutoShow && song.trackId !== this.dismissed) void this.check();
      if(!this.manual&&!this.safetyTimer)this.safetyTimer=setInterval(()=>void this.check(),3000);
    } else {
      this.stopSafety();
      if(this.requested&&(!this.pauseTimer||this.pauseDelay!==settings.musicAutoHideSeconds)){clearTimeout(this.pauseTimer);this.pauseDelay=settings.musicAutoHideSeconds;this.pauseTimer=setTimeout(()=>{this.pauseTimer=undefined;this.hide();},settings.musicAutoHideSeconds*1000);}
    }
  }
  openManual() {
    if(!this.options.settings().musicPlayer)throw new Error('Activa el minirreproductor en Música.');
    if(this.options.blocked())throw new Error('La cápsula se mantiene oculta en este modo o durante una introducción.');
    this.dismissed=undefined; this.manual=true; this.stopSafety();this.requested=true; this.options.show();
  }
  dismiss() { this.dismissed=chooseMusicSession(this.snapshot.sessions,this.snapshot.activeId)?.trackId;this.hide(); }
  private async check() {
    if(this.checking||this.disposed)return;
    const settings=this.options.settings(),song=chooseMusicSession(this.snapshot.sessions,this.snapshot.activeId);
    if(this.options.blocked()||!settings.musicPlayer){this.hide();return;}
    if(!song||song.status!=='playing'||this.manual)return;
    this.checking=true;
    try {
      const safe=await this.options.safe().catch(()=>false);
      const current=chooseMusicSession(this.snapshot.sessions,this.snapshot.activeId);
      if(this.disposed||this.options.blocked()||this.manual||current?.status!=='playing')return;
      if(!safe){this.hide();return;}
      if(!this.requested&&this.options.settings().musicAutoShow&&current.trackId!==this.dismissed){this.requested=true;this.options.show();}
    } finally { this.checking=false; }
  }
  private hide(){this.manual=false;this.requested=false;clearTimeout(this.pauseTimer);this.pauseTimer=undefined;this.options.hide();}
  private stopSafety(){clearInterval(this.safetyTimer);this.safetyTimer=undefined;}
  dispose(){this.disposed=true;this.stopSafety();this.hide();}
}
