// Read-only acceptance against the user's already-playing Spotify session.
// Uses a temporary QA profile, never the user's settings, history or Core DB.
const { _electron: electron } = require('@playwright/test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(find, message) {
  for (let i = 0; i < 100; i++) { const value = await find(); if (value) return value; await delay(100); }
  throw new Error(message);
}
(async () => {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'karen-spotify-readonly-'));
  fs.writeFileSync(path.join(profile, 'settings.json'), JSON.stringify({
    musicEnabled: true, musicPlatforms: ['spotify'], musicHistory: false,
    musicComments: false, voiceEnabled: false, introEnabled: false,
  }));
  const env = { ...process.env, KAREN_QA_PROFILE: profile };
  delete env.ELECTRON_RUN_AS_NODE; delete env.KAREN_CORE_DB; delete env.KAREN_TASKS_DB;
  let app, keepAlive = false;
  try {
    app = await electron.launch({ args: [path.resolve('.'), '--qa'], env, timeout: 30000 });
    const panel = await until(() => app.windows().find(w => w.url().includes('view=settings')), 'No aparece la interfaz QA.');
    await panel.waitForSelector('h1');
    const song = await until(async () => {
      const snapshot = await panel.evaluate(() => window.karen.music.snapshot());
      return snapshot.sessions.find(s => s.platform === 'spotify' && s.status === 'playing');
    }, 'No hay una canción de Spotify confirmada en reproducción.');
    const settings = (await panel.evaluate(() => window.karen.snapshot())).settings;
    assert.equal(settings.musicHistory, false); assert.equal(settings.musicComments, false);
    await panel.evaluate(() => window.karen.music.action({ action: 'open' }));
    const mini = await until(() => app.windows().find(w => w.url().includes('view=music')), 'No aparece el reproductor.');
    await mini.getByRole('heading', { name: song.title, exact: true }).waitFor();
    assert(await mini.getByRole('button', { name: 'Pausar música', exact: true }).isEnabled());
    const rendered = await mini.evaluate(() => ({
      title: document.querySelector('.music-track h2')?.textContent,
      artist: document.querySelector('.music-track p')?.textContent,
      cover: Boolean(document.querySelector('.music-art img')),
    }));
    assert.equal(rendered.title, song.title); assert.equal(rendered.artist, song.artist);
    const report = {
      spotifyDesktopReal: true, gsmtcDetected: true, classifierRecognized: true,
      miniPlayerRendered: true, coverAvailable: rendered.cover,
      historyEnabled: false, commentsEnabled: false, playbackCommandsSent: 0,
      ...(process.argv.includes('--show-track') ? { track: { title: song.title, artist: song.artist } } : {}),
    };
    if (process.argv.includes('--keep-open')) {
      await app.evaluate(({ BrowserWindow }) => {
        for (const window of BrowserWindow.getAllWindows()) {
          const url = window.webContents.getURL();
          if (url.includes('view=settings')) window.hide();
          else if (url.includes('view=pet') || url.includes('view=music')) window.showInactive();
        }
      });
      keepAlive = true; report.keptOpen = true;
      app.once('close', () => {
        fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
        process.exit(0);
      });
    }
    console.log(JSON.stringify(report));
  } finally {
    if (!keepAlive) {
      await app?.close().catch(() => {});
      fs.rmSync(profile, { recursive: true, force: true });
    }
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
