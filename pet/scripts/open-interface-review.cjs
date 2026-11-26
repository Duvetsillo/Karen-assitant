// Keep a review of the canonical build open without touching the running app.
const { _electron: electron } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

(async () => {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'karen-interface-review-'));
  fs.writeFileSync(path.join(profile, 'settings.json'), JSON.stringify({
    introEnabled: false, voiceEnabled: false, musicEnabled: false,
    musicHistory: false, musicComments: false,
  }));
  const env = { ...process.env, KAREN_QA_PROFILE: profile };
  for (const key of ['ELECTRON_RUN_AS_NODE', 'KAREN_CORE_DB', 'KAREN_TASKS_DB']) delete env[key];
  let app;
  const cleanup = () => fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  try {
    app = await electron.launch({ args: [path.resolve('.'), '--qa'], env });
    await app.firstWindow();
    const panel = app.windows().find(window => window.url().includes('view=settings'));
    if (!panel) throw new Error('No se abrió el panel de revisión.');
    await panel.waitForSelector('h1');
    await app.evaluate(({ BrowserWindow }) => {
      for (const window of BrowserWindow.getAllWindows()) {
        if (window.webContents.getURL().includes('view=settings')) {
          window.setTitle('Karen · Revisión de interfaz'); window.show(); window.focus();
        } else if (window.webContents.getURL().includes('view=pet')) window.showInactive();
      }
    });
    app.once('close', () => { cleanup(); process.exit(0); });
    console.log(JSON.stringify({ canonicalBuildOpen: true, reviewProfile: true, existingAppPreserved: true }));
  } catch (error) {
    await app?.close().catch(() => {}); cleanup(); throw error;
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
