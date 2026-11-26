const {_electron:electron}=require('@playwright/test');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'karen-polish-'));
 fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({introEnabled:false,voiceEnabled:false,fadeEnabled:true,musicEnabled:false}));
 const env={...process.env,KAREN_QA_PROFILE:profile};delete env.ELECTRON_RUN_AS_NODE;delete env.KAREN_CORE_DB;delete env.KAREN_TASKS_DB;
 let app;const errors=[];const output=path.resolve('qa/polish');fs.mkdirSync(output,{recursive:true});
 try{
 app=await electron.launch({args:[path.resolve('.'),'--qa','--qa-farewell'],env});await app.firstWindow();await delay(1200);
 const panel=app.windows().find(w=>w.url().includes('view=settings'));const pet=app.windows().find(w=>w.url().includes('view=pet'));assert(panel&&pet);
 for(const w of app.windows())w.on('pageerror',e=>errors.push(e.message));await pet.waitForSelector('canvas');
 await app.evaluate(({BrowserWindow})=>{for(const w of BrowserWindow.getAllWindows()){if(w.webContents.getURL().includes('view=settings'))w.hide();else w.showInactive();}});
 for(const scale of [.5,1])for(const shape of ['bubble','panel','ribbon']){
 await panel.evaluate(({shape,scale})=>window.karen.settings({petChatShape:shape,scale}),{shape,scale});
 await app.evaluate(({BrowserWindow})=>{const p=BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=pet'));p.webContents.send('desktop-event',{type:'chat',message:{id:'synthetic',role:'assistant',text:'Una respuesta para leer con calma. 日本語 · ¡Hola! '+ 'contenido largo '.repeat(45)},final:true});});await delay(450);
 const bounds=await pet.locator('.pet-bubble').boundingBox();assert(bounds);const size=pet.viewportSize()||await pet.evaluate(()=>({width:innerWidth,height:innerHeight}));assert(bounds.x>=0&&bounds.y>=0&&bounds.x+bounds.width<=size.width+1&&bounds.y+bounds.height<=size.height+1);
 await pet.screenshot({path:path.join(output,`${shape}-${scale}.png`),omitBackground:true});
 }
 await pet.getByRole('button',{name:'Abrir mensaje',exact:true}).click({force:true});const input=pet.getByRole('textbox',{name:'Mensaje para Karen'});await input.fill('Karen, desactiva los saludos de inicio');await input.press('Shift+Enter');assert((await input.inputValue()).includes('\n'));await input.fill('Karen, desactiva los saludos de inicio');await input.press('Enter');await delay(400);assert(await input.isVisible());assert.equal(await input.inputValue(),'');await pet.screenshot({path:path.join(output,'composer.png'),omitBackground:true});
 await pet.getByRole('button',{name:'Cerrar mensaje',exact:true}).click({force:true});
 await pet.getByLabel('Más opciones de Karen').click({force:true});
 assert(await pet.getByRole('button',{name:'Repetir última respuesta',exact:true}).isVisible());
 await pet.getByLabel('Más opciones de Karen').press('Escape');
 assert(!(await pet.getByRole('button',{name:'Repetir última respuesta',exact:true}).isVisible()));
 await panel.evaluate(()=>window.karen.settings({scale:1,introVoice:false,introSounds:false}));
 const opened=app.waitForEvent('window',{predicate:w=>w.url().includes('view=intro')});
 assert(await panel.evaluate(()=>window.karen.playIntro('awakening')));
 const intro=await opened;await intro.waitForSelector('canvas');await intro.clock.install();await intro.clock.fastForward(700);
 const quality=await intro.locator('canvas').evaluate(c=>({resolution:JSON.parse(c.dataset.textureResolution),bytes:Number(c.dataset.textureSourceBytes)}));
 assert(quality.resolution.face>=7);assert(quality.bytes<=48*1024*1024);
 await intro.screenshot({path:path.join(output,'awakening-eyes.png'),omitBackground:true});
 await intro.clock.fastForward(30000);if(!intro.isClosed())await intro.waitForEvent('close',{timeout:4000});

 assert.equal(JSON.parse(fs.readFileSync(path.join(profile,'settings.json'),'utf8')).petChatShape,'ribbon');
 let farewell=false;await pet.exposeFunction('farewellSeen',()=>{farewell=true;});await pet.evaluate(()=>window.karen.event(e=>{if(e.type==='pet-departure')window.farewellSeen();}));
 const start=Date.now();await app.evaluate(({app})=>{setTimeout(()=>app.quit(),50);});await app.waitForEvent('close',{timeout:4000});app=undefined;assert(farewell);const elapsed=Date.now()-start;assert(elapsed<2500);assert.deepEqual(errors,[]);
 const report={syntheticData:true,variants:6,multiline:true,localSend:true,draftRemainsOpen:true,persistence:true,moreOptions:true,awakeningQuality:quality,farewell:true,quitMs:elapsed,errors};fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await app?.close().catch(()=>{});fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});}
})().catch(e=>{console.error(e);process.exitCode=1;});

