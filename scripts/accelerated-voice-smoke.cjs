// Real local Qwen + Electron decoding/playback, synthetic text, muted output.
const { _electron: electron, expect } = require('@playwright/test');
const { createCoreQaProfile } = require('./core-qa-profile.cjs');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const root = path.resolve(process.env.KAREN_TEST_VOICE_ROOT || '..');
  const { directory, profile, cleanup } = createCoreQaProfile('karen-native-voice-');
  const core = path.join(directory, 'core.sqlite3');
  execFileSync('python', ['-c', 'from conversations import Conversations; import sys; Conversations(sys.argv[1]).current()', core], { cwd: root });
  const env = { ...process.env, KAREN_QA_PROFILE: profile, KAREN_CORE_DB: core };
  delete env.ELECTRON_RUN_AS_NODE;
  const executable = process.env.KAREN_SMOKE_EXECUTABLE;
  const expectedClips = Number(process.env.KAREN_EXPECTED_VOICE_CLIPS || 2);
  const label = process.env.KAREN_VOICE_LABEL || 'native';
  assert(/^[a-z0-9-]+$/.test(label));
  const app = await electron.launch({ ...(executable ? { executablePath: executable, args: ['--qa'] }
    : { args: [path.resolve('.'), '--qa'] }), env, timeout: 30000 });
  const token = fs.readFileSync(path.join(root, 'voice-models/.expressive-token'), 'utf8').trim();
  const health = async () => {
    const response = await fetch('http://127.0.0.1:18790/health', { headers: { Authorization: `Bearer ${token}` } });
    assert(response.ok);
    return response.json();
  };
  const report = { syntheticText: true, hardware: 'local configured Qwen/CUDA', outputMuted: true, audibleReview: false, rendererErrors: [] };
  try {
    const panel = app.windows().find(w => w.url().includes('view=settings')) ||
      await app.waitForEvent('window', { predicate: w => w.url().includes('view=settings') });
    await panel.waitForSelector('h1');
    for (const page of app.windows()) page.on('pageerror', error => report.rendererErrors.push(error.message));
    const pet = app.windows().find(w => w.url().includes('view=pet'));
    assert(pet);
    await panel.evaluate(async root => {
      await window.karen.settings({ voiceRoot: root, ttsEngine: 'local', voiceEnabled: true,
        sttEnabled: false, wakeWordEnabled: false, volume: 0, outputDevice: '' });
      await window.karen.prepareVoice();
      window.__ttsPhases = [];
      window.__ttsStart = performance.now();
      window.karen.event(event => {
        if (event.type === 'capture' && event.status.kind === 'voice')
          window.__ttsPhases.push({ phase: event.status.phase, seconds: (performance.now() - window.__ttsStart) / 1000 });
      });
    }, root);
    const text = process.env.KAREN_VOICE_SAMPLE === 'tasks'
      ? 'Podemos revisar juntos el estado de tus tareas. Después te explicaré cada resultado con claridad y en el orden correcto.'
      : 'Puedo ayudarte a organizar mejor tus pendientes. Después revisamos los pasos necesarios para terminar cada tarea.';
    await app.evaluate(({ BrowserWindow }, text) => {
      for (const win of BrowserWindow.getAllWindows()) win.webContents.send('desktop-event', {
        type: 'chat', final: true, message: { id: 'qa-accelerated-voice', role: 'assistant', text },
      });
    }, text);
    await expect.poll(() => panel.evaluate(() => window.__ttsPhases.filter(p => p.phase === 'speaking').length), { timeout: 180000 }).toBeGreaterThan(0);
    report.healthAtFirstPlayback = await health();
    await expect.poll(() => panel.evaluate(() => window.__ttsPhases.filter(p => p.phase === 'speaking').length), { timeout: 180000 }).toBe(expectedClips);
    await expect.poll(() => panel.evaluate(() => window.karen.snapshot().then(s => s.capture.phase)), { timeout: 60000 }).toBe('idle');
    report.phases = await panel.evaluate(() => window.__ttsPhases);
    report.firstPlaybackSeconds = report.phases.find(p => p.phase === 'speaking').seconds;
    report.healthAfterPlayback = await health();
    // Exercise real transport cancellation before a long utterance completes.
    await pet.evaluate(() => {
      window.__cancelResult = 'pending';
      void window.karen.synthesize('Esta es una prueba sintética de cancelación segura. '.repeat(8))
        .then(() => { window.__cancelResult = 'unexpected-success'; }, () => { window.__cancelResult = 'cancelled'; });
    });
    await expect.poll(async () => (await health()).phase, { timeout: 60000 }).toBe('generating');
    const started = performance.now();
    await pet.evaluate(() => window.karen.cancelSynthesis());
    await expect.poll(async () => (await health()).phase, { timeout: 10000 }).toBe('ready');
    report.cancelRecoverySeconds = (performance.now() - started) / 1000;
    await expect.poll(() => pet.evaluate(() => window.__cancelResult)).toBe('cancelled');
    const result = await pet.evaluate(async () => {
      const bytes = await window.karen.synthesize('La prueba terminó y podemos continuar.');
      const context = new AudioContext();
      try {
        const audio = await context.decodeAudioData(bytes);
        return { duration: audio.duration, sampleRate: audio.sampleRate };
      } finally { await context.close(); }
    });
    assert(result.duration > 1);
    report.synthesisAfterCancel = result;
    assert.deepEqual(report.rendererErrors, []);
    assert.equal((await health()).lastError, null);
    fs.mkdirSync('qa', { recursive: true });
    fs.writeFileSync(`qa/accelerated-voice-${label}.json`, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await app.close();
    cleanup();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
