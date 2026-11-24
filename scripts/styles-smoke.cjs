const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { createCoreQaProfile } = require('./core-qa-profile.cjs');

(async () => {
  fs.mkdirSync('qa', {recursive:true});
  const {directory,profile,cleanup} = createCoreQaProfile('karen-native-styles-');
  const core = path.join(directory,'core.sqlite3');
  execFileSync('python',['-c','from conversations import Conversations; import sys; Conversations(sys.argv[1]).current()',core],{cwd:path.resolve('..')});
  const env = {...process.env,KAREN_QA_PROFILE:profile,KAREN_CORE_DB:core}; delete env.ELECTRON_RUN_AS_NODE;
  const launch = () => electron.launch({args:[path.resolve('.'), '--qa'], env});
  let app = await launch();
  const errors = [], frames = [];
  try {
    await app.firstWindow();
    let panel = app.windows().find(p => p.url().includes('view=settings')) || await app.waitForEvent('window', {predicate:p=>p.url().includes('view=settings')});
    for (const page of app.windows()) page.on('pageerror', e => errors.push(e.stack || e.message));
    await panel.waitForSelector('h1');
    await panel.evaluate(() => window.karen.settings({animations:false,particles:false,cursorTracking:false,voiceEnabled:false,wakeWordEnabled:false,scale:1}));
    await app.evaluate(({BrowserWindow}) => {
      BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('view=pet')).hide();
      BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('view=settings')).focus();
    });
    await panel.bringToFront();
    await panel.getByRole('button', {name:'Apariencia', exact:true}).click();
    const preview = panel.locator('.preview-window canvas');
    await preview.waitFor();
    for (const [style, name] of [['crystal','Cristal'], ['cloud','Nube'], ['orbit','Órbita'], ['sprite','Lucero'], ['bloom','Flor'], ['aurora','Aurora'], ['ember','Ámbar'], ['midnight','Nocturna']]) {
      await panel.getByRole('radio', {name:new RegExp(name)}).check();
      await expect.poll(async () => (await panel.evaluate(() => window.karen.snapshot())).settings.petStyle).toBe(style);
      await panel.getByRole('img', {name:new RegExp(`Karen, estilo ${name},`)}).waitFor();
      await panel.waitForTimeout(400);
      for (const state of ['IDLE','LISTENING','THINKING','SPEAKING','HAPPY','LAUGHING','ANGRY','SAD','SURPRISED','PROUD','CURIOUS','CONFUSED','ERROR','SLEEPING','DRAGGING']) {
        await panel.evaluate(state => window.karen.demo(state), state);
        await panel.waitForTimeout(style === 'crystal' && ['LAUGHING','ANGRY','SAD','SURPRISED','PROUD','CURIOUS'].includes(state) ? 350 : 100);
        if (style === 'crystal' && ['LAUGHING','ANGRY','SAD','SURPRISED','PROUD','CURIOUS'].includes(state))
          await preview.screenshot({path:`qa/expression-${state.toLowerCase()}.png`,omitBackground:true});
      }
      await panel.evaluate(() => window.karen.demo('IDLE'));
      await panel.waitForTimeout(300);
      frames.push(await preview.screenshot({path:`qa/style-${style}.png`,omitBackground:true}));
    }
    assert(!frames[0].equals(frames[1]) && !frames[1].equals(frames[2]));
    // Native radio semantics: arrow keys switch and preserve focus.
    await panel.getByRole('radio', {name:/Órbita/}).focus();
    await panel.keyboard.press('ArrowLeft');
    await expect(panel.getByRole('radio', {name:/Nube/})).toBeChecked();
    await panel.emulateMedia({reducedMotion:'reduce'});
    await panel.screenshot({path:'qa/styles-settings-160.png'});
    await panel.getByRole('button', {name:'Conversación',exact:true}).click();
    await expect(panel.getByLabel('Modelo de IA', {exact:true})).toBeDisabled();
    await panel.screenshot({path:'qa/model-disconnected-160.png'});
    await app.close();
    app = await launch(); await app.firstWindow();
    panel = app.windows().find(p => p.url().includes('view=settings')) || await app.waitForEvent('window', {predicate:p=>p.url().includes('view=settings')});
    await panel.waitForSelector('h1');
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).settings.petStyle, 'cloud');
    assert.deepEqual(errors, []);
    const report = {styles:['crystal','cloud','orbit','sprite','bloom','aurora','ember','midnight'],statesPerStyle:15,keyboard:true,persisted:'cloud',reducedMotion:true,disconnectedModel:true,errors};
    fs.writeFileSync('qa/styles-160.json',JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally {await app.close();cleanup();}
  process.exit(0);
})().catch(e => {console.error(e);process.exit(1)});
