// Native IPC and real OS-lock workers. Does not open microphone or contact AI.
const { _electron: electron } = require('@playwright/test');
const { createCoreQaProfile } = require('./core-qa-profile.cjs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const { directory, profile, cleanup } = createCoreQaProfile('karen-native-core-');
  const env = { ...process.env, KAREN_RESOURCE_DIR: directory,
    KAREN_PROJECT_ROOT: path.resolve('..'), KAREN_QA_PROFILE: profile };
  delete env.ELECTRON_RUN_AS_NODE;
  const packaged = process.env.KAREN_SMOKE_EXECUTABLE;
  let application;
  try {
    application = await electron.launch({
      ...(packaged ? { executablePath: packaged, args: ['--qa'] } : { args: [path.resolve('.'), '--qa'] }), env,
    });
    let pet, panel;
    for (let attempt = 0; attempt < 100; attempt++) {
      pet = application.windows().find(w => w.url().includes('view=pet'));
      panel = application.windows().find(w => w.url().includes('view=settings'));
      if (pet && panel) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert(pet && panel, 'Faltan ventanas nativas');
    await pet.waitForFunction(() => Boolean(window.karen));
    await panel.waitForFunction(() => Boolean(window.karen));
    const settings = (await panel.evaluate(() => window.karen.snapshot())).settings;
    assert(!settings.wakeWordEnabled && !settings.sttEnabled && !settings.voiceEnabled);
    // Only the disposable QA profile changes, never the user's settings.
    await panel.evaluate(root => window.karen.settings({ voiceRoot: root }), path.resolve('..'));
    const token = await pet.evaluate(() => window.karen.claimMicrophone());
    assert.equal(typeof token, 'string');
    await assert.rejects(panel.evaluate(() => window.karen.claimMicrophone()), /Otra ventana/);
    await panel.evaluate(token => window.karen.releaseMicrophone(token), token);
    await assert.rejects(panel.evaluate(() => window.karen.claimMicrophone()), /Otra ventana/);
    await pet.evaluate(token => window.karen.releaseMicrophone(token), token);
    const second = await panel.evaluate(() => window.karen.claimMicrophone());
    await panel.evaluate(token => window.karen.releaseMicrophone(token), second);
    console.log('CORE_NATIVE_IPC_OK: native windows, scoped ownership, release; no audio hardware opened');
  } finally {
    if (application) await application.close();
    cleanup();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
