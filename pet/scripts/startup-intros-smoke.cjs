const { _electron: electron } = require('@playwright/test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { execFile } = require('node:child_process');
const ids = ['breakthrough','glass','awakening','materialization','sleepy','surprise'];
const styles = ['crystal','cloud','orbit','sprite','bloom','aurora','ember','midnight'];
const report = { timestamp: new Date().toISOString(), transport: 'Electron nativo; guardia Windows real; sin Gateway ni modelos', runs: [], samples: [], gpu: [], errors: [] };
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'karen-intro-qa-'));
const output = path.resolve('qa/startup-intros'); fs.mkdirSync(output, { recursive: true });
const env = { ...process.env, KAREN_QA_PROFILE: profile };
delete env.ELECTRON_RUN_AS_NODE; delete env.KAREN_CORE_DB; delete env.KAREN_TASKS_DB;
const greetings = path.resolve('.private/startup-greetings');
if (fs.existsSync(path.join(greetings, 'manifest.json'))) {
  fs.cpSync(greetings, path.join(profile, 'startup-greetings'), { recursive: true });
  const manifest = JSON.parse(fs.readFileSync(path.join(greetings, 'manifest.json'), 'utf8'));
  const [engine, id, hash, voiceStyle] = manifest.voiceVersion.split(':');
  report.greetingCount = manifest.greetings.length;
  if (engine === 'local') {
    const voiceRoot = path.join(profile, 'voice');
    fs.mkdirSync(path.join(voiceRoot, 'voice-models'), { recursive: true });
    fs.writeFileSync(path.join(voiceRoot, 'voice-models/active-voice.json'), JSON.stringify({ id, reference_sha256: hash }));
    fs.writeFileSync(path.join(profile, 'settings.json'), JSON.stringify({ ttsEngine: 'local', voiceStyle, voiceRoot }));
  }
}
let app, panel, pet, timer, gpuTimer, sampling = false, gpuBusy = false;
const delay = ms => new Promise(r => setTimeout(r, ms));
const gpu = () => {
  if (gpuBusy) return;
  gpuBusy = true;
  execFile('nvidia-smi', ['--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader,nounits'], { windowsHide: true, timeout: 3000 }, (error, stdout) => {
    gpuBusy = false;
    if (!error) report.gpu.push({ at: Date.now(), adapterWide: true, value: stdout.trim() });
  });
};
async function launch() {
  app = await electron.launch({ args: [path.resolve('.'), '--qa'], env, timeout: 30000 });
  for (let i = 0; i < 150; i++) {
    if (app.windows().some(w => w.url().includes('view=settings')) && app.windows().some(w => w.url().includes('view=pet'))) break;
    await delay(100);
  }
  panel = app.windows().find(w => w.url().includes('view=settings'));
  pet = app.windows().find(w => w.url().includes('view=pet'));
  assert(panel && pet); await panel.waitForSelector('h1'); await pet.waitForSelector('canvas');
  app.on('window', w => {
    w.on('pageerror', e => report.errors.push(e.message));
    w.on('console', message => { if (message.type() === 'error') console.error(message.text()); });
  });
}
async function play(id, style, accelerated) {
  await panel.evaluate(({ style, accelerated }) => window.karen.settings({ petStyle: style, introVoice: !accelerated, introSounds: !accelerated }), { style, accelerated });
  const home = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.getTitle() === 'Karen Desktop Pet').getBounds());
  const opened = app.waitForEvent('window', { predicate: w => w.url().includes('view=intro'), timeout: 15000 });
  const ok = await panel.evaluate(id => window.karen.playIntro(id), id);
  assert.equal(ok, true, 'Windows permite la introducción');
  const intro = await opened;
  await intro.waitForSelector('canvas');
  await delay(250);
  const window = await app.evaluate(({ BrowserWindow }) => {
    const w = BrowserWindow.getAllWindows().find(w => w.getTitle() === 'Karen · Introducción');
    return w && { bounds: w.getBounds(), frame: w.isFullScreen(), focusable: w.isFocusable(), focused: w.isFocused(), visible: w.isVisible() };
  });
  assert(window && window.visible && !window.focusable && !window.focused);
  const resources = await intro.evaluate(async () => {
    const p = await window.karenIntro.payload();
    return { greeting: Boolean(p.greeting), audio: Boolean(p.audio?.length) };
  });
  if (report.greetingCount === 40 && !accelerated) assert(resources.greeting && resources.audio);
  await assert.rejects(() => intro.evaluate(() => window.karen.snapshot()), /Origen no autorizado/);
  await assert.rejects(() => panel.evaluate(() => window.karenIntro.payload()), /Origen de introducción no autorizado/);
  let measuredFPS;
  if (accelerated) {
    await intro.clock.install();
    await intro.clock.fastForward(2000);
    await intro.screenshot({ path: path.join(output, `${id}-${style}.png`), omitBackground: true });
    await intro.clock.fastForward(30000);
  } else {
    await delay(3000);
    measuredFPS = await intro.locator('.pet-renderer').getAttribute('data-render-fps');
    await intro.screenshot({ path: path.join(output, `${id}.png`), omitBackground: true });
  }
  if (!intro.isClosed()) await intro.waitForEvent('close', { timeout: 22000 }).catch(error => { if (!intro.isClosed()) throw error; });
  const final = await app.evaluate(({ BrowserWindow }) => {
    const p = BrowserWindow.getAllWindows().find(w => w.getTitle() === 'Karen Desktop Pet');
    return { bounds: p.getBounds(), visible: p.isVisible(), windows: BrowserWindow.getAllWindows().length };
  });
  assert.deepEqual(final.bounds, home); assert.equal(final.visible, true); assert.equal(final.windows, 2);
  report.runs.push({ id, style, accelerated, window, restored: true, measuredFPS, resources });
  console.log(`OK ${id} ${style} ${accelerated ? 'reloj acelerado' : 'tiempo real'}`);
}
(async () => {
  try {
    await launch();
    timer = setInterval(async () => {
      if (sampling) return; sampling = true;
      try { report.samples.push({ at: Date.now(), processes: await app.evaluate(({ app }) => app.getAppMetrics().map(m => ({ type: m.type, cpu: m.cpu.percentCPUUsage, workingSetKB: m.memory.workingSetSize }))) }); }
      catch {} finally { sampling = false; }
    }, 500);
    gpuTimer = setInterval(gpu, 1500); gpu();
    // Six unaccelerated playbacks provide actual resource measurements.
    if (!process.argv.includes('--matrix-only') && !process.argv.includes('--checks-only')) for (const id of ids) await play(id, 'crystal', false);
    if (process.argv.includes('--matrix')) for (const style of styles) for (const id of ids) await play(id, style, true);
    await delay(3000);
    report.settledProcesses = await app.evaluate(({ app }) => app.getAppMetrics().map(m => ({ type: m.type, cpu: m.cpu.percentCPUUsage, workingSetKB: m.memory.workingSetSize })));
    // Explicit cancel and recovery, then local command and persistence.
    const played = await panel.evaluate(() => window.karen.playIntro('awakening'));
    if (played) {
      const intro = app.windows().find(w => w.url().includes('view=intro'));
      assert(intro); await intro.waitForSelector('canvas');
      await intro.keyboard.press('Escape').catch(error => { if (!intro.isClosed()) throw error; });
      if (!intro.isClosed()) await intro.waitForEvent('close', { timeout: 3000 });
      report.escape = 'Evento de teclado entregado por Playwright; tecla física pendiente';
    } else {
      report.escape = 'No ejecutado: Windows omitió la introducción por escritorio protegido.';
      report.introSkippedByWindows = true;
    }
    await panel.evaluate(() => window.karen.send('Karen, usa introducciones aleatorias'));
    await panel.evaluate(() => window.karen.send('Karen, desactiva los saludos de inicio'));
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).settings.introVoice, false);
    await panel.evaluate(() => window.karen.settings({ introSelection: 'fixed', introFixed: 'sleepy', introFPS: 30, introVolume: .25 }));
    assert.equal(JSON.parse(fs.readFileSync(path.join(profile, 'settings.json'), 'utf8')).introFixed, 'sleepy');
    await app.close(); app = undefined;
    await launch();
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).settings.introFixed, 'sleepy');
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).settings.introFPS, 30);
    await panel.evaluate(() => window.karen.settings({ mode: 'gaming' }));
    assert.equal(await panel.evaluate(() => window.karen.playIntro('glass')), false);
    report.persistenceAfterRestart = true; report.gamingSuppression = true; report.ipcIsolation = true;
    assert.deepEqual(report.errors, []);
    console.log(JSON.stringify({ runs: report.runs.length, errors: report.errors, persistence: true, gamingSuppression: true }));
  } catch (error) {
    report.failure = error.stack; console.error(error);
    if (panel && !panel.isClosed()) console.error(JSON.stringify((await panel.evaluate(() => window.karen.snapshot())).diagnostics));
    process.exitCode = 1;
  }
  finally {
    clearInterval(timer); clearInterval(gpuTimer);
    if (app) await app.close().catch(() => {});
    fs.writeFileSync(path.join(output, process.argv.includes('--checks-only') ? 'checks.json' : 'metrics.json'), JSON.stringify(report, null, 2));
    fs.rmSync(profile, { recursive: true, force: true });
  }
})();
