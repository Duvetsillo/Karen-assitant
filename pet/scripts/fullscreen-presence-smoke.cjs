const {_electron:electron,expect}=require('@playwright/test');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert/strict');
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'karen-fullscreen-'));let app;
 const env={...process.env,KAREN_QA_PROFILE:profile};for(const key of['ELECTRON_RUN_AS_NODE','KAREN_CORE_DB','KAREN_TASKS_DB'])delete env[key];
 fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({introEnabled:false,voiceEnabled:false,musicEnabled:false,fullscreenHide:true,environmentObserve:false,idleActivities:false}));
 const errors=[];const visible=()=>app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=pet')).isVisible());
 try{
  app=await electron.launch({args:[path.resolve('.'),'--qa'],env});await app.firstWindow();
  await new Promise(resolve=>setTimeout(resolve,700));const panel=app.windows().find(w=>w.url().includes('view=settings')),pet=app.windows().find(w=>w.url().includes('view=pet'));assert(panel&&pet);
  for(const w of app.windows())w.on('pageerror',e=>errors.push(e.message));
  await pet.waitForSelector('canvas');await panel.evaluate(()=>window.karen.show());
  await app.evaluate(async({BrowserWindow})=>{const w=new BrowserWindow({width:600,height:400,title:'Karen QA fullscreen fixture'});await w.loadURL('data:text/html,<body style="background:%23181d28;color:white">Pantalla de prueba</body>');w.maximize();w.show();w.focus();});
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.getTitle().includes('fullscreen fixture'));w.show();w.focus();});
  console.log('Activa la ventana «Karen QA fullscreen fixture» para la comprobación nativa de primer plano.');
  await expect.poll(()=>panel.evaluate(async()=>(await window.karen.snapshot()).environment?.fullscreen),{timeout:45000}).toBe(false);
  await expect.poll(visible,{timeout:6000}).toBe(true);
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.getTitle().includes('fullscreen fixture'));w.setFullScreen(true);w.focus();});
  await expect.poll(()=>pet.evaluate(async()=>Boolean((await window.karen.snapshot()).environment?.fullscreen)),{timeout:10000}).toBe(true);
  try{await expect.poll(visible,{timeout:6000}).toBe(false);}catch(error){console.log(JSON.stringify({environment:(await panel.evaluate(()=>window.karen.snapshot())).environment,windows:await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().map(w=>({title:w.getTitle(),visible:w.isVisible(),fullscreen:w.isFullScreen()})))}));throw error;}
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.getTitle().includes('fullscreen fixture'));w.setFullScreen(false);w.show();w.focus();});
  await expect.poll(visible,{timeout:10000}).toBe(true);
  await expect.poll(()=>pet.evaluate(async()=>(await window.karen.snapshot()).environment?.fullscreen),{timeout:5000}).toBe(false);
  assert.equal((await panel.evaluate(()=>window.karen.snapshot())).settings.environmentObserve,false);
  await panel.evaluate(()=>window.karen.hide());await new Promise(resolve=>setTimeout(resolve,1600));assert.equal(await visible(),false);
  assert.deepEqual(errors,[]);const report={nativeWindows:true,realFullscreenWindow:true,maximizedPreserved:true,animatedHide:true,automaticRestore:true,manualHidePreserved:true,environmentObservationRemainsOff:true,errors};
  fs.mkdirSync('qa/experience',{recursive:true});fs.writeFileSync('qa/experience/fullscreen-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await app?.close().catch(()=>{});fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});}
})().catch(e=>{console.error(e);process.exitCode=1;});
