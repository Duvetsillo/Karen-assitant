const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({ args: [path.resolve('.'), '--qa'], env });
  let panel, previous;
  try {
    panel = app.windows().find(page => page.url().includes('view=settings')) ||
      await app.waitForEvent('window', { predicate: page => page.url().includes('view=settings') });
    await panel.waitForSelector('h1');
    previous = (await panel.evaluate(() => window.karen.snapshot())).settings;
    await panel.evaluate(() => {
      window.__edgeEnergy = 0;
      window.__edgeStop = window.karen.event(event => {
        if (event.type === 'energy') window.__edgeEnergy = Math.max(window.__edgeEnergy, event.value);
      });
    });
    await panel.evaluate(() => window.karen.settings({ voiceRoot: 'C:/karen', voiceEnabled: true, ttsEngine: 'edge', outputDevice: 'default' }));
    await panel.evaluate(() => window.karen.testVoice());
    const phase = () => panel.evaluate(async () => (await window.karen.snapshot()).capture.phase);
    await expect.poll(phase, { timeout: 30000 }).toBe('speaking');
    await expect.poll(phase, { timeout: 30000 }).toBe('idle');
    const energy = await panel.evaluate(() => window.__edgeEnergy);
    assert(energy > 0.01, 'Neural audio did not reach playback');
    await panel.evaluate(() => window.__edgeStop());
    console.log(JSON.stringify({ neuralPlayback: true, energy }));
  } finally {
    if (panel && previous) await panel.evaluate(settings => window.karen.settings(settings), previous).catch(() => {});
    await app.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
