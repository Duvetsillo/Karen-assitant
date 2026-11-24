/** Synthetic silence exercises microphone lifecycle without recording a person. */
const { _electron: electron, expect } = require('@playwright/test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'karen-wake-'));
  const fixture = path.join(directory, 'silence.wav');
  const wav = Buffer.alloc(44 + 16000 * 2 * 2);
  wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28);
  wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34);
  wav.write('data', 36); wav.writeUInt32LE(wav.length - 44, 40);
  fs.writeFileSync(fixture, wav);
  const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE;
  let app;
  try {
    app = await electron.launch({args: [path.resolve('.'), '--qa',
      '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
      `--use-file-for-fake-audio-capture=${fixture}`], env});
    const panel = app.windows().find(p => p.url().includes('view=settings')) ||
      await app.waitForEvent('window', {predicate: p => p.url().includes('view=settings')});
    await panel.waitForSelector('h1');
    const errors = [];
    for (const page of app.windows()) page.on('pageerror', error => errors.push(error.message));
    const state = () => panel.evaluate(() => window.karen.snapshot());
    await panel.evaluate(() => window.karen.settings({sttEnabled:true,wakeWordEnabled:false}));
    await expect(panel.getByRole('button', {name:'Activar escucha', exact:true})).toBeVisible();
    await panel.getByRole('button', {name:'Activar escucha', exact:true}).click();
    await expect.poll(async () => (await state()).wakeStatus).toBe('listening');
    await panel.evaluate(() => window.karen.abort());
    await expect.poll(async () => (await state()).wakeStatus).toBe('listening');
    assert.equal((await state()).settings.wakeWordEnabled, true, 'Stop must preserve the wake preference');
    await panel.getByRole('button', {name:'Pausar escucha', exact:true}).click();
    await expect.poll(async () => (await state()).wakeStatus).toBe('off');
    assert.equal((await state()).settings.wakeWordEnabled, false, 'Explicit pause must persist');
    await expect(panel.getByRole('button', {name:'Activar escucha', exact:true})).toBeVisible();
    const pet = app.windows().find(p => p.url().includes('view=pet'));
    await pet.evaluate(() => {
      window.restoreMicrophone = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = async () => {throw new Error('QA microphone unavailable');};
    });
    await panel.getByRole('button', {name:'Activar escucha', exact:true}).click();
    await expect.poll(async () => (await state()).wakeStatus).toBe('error');
    await expect(panel.getByRole('button', {name:'Reintentar escucha', exact:true})).toBeVisible();
    await pet.evaluate(() => {navigator.mediaDevices.getUserMedia = window.restoreMicrophone;});
    await panel.getByRole('button', {name:'Reintentar escucha', exact:true}).click();
    await expect.poll(async () => (await state()).wakeStatus).toBe('listening');
    await panel.getByRole('button', {name:'Pausar escucha', exact:true}).click();
    await expect.poll(async () => (await state()).wakeStatus).toBe('off');
    assert.deepEqual(errors, []);
    const report = {stopPreservesWake:true,explicitPauseClosesMicrophone:true,
      pausedStateRecoverable:true,microphoneErrorRetry:true,realMicrophoneUsed:false,errors};
    fs.mkdirSync('qa', {recursive:true});
    fs.writeFileSync('qa/wake-controls.json', JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally {
    if (app) await app.close();
    fs.unlinkSync(fixture); fs.rmdirSync(directory);
  }
})().catch(error => {console.error(error);process.exitCode=1;});
