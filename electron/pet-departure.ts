import { ipcMain, type BrowserWindow } from 'electron';
import { randomUUID } from 'node:crypto';

/** A bounded goodbye on the already-visible pet; never creates another surface. */
export class PetDeparture {
  private token?: string;
  private pending?: Promise<void>;
  private resolve?: () => void;
  private timer?: ReturnType<typeof setTimeout>;
  constructor(private pet: () => BrowserWindow | undefined) {
    ipcMain.handle('pet-departure-complete', (event, token: unknown) => {
      const pet = this.pet();
      if (!pet || event.sender.id !== pet.webContents.id || event.senderFrame !== event.sender.mainFrame)
        throw new Error('Origen de despedida no autorizado.');
      if (typeof token === 'string' && token === this.token) this.finish();
    });
  }
  get active() { return Boolean(this.token); }
  play() {
    if (this.pending) return this.pending;
    const pet = this.pet();
    if (!pet || pet.isDestroyed() || !pet.isVisible() || pet.webContents.isLoadingMainFrame()) return Promise.resolve();
    this.token = randomUUID();
    this.pending = new Promise<void>(resolve => {
      this.resolve = resolve;
      this.timer = setTimeout(() => this.finish(), 1200);
    });
    pet.setIgnoreMouseEvents(true);
    pet.webContents.send('desktop-event', { type: 'pet-departure', token: this.token });
    return this.pending;
  }
  finish() { clearTimeout(this.timer); this.token = undefined; this.resolve?.(); this.resolve = undefined; this.pending = undefined; }
  dispose() { this.finish(); ipcMain.removeHandler('pet-departure-complete'); }
}
