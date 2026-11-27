// Real Windows/WebGL, disposable settings, no model, mic, or Gateway requests.
const { _electron: electron, expect } = require('@playwright/test');
const { createCoreQaProfile } = require('./core-qa-profile.cjs');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const { directory, profile, cleanup } = createCoreQaProfile('karen-native-variants-');
  const core = path.join(directory,'core.sqlite3');
  execFileSync('python',['-c','from conversations import Conversations; import sys; Conversations(sys.argv[1]).current()',core],{cwd:fs.existsSync(path.resolve('../runtime/conversations.py'))?path.resolve('../runtime'):path.resolve('..')});
  const env = {...process.env,KAREN_QA_PROFILE:profile,KAREN_CORE_DB:core};
  delete env.ELECTRON_RUN_AS_NODE;
  const executable = process.env.KAREN_SMOKE_EXECUTABLE;
  const launch = () => electron.launch({...(executable ? {executablePath:executable,args:['--qa']} : {args:[path.resolve('.'),'--qa']}),env});
  let app = await launch();
  const report = { createdUtc:new Date().toISOString(), build:executable?'packaged':'source', rendererErrors:[], styles:[], persisted:false, realIdleClips:[], cpu:[] };
  fs.mkdirSync('qa/variants',{recursive:true});
  async function pages() {
    const panel = app.windows().find(w=>w.url().includes('view=settings')) || await app.waitForEvent('window',{predicate:w=>w.url().includes('view=settings')});
    await panel.waitForSelector('h1');
    const pet = app.windows().find(w=>w.url().includes('view=pet'));
    assert(pet);
    for (const page of app.windows()) page.on('pageerror',e=>report.rendererErrors.push(e.message));
    await pet.waitForSelector('canvas');
    return {panel,pet};
  }
  try {
    let {panel,pet} = await pages();
    report.version = (await panel.evaluate(()=>window.karen.snapshot())).version;
    const settings = values => panel.evaluate(values=>window.karen.settings(values),values);
    await settings({voiceEnabled:false,sttEnabled:false,wakeWordEnabled:false,scale:1,animations:false,particles:false,cursorTracking:false,sleepAfter:3600});
    await panel.keyboard.press('Control+k');await panel.getByRole('searchbox',{name:'Buscar sección'}).fill('Apariencia');await panel.keyboard.press('Enter');
    await expect(panel.getByRole('radio')).toHaveCount(8);
    await settings({showArms:true,showLegs:true});
    await expect(pet.locator('.pet-renderer')).toHaveAttribute('data-arms','false');
    await expect(pet.locator('.pet-renderer')).toHaveAttribute('data-legs','false');
    assert.equal(await panel.getByRole('switch',{name:'Mostrar brazos',exact:true}).count(),0);
    assert.equal(await panel.getByRole('switch',{name:'Mostrar piernas',exact:true}).count(),0);
    report.floatingOnly=true;
    for(const style of ['crystal','cloud','orbit','sprite','bloom','aurora','ember','midnight']) {
      await settings({petStyle:style});
      await expect(pet.locator('.pet-renderer')).toHaveAttribute('aria-label',/sin brazos y sin piernas/);
      await pet.waitForTimeout(250);
      await pet.locator('canvas').screenshot({path:`qa/variants/${style}.png`,omitBackground:true});
      report.styles.push(style);
    }
    for(const scale of [.5,1,2]) {
      await settings({scale});
      await pet.getByRole('button',{name:'Abrir mensaje',exact:true}).focus();
      const fits = await pet.locator('.pet-toolbar').evaluate(node=>{const r=node.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth;});
      assert(fits,`Toolbar must fit scale ${scale}`);
    }
    await settings({scale:1,petStyle:'aurora',showArms:false,showLegs:true,idleActivities:true,idleActivity:'play',idleAfter:15,animations:true,activity:.6});
    await panel.evaluate(()=>window.karen.demo('IDLE'));
    await pet.bringToFront();
    await pet.evaluate(()=>document.activeElement?.blur());
    await pet.mouse.move(-10,-10);
    try {
      await expect.poll(()=>pet.locator('.pet-renderer').getAttribute('data-idle-activity'),{timeout:25000}).toBe('play');
    } catch(error) {
      console.log('Idle diagnostics:',JSON.stringify(await pet.evaluate(async()=>({hidden:document.hidden,renderer:document.querySelector('.pet-renderer').outerHTML.replace(/<canvas.*<\/canvas>/,'CANVAS'),state:document.querySelector('.pet-hit-area')?.getAttribute('aria-label'),snapshot:await window.karen.snapshot()}))));
      console.log('Native visibility:',JSON.stringify(await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().map(w=>({title:w.getTitle(),visible:w.isVisible(),minimized:w.isMinimized()})))));
      await pet.screenshot({path:'qa/variants/idle-failure.png',omitBackground:true});
      throw error;
    }
    await pet.waitForTimeout(2600);
    await pet.locator('canvas').screenshot({path:'qa/variants/idle-play.png',omitBackground:true});
    report.realIdleClips.push('play');
    await panel.evaluate(()=>window.karen.demo('THINKING'));
    await expect(pet.locator('.pet-renderer')).toHaveAttribute('data-idle-activity','none');
    report.yieldsToThinking = true;
    for(const activity of ['stretch','stargaze']) {
      await settings({idleActivity:activity});
      await panel.evaluate(()=>window.karen.demo('IDLE'));
      await expect.poll(()=>pet.locator('.pet-renderer').getAttribute('data-idle-activity'),{timeout:25000}).toBe(activity);
      await pet.waitForTimeout(2600);
      await pet.locator('canvas').screenshot({path:`qa/variants/idle-${activity}.png`,omitBackground:true});
      report.realIdleClips.push(activity);
    }
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=pet')).hide());
    await panel.waitForTimeout(250);
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=pet')).show());
    await expect(pet.locator('.pet-renderer')).toHaveAttribute('data-idle-activity','none');
    report.resumesWithoutOverdueGame = true;
    await pet.emulateMedia({reducedMotion:'reduce'});
    await expect(pet.locator('.pet-renderer')).toHaveAttribute('data-idle-activity','none');
    await expect.poll(async()=>Number(await pet.locator('.pet-renderer').getAttribute('data-render-fps')),{timeout:10000}).toBeLessThanOrEqual(15);
    report.reducedMotion = true;
    await pet.emulateMedia({reducedMotion:'no-preference'});
    await settings({idleActivities:false});
    await pet.waitForTimeout(4000);
    report.idleFps = Number(await pet.locator('.pet-renderer').getAttribute('data-render-fps'));
    await app.evaluate(({app})=>app.getAppMetrics());
    await pet.waitForTimeout(4000);
    report.cpu = await app.evaluate(({app})=>app.getAppMetrics().filter(p=>p.type==='Tab').map(p=>({type:p.type,cpu:p.cpu,memory:p.memory})));
    await app.close();
    app = await launch();
    ({panel,pet}=await pages());
    const restored = (await panel.evaluate(()=>window.karen.snapshot())).settings;
    assert.equal(restored.petStyle,'aurora'); assert.equal(restored.showArms,false);assert.equal(restored.showLegs,false);
    assert.equal(restored.idleActivity,'stargaze');assert.equal(restored.idleActivities,false);
    report.persisted = true;
    assert.deepEqual(report.rendererErrors,[]);
    fs.writeFileSync(`qa/variants/${executable?'packaged':'source'}-results.json`,JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally {
    await app.close(); cleanup();
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
