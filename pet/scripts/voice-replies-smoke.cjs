const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

(async () => {
  fs.mkdirSync('qa', { recursive: true });
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({ args: [path.resolve('.'), '--qa',
    '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'], env });
  const report = { source: 'synthetic native events; Windows System.Speech playback', rendererErrors: [] };
  try {
    const panel = app.windows().find(page => page.url().includes('view=settings')) ||
      await app.waitForEvent('window', { predicate: page => page.url().includes('view=settings') });
    await panel.waitForSelector('h1');
    for (const page of app.windows()) page.on('pageerror', error => report.rendererErrors.push(error.message));
    const pet = app.windows().find(page => page.url().includes('view=pet'));
    assert(pet);
    await panel.evaluate(() => window.karen.settings({ voiceRoot:'', wakeWordEnabled:false, voiceEnabled: true, sttEnabled: false, ttsEngine: 'system', outputDevice: '', volume: .4, scale: 1 }));
    await expect(pet.getByRole('button', { name: 'Repetir última respuesta', exact: true })).toBeDisabled();
    await expect(pet.getByRole('button', { name: 'Hablar ahora o terminar dictado', exact: true })).toBeDisabled();
    await panel.evaluate(() => {
      window.__voicePhases = [];
      window.__maxVoiceEnergy = 0;
      window.__stopReplyProbe = window.karen.event(event => {
        if (event.type === 'capture') window.__voicePhases.push(event.status.phase);
        if (event.type === 'energy') window.__maxVoiceEnergy = Math.max(window.__maxVoiceEnergy, event.value);
      });
    });
    const emit = async events => app.evaluate(({ BrowserWindow }, events) => {
      for (const event of events) for (const window of BrowserWindow.getAllWindows()) window.webContents.send('desktop-event', event);
    }, events);
    await emit([
      { type: 'capture', status: { kind: 'microphone', phase: 'transcribing' } },
      { type: 'chat', final: true, message: { id: 'qa-final-during-stt', role: 'assistant', text: 'Hola. Esta respuesta espera a que termine la transcripción.' } },
    ]);
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).capture.phase, 'idle');
    await emit([{ type: 'capture', status: { kind: 'microphone', phase: 'idle' } }]);
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture.phase, { timeout: 30000 }).toBe('speaking');
    await emit([{ type: 'pet', state: 'HAPPY', reason: 'Late Gateway completion' }]);
    await expect(pet.locator('.pet-caption')).toContainText('Hablando');
    await emit([{ type: 'chat', final: true, message: { id: 'qa-next-final', role: 'assistant', text: 'La siguiente respuesta también se reproduce, con una boca expresiva y suave.' } }]);
    await expect.poll(() => panel.evaluate(() => window.__voicePhases.filter(phase => phase === 'speaking').length), { timeout: 30000 }).toBe(2);
    await expect.poll(() => panel.evaluate(() => window.__maxVoiceEnergy), { timeout: 10000 }).toBeGreaterThan(.01);
    await pet.screenshot({ path: 'qa/reply-speaking.png', omitBackground: true });
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture.phase, { timeout: 30000 }).toBe('idle');
    await pet.evaluate(() => document.activeElement?.blur());
    await pet.mouse.move(-10, -10);
    await expect.poll(() => pet.locator('.pet-toolbar').evaluate(node => getComputedStyle(node).pointerEvents)).toBe('none');
    report.hiddenToolbarPassesClicks = true;
    const replay = pet.getByRole('button', { name: 'Repetir última respuesta', exact: true });
    await replay.focus();
    await expect(replay).toBeEnabled();
    await replay.click();
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture.phase, { timeout: 30000 }).toBe('speaking');
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).connection.state, 'disconnected');
    report.replayWithoutGateway = true;
    await panel.evaluate(() => window.karen.settings({ sttEnabled: true }));
    await pet.getByRole('button', { name: 'Hablar ahora o terminar dictado', exact: true }).click();
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture.phase, { timeout: 10000 }).toBe('recording');
    report.microphoneInterruptsSpeech = true;
    await panel.evaluate(() => window.karen.abort());
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture.phase).toBe('idle');
    await panel.evaluate(() => window.karen.settings({ sttEnabled: false }));
    await pet.getByRole('button', { name: 'Leer respuestas', exact: true }).click();
    await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).capture.phase).toBe('idle');
    await expect(replay).toBeDisabled();
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).settings.voiceEnabled, false);
    report.quickMuteStopsPlayback = true;
    await pet.getByRole('button', { name: 'Leer respuestas', exact: true }).click();
    await panel.evaluate(() => window.karen.settings({ ttsEngine: 'local' }));
    await emit([{ type: 'capture', status: { kind: 'voice', phase: 'preparing', startedAt: Date.now() - 16000 } }]);
    await expect(pet.getByText('La generación local puede tardar.', { exact: true })).toBeVisible();
    await expect(pet.locator('.capture-clock')).toContainText(/0:1[6-9]/);
    for (const scale of [.5, 1, 2]) {
      await panel.evaluate(scale => window.karen.settings({ scale }), scale);
      await emit([{type:'chat',final:true,speak:false,message:{id:`qa-layout-${scale}`,role:'assistant',text:'Esta respuesta permanece legible mientras Karen prepara el audio, sin superponerse al indicador de voz.'}}]);
      await expect(pet.locator('.pet-bubble')).toBeVisible();
      const layout = await pet.evaluate(() => {
        const status=document.querySelector('.capture-status').getBoundingClientRect();
        const bubble=document.querySelector('.pet-bubble').getBoundingClientRect();
        const toolbar=document.querySelector('.pet-toolbar').getBoundingClientRect();
        return {
          separate:status.bottom+4<=bubble.top && toolbar.bottom<=bubble.top,
          characterClear:status.bottom<=innerHeight*.25 && bubble.top>=innerHeight*.8,
          inside:bubble.bottom<=innerHeight&&bubble.left>=0&&bubble.right<=innerWidth,
        };
      });
      assert(layout.separate&&layout.characterClear&&layout.inside,'Voice status and reply bubble must stay clear of Karen at '+scale);
      const fits = await pet.locator('.pet-toolbar').evaluate(node => { const r = node.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; });
      assert(fits, 'Toolbar must fit the pet at ' + scale);
      await pet.waitForTimeout(180);
      await pet.screenshot({ path: `qa/quick-controls-${scale}.png`, omitBackground: true });
    }
    report.waitClockAndScale = true;
    report.dialogueDoesNotOverlap = true;
    await emit([{ type: 'capture', status: { kind: 'voice', phase: 'idle' } }]);
    report.phases = await panel.evaluate(() => window.__voicePhases);
    report.mouthEnergy = await panel.evaluate(() => window.__maxVoiceEnergy);
    report.deferredFinalPlayed = true;
    report.nextReplyPlayed = true;
    report.gatewayCannotOverrideSpeech = true;
    assert.deepEqual(report.rendererErrors, []);
    await panel.evaluate(() => window.__stopReplyProbe());
    fs.writeFileSync('qa/voice-replies-native.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await app.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
