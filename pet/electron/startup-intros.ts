import { BrowserWindow, ipcMain, screen } from 'electron';
import { join } from 'node:path';
import { readFileSync, writeFileSync, renameSync } from 'node:fs';
import type { Settings } from '../shared/types.js';
import { INTRO_IDS, IntroTimeline, selectIntro, shouldPlayIntro, type IntroId, type IntroPayload } from '../shared/startup-intros.js';
import { GreetingLibrary, ResourceCache, greetingVoiceVersion } from './greeting-library.js';
import { IntroGuard } from './intro-guard.js';
import { randomUUID } from 'node:crypto';

export class StartupIntroManager {
  private previousGreeting?:string;
  private window?: BrowserWindow;
  private guard?: IntroGuard;
  private cache?: ResourceCache;
  private payload?: IntroPayload;
  private watchdog?: ReturnType<typeof setTimeout>;
  private previous?: IntroId;
  private epoch = 0;
  private busy = false;
  private restorePet = false;
  private started = false;
  private landingToken?: string;
  private landingPromise?: Promise<boolean>;
  private landingResolve?: (ready: boolean) => void;
  private landingTimer?: ReturnType<typeof setTimeout>;
  private revealed = false;
  private lastPlayed = 0;
  private automatic = false;
  constructor(private options: {
    pet: BrowserWindow; settings: () => Settings; directory: string;
    catalog?:string;
    prefs: () => Electron.WebPreferences;
    load: (window: BrowserWindow, view: string) => Promise<unknown>;
    protect: (window: BrowserWindow) => void;
    blocked: () => boolean;
    log: (message: string) => void;
  }) {
    try {
      const stored=JSON.parse(readFileSync(join(options.directory,'intro-last-play.json'),'utf8'));
      if(Number.isFinite(stored.at)&&stored.at>0&&stored.at<=Date.now())this.lastPlayed=stored.at;
    } catch { /* First run or unreadable timing never prevents opening the pet. */ }
    const own = (event: Electron.IpcMainInvokeEvent) => {
      if (event.sender.id !== this.window?.webContents.id || event.senderFrame !== event.sender.mainFrame)
        throw new Error('Origen de introducción no autorizado.');
    };
    ipcMain.handle('intro-payload', event => { own(event); return this.payload; });
    ipcMain.handle('intro-ready', event => {
      own(event);
      if (this.started || !this.payload || this.options.blocked()) { if (this.options.blocked()) this.cancel(); return false; }
      this.started = true;
      if(this.automatic){
        this.lastPlayed=Date.now();
        try {
          const file=join(this.options.directory,'intro-last-play.json');
          writeFileSync(file+'.tmp',JSON.stringify({at:this.lastPlayed}),{mode:0o600});renameSync(file+'.tmp',file);
        } catch { this.options.log('No se pudo recordar la frecuencia del saludo. La introducción continúa.'); }
      }
      this.options.pet.hide();
      this.window!.showInactive(); // Never take foreground focus, including in preview.
      return true;
    });
    ipcMain.handle('intro-finished', event => { own(event); this.cancel(); });
    ipcMain.handle('intro-prepare-landing', event => { own(event); return this.prepareLanding(); });
    ipcMain.handle('intro-reveal-pet', event => { own(event); this.revealPet(); });
    ipcMain.handle('intro-pet-rendered', (event, token: unknown) => {
      if (event.sender.id !== this.options.pet.webContents.id || event.senderFrame !== event.sender.mainFrame)
        throw new Error('Origen de mascota no autorizado.');
      if (typeof token === 'string' && token === this.landingToken) {
        clearTimeout(this.landingTimer); this.landingResolve?.(true); this.landingResolve = undefined;
      }
    });
  }
  get active() { return this.busy; }
  greetingStatus() {
    const s = this.options.settings(), cache = new ResourceCache();
    try {
      const version = greetingVoiceVersion(s, s.voiceRoot || process.env.KAREN_PROJECT_ROOT || join(this.options.directory, 'voice'));
      const result = new GreetingLibrary(join(this.options.directory, 'startup-greetings'), cache, version).choose(s.introFixed, new Date().getHours());
      return result.greeting ? { available: true, message: 'Saludo local preparado con tu voz configurada.' } :
        { available: false, message: 'Falta un saludo compatible con tu voz actual. La entrada se reproducirá en silencio.' };
    } catch { return { available: false, message: 'No hay una biblioteca local compatible con la voz configurada.' }; }
    finally { cache.clear(); }
  }
  get coveringPet() { return Boolean(this.landingToken && !this.revealed); }
  private prepareLanding(): Promise<boolean> {
    if (this.landingPromise) return this.landingPromise;
    if (!this.restorePet || this.options.pet.isDestroyed()) return Promise.resolve(false);
    this.landingToken = randomUUID();
    this.landingPromise = new Promise(resolve => {
      this.landingResolve = resolve;
      this.landingTimer = setTimeout(() => { this.landingResolve = undefined; resolve(false); }, 700);
    });
    const pet = this.options.pet;
    pet.setOpacity(0); pet.setIgnoreMouseEvents(true);
    pet.webContents.setBackgroundThrottling(false);
    pet.webContents.send('desktop-event', { type: 'intro-landing', token: this.landingToken });
    pet.showInactive();
    return this.landingPromise;
  }
  private revealPet() {
    this.revealed = true;
    if (this.restorePet && !this.options.pet.isDestroyed()) {
      this.options.pet.setOpacity(1); this.options.pet.showInactive();
    }
    // Swap native surfaces before the intro's React/Pixi cleanup can clear its
    // final frame. The regular avatar has already rendered under zero opacity.
    this.window?.hide();
  }
  async play(id?: IntroId, startup = false, trigger: 'startup'|'return' = 'startup'): Promise<boolean> {
    if (id !== undefined && !INTRO_IDS.includes(id)) throw new Error('Introducción desconocida.');
    if (this.busy || this.options.blocked()) return false;
    const settings = { ...this.options.settings() };
    if ((startup && !shouldPlayIntro(settings,trigger,Date.now(),this.lastPlayed)) || settings.mode !== 'normal') return false;
    this.automatic = startup;
    this.busy = true; this.restorePet = startup || this.options.pet.isVisible();
    const epoch = ++this.epoch;
    try {
      this.guard = new IntroGuard();
      if (!await this.guard.start(reason => { if (reason) this.options.log(reason); this.cancel(); }, settings.introEscape) || epoch !== this.epoch) {
        if (epoch === this.epoch) this.cancel(); return false;
      }
      const bounds = this.options.pet.getBounds();
      const home = screen.getDisplayMatching(bounds);
      const display = screen.getAllDisplays().find(d => String(d.id) === settings.introMonitor) ?? home;
      // The flight lands on the home monitor, even when the cinematic uses another display.
      const target = { ...bounds, x: bounds.x - display.bounds.x, y: bounds.y - display.bounds.y };
      const selected = id ?? selectIntro(settings, new Date().getHours(), this.previous);
      this.previous = selected;
      this.cache = new ResourceCache();
      let greeting: Pick<IntroPayload, 'greeting' | 'audio'> = {};
      if (settings.introVoice) {
        try {
          const version = greetingVoiceVersion(settings, settings.voiceRoot || process.env.KAREN_PROJECT_ROOT || join(this.options.directory, 'voice'));
          greeting = new GreetingLibrary(join(this.options.directory, 'startup-greetings'), this.cache, version,
            this.options.catalog).choose(selected, new Date().getHours(),undefined,
              {previousId:this.previousGreeting,category:trigger==='return'?'absence':undefined,mix:trigger!=='return'});
          this.previousGreeting=greeting.greeting?.id;
        } catch { /* Missing voice identity keeps the cinematic silent. */ }
      }
      if(!greeting.greeting){
        greeting=new GreetingLibrary(join(this.options.directory,'startup-greetings'),this.cache,'text-only',this.options.catalog)
          .choose(selected,new Date().getHours(),undefined,{previousId:this.previousGreeting,category:trigger==='return'?'absence':undefined,mix:trigger!=='return'});
        this.previousGreeting=greeting.greeting?.id;
      }
      this.payload = { id: selected, settings, target, ...greeting };
      this.guard.expectOverlay();
      const w = this.window = new BrowserWindow({
        ...display.bounds, frame: false, transparent: true, backgroundColor: '#00000000',
        resizable: false, movable: false, hasShadow: false, skipTaskbar: true,
        fullscreenable: false, focusable: false, alwaysOnTop: true, show: false,
        title: 'Karen · Introducción', webPreferences: { ...this.options.prefs(), autoplayPolicy: 'no-user-gesture-required' },
      });
      this.options.protect(w);
      w.setIgnoreMouseEvents(true);
      w.setMenuBarVisibility(false);
      w.on('closed', () => { if (this.window === w) this.cancel(); });
      w.webContents.on('render-process-gone', () => this.cancel());
      w.on('unresponsive', () => this.cancel());
      this.watchdog = setTimeout(() => this.cancel(), 8000 + new IntroTimeline(selected, false, greeting.greeting?.duration).duration * 1000);
      await this.options.load(w, 'intro');
      return epoch === this.epoch;
    } catch {
      this.options.log('No se pudo reproducir la introducción; se muestra la mascota habitual.');
      if (epoch === this.epoch) this.cancel();
      return false;
    }
  }
  cancel() {
    ++this.epoch;
    clearTimeout(this.watchdog); this.watchdog = undefined;
    this.guard?.stop(); this.guard = undefined;
    clearTimeout(this.landingTimer); this.landingTimer = undefined;
    this.landingResolve?.(false); this.landingResolve = undefined;
    this.landingPromise = undefined; this.landingToken = undefined;
    const w = this.window; this.window = undefined;
    if (!this.options.pet.isDestroyed()) {
      this.options.pet.setOpacity(1);
      this.options.pet.webContents.setBackgroundThrottling(true);
      this.options.pet.webContents.send('desktop-event', { type: 'intro-landing', token: null });
    }
    if (this.restorePet && !this.options.pet.isDestroyed()) this.options.pet.showInactive();
    if (w && !w.isDestroyed()) w.destroy();
    this.cache?.clear(); this.cache = undefined; this.payload = undefined;
    this.restorePet = false; this.started = false; this.busy = false; this.revealed = false;
  }
  dispose() {
    this.restorePet = false; this.cancel();
    for (const channel of ['intro-payload', 'intro-ready', 'intro-finished', 'intro-prepare-landing', 'intro-reveal-pet', 'intro-pet-rendered']) ipcMain.removeHandler(channel);
  }
}
