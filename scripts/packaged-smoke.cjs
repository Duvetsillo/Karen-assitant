const { _electron } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
(async () => {
  const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE;
  const app = await _electron.launch({ executablePath:path.resolve('release/win-unpacked/Karen Desktop Pet.exe'),args:['--qa','--settings'],env,timeout:30000 });
  const errors=[];
  const attach=w=>w.on('pageerror',error=>errors.push(error.message));
  app.on('window',attach);app.windows().forEach(attach);
  try {
    await new Promise(resolve=>setTimeout(resolve,1500));
    const packaged=await app.evaluate(({app})=>({packaged:app.isPackaged,path:app.getAppPath(),version:app.getVersion()}));
    assert(packaged.packaged&&packaged.path.endsWith('app.asar'));
    const panel=app.windows().find(w=>w.url().includes('view=settings'));
    const pet=app.windows().find(w=>w.url().includes('view=pet'));
    assert(panel&&pet);await pet.waitForSelector('canvas');
    const snapshot=await panel.evaluate(()=>window.karen.snapshot());
    assert(snapshot.native);assert(!await pet.locator('.error-banner').count());
    await panel.getByRole('button',{name:'Apariencia',exact:true}).click();
    await panel.screenshot({path:'qa/packaged-settings.png'});
    await pet.screenshot({path:'qa/packaged-pet.png',omitBackground:true});
    await panel.evaluate(()=>window.karen.settings({lowPower:true}));
    await panel.close();
    await app.evaluate(({app})=>app.getAppMetrics());
    await new Promise(resolve=>setTimeout(resolve,1800));
    const metrics=await app.evaluate(({app})=>app.getAppMetrics().map(m=>({type:m.type,cpu:m.cpu.percentCPUUsage,workingSetKB:m.memory.workingSetSize})));
    const result={...packaged,rendererErrors:errors,lowPowerMetricsPanelClosed:metrics};
    assert.equal(errors.length,0);
    fs.writeFileSync('qa/packaged-results.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  } finally { await app.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
