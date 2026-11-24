const { _electron: electron, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');

(async () => {
  const root = process.env.KAREN_TEST_VOICE_ROOT;
  assert(root, 'Set KAREN_TEST_VOICE_ROOT to your own configured voice resources');
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({ args: [path.resolve('.'), '--qa'], env, timeout: 30000 });
  const errors = [];
  let panel, before;
  try {
    panel = app.windows().find(page => page.url().includes('view=settings')) ||
      await app.waitForEvent('window', { predicate: page => page.url().includes('view=settings'), timeout: 20000 });
    assert(panel);
    await panel.waitForSelector('h1');
    app.windows().forEach(page => page.on('pageerror', error => errors.push(error.message)));
    before = (await panel.evaluate(() => window.karen.snapshot())).settings;
    await panel.evaluate(root => window.karen.settings({ voiceRoot: root, ttsEngine: 'local', voiceEnabled: true }), root);
    await panel.getByRole('button', { name: 'Voz', exact: true }).click();
    await panel.getByRole('button', { name: 'Consultar motores', exact: true }).click();
    const result = await panel.evaluate(async () => {
      const bytes = await window.karen.synthesize('Hola, soy Karen. Esta es mi voz compartida.');
      const decoder = new AudioContext();
      try {
        const audio = await decoder.decodeAudioData(bytes.slice(0));
        let sum = 0;
        for (const sample of audio.getChannelData(0)) sum += sample * sample;
        return { bytes: Array.from(new Uint8Array(bytes)), duration: audio.duration,
                 rms: Math.sqrt(sum / audio.length), health: await window.karen.voiceHealth() };
      } finally { await decoder.close(); }
    });
    assert(result.duration > .5 && result.duration < 15 && result.rms > .005);
    const digest = createHash('sha256').update(Buffer.from(result.bytes)).digest('hex');
    await panel.evaluate(() => window.karen.testVoice());
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture?.phase, { timeout: 180000 }).toBe('speaking');
    const speaking = await panel.evaluate(() => window.karen.snapshot());
    assert.equal(speaking.capture.kind, 'voice');
    const pet = app.windows().find(page => page.url().includes('view=pet'));
    if (pet) await pet.screenshot({ path: 'qa/shared-voice-speaking.png', omitBackground: true });
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture?.phase, { timeout: 30000 }).toBe('idle');
    await panel.screenshot({ path: 'qa/shared-voice-settings.png' });
    assert.deepEqual(errors, []);
    const active = JSON.parse(fs.readFileSync(path.join(root, 'voice-models', 'active-voice.json'), 'utf8'));
    const report = { profile: active.id, nativeIpc: true, playbackCompleted: true,
      bytes: result.bytes.length, sha256: digest, duration: result.duration, rms: result.rms,
      health: result.health, rendererErrors: errors };
    fs.writeFileSync('qa/shared-voice-native.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    if (panel && before) await panel.evaluate(settings => window.karen.settings(settings), before).catch(() => {});
    await app.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
