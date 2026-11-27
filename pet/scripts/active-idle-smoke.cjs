// Real elapsed time: the old 60-second sleep threshold must not stop the clips.
const {_electron:electron}=require('@playwright/test');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert/strict');
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'karen-active-idle-'));let app;
 fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({introEnabled:false,voiceEnabled:false,wakeWordEnabled:false,musicEnabled:false,fullscreenHide:false,environmentObserve:false,sleepAfter:0,idleAfter:15,idleActivities:true,idleActivity:'variety',activity:1}));
 const env={...process.env,KAREN_QA_PROFILE:profile};for(const key of['ELECTRON_RUN_AS_NODE','KAREN_CORE_DB','KAREN_TASKS_DB'])delete env[key];
 try{
  app=await electron.launch({args:[path.resolve('.'),'--qa'],env});await app.firstWindow();await new Promise(r=>setTimeout(r,700));
  const pet=app.windows().find(w=>w.url().includes('view=pet')),panel=app.windows().find(w=>w.url().includes('view=settings'));assert(pet&&panel);
  const errors=[];pet.on('pageerror',error=>errors.push(error.message));await pet.waitForSelector('canvas');
  await app.evaluate(({BrowserWindow})=>{for(const w of BrowserWindow.getAllWindows()){if(w.webContents.getURL().includes('view=settings'))w.hide();else{w.show();w.focus();}}});
  await pet.evaluate(()=>{window.__idleCheck={clips:[],states:[]};const node=document.querySelector('.pet-renderer');const capture=()=>{const clip=node.dataset.idleActivity,state=node.dataset.visualState;if(clip&&clip!=='none'&&!window.__idleCheck.clips.includes(clip))window.__idleCheck.clips.push(clip);if(state&&!window.__idleCheck.states.includes(state))window.__idleCheck.states.push(state);};new MutationObserver(capture).observe(node,{attributes:true});capture();});
  await new Promise(resolve=>setTimeout(resolve,76000));
  const result=await pet.evaluate(()=>window.__idleCheck);
  assert(!result.states.includes('SLEEPING'));assert(result.clips.length>=2,'Debe alternar varias actividades sin quedarse dormida.');
  const saved=(await panel.evaluate(()=>window.karen.snapshot())).settings;assert.equal(saved.sleepAfter,0);
  assert.equal(JSON.parse(fs.readFileSync(path.join(profile,'settings.json'),'utf8')).sleepAfter,0);assert.deepEqual(errors,[]);
  const report={nativeElectron:true,realSeconds:76,noAutomaticSleep:true,persisted:true,clips:result.clips,states:result.states,errors};
  fs.mkdirSync('qa/experience',{recursive:true});fs.writeFileSync('qa/experience/active-idle-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await app?.close().catch(()=>{});fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});}
})().catch(error=>{console.error(error);process.exitCode=1;});
