const { _electron: electron } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const env = {...process.env};
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({args:[path.resolve('.'),'--qa'],env});
  try {
    const panel = app.windows().find(page => page.url().includes('view=settings')) ||
      await app.waitForEvent('window',{predicate:page=>page.url().includes('view=settings')});
    const sources = await panel.evaluate(() => window.karen.captureSources());
    const source = sources.find(item => item.canPoint);
    assert(source,'No se encontró una pantalla para la prueba');
    await panel.evaluate(() => { window.__pointEvents=[]; window.karen.event(event => { if(event.type==='pointing') window.__pointEvents.push(event.side); }); });
    await panel.evaluate(id => window.karen.pointAt(id,0.5,0.5),source.id);
    await new Promise(resolve => setTimeout(resolve,500));
    const overlay = await app.evaluate(({BrowserWindow}) => {
      const window = BrowserWindow.getAllWindows().find(item => item.webContents.getURL().startsWith('data:text/html'));
      return {exists:Boolean(window),top:window?.isAlwaysOnTop(),visible:window?.isVisible(),bounds:window?.getBounds()};
    });
    assert(overlay.exists,'No se abrió la marca de señalamiento');
    assert(overlay.top,JSON.stringify(overlay));
    assert((await panel.evaluate(() => window.__pointEvents)).some(side => side === -1 || side === 1),'Karen no levantó la mano para señalar');
    await panel.evaluate(() => window.karen.stopPointing());
    assert.equal(await app.evaluate(({BrowserWindow}) => BrowserWindow.getAllWindows()
      .filter(window => window.webContents.getURL().startsWith('data:text/html')).length),0);
    assert.equal((await panel.evaluate(() => window.__pointEvents)).at(-1),0);
    console.log(JSON.stringify({screen:source.name,overlay:true,stopped:true}));
  } finally {await app.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
