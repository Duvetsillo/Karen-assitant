// Local acceptance only: existing loopback Gateway/model, disposable Pet profile.
// Keeps the shared main transcript and Core databases untouched. No tool request.
const {_electron:electron,expect}=require('@playwright/test');
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert/strict');
(async()=>{
 const source=path.join(process.env.APPDATA,'karen-desktop-pet');
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'karen-local-chat-'));let app;
 const settings=JSON.parse(fs.readFileSync(path.join(source,'settings.json'),'utf8'));
 fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({...settings,conversationScope:'desktop',routingMode:'manual',mode:'normal',introEnabled:false,voiceEnabled:false,wakeWordEnabled:false,environmentObserve:false,fullscreenHide:false,musicEnabled:false}));
 fs.copyFileSync(path.join(source,'vault.dpapi'),path.join(profile,'vault.dpapi'));
  fs.copyFileSync(path.join(source,'Local State'),path.join(profile,'Local State'));
 const env={...process.env,KAREN_QA_PROFILE:profile};for(const key of['ELECTRON_RUN_AS_NODE','KAREN_CORE_DB','KAREN_TASKS_DB'])delete env[key];
 const errors=[];
 try{
  app=await electron.launch({args:[path.resolve('.'),'--qa','--qa-models'],env});await app.firstWindow();
  await new Promise(resolve=>setTimeout(resolve,700));const panel=app.windows().find(w=>w.url().includes('view=settings'));assert(panel);
  for(const w of app.windows())w.on('pageerror',e=>errors.push(e.message));
  await panel.evaluate(()=>window.karen.connect());
  await expect.poll(()=>panel.evaluate(async()=>(await window.karen.snapshot()).connection.state),{timeout:30000}).toBe('connected');
  const selected=await panel.evaluate(()=>window.karen.selectModel('ollama/gemma3:1b'));
  assert.equal(selected.effective,'ollama/gemma3:1b');assert.equal(selected.sessionKey,'agent:main:karen-desktop');
  const before=await panel.evaluate(async()=>(await window.karen.snapshot()).messages.map(m=>m.id));
  const started=Date.now();await panel.evaluate(()=>window.karen.send('Sin usar herramientas, responde brevemente en español: ¿estás lista para conversar?'));
  await expect.poll(()=>panel.evaluate(async ids=>{const s=await window.karen.snapshot();return s.messages.some(m=>!ids.includes(m.id)&&m.role==='assistant'&&!m.pending&&Boolean(m.text.trim()));},before),{timeout:120000}).toBe(true);
  const outcome=await panel.evaluate(async ids=>{const s=await window.karen.snapshot();const answer=s.messages.find(m=>!ids.includes(m.id)&&m.role==='assistant'&&!m.pending);return {valid:Boolean(answer?.text.trim())&&!/^OpenClaw|LLM request failed/i.test(answer?.text??''),version:s.version};},before);
  assert(outcome.valid,'El Pet recibió un fallo en lugar de una respuesta.');assert.deepEqual(errors,[]);
  const report={...outcome,seconds:Number(((Date.now()-started)/1000).toFixed(2)),transport:'Pet Electron → Gateway real → Ollama local',model:selected.effective,sessionScope:'desktop',temporaryPetProfile:true,coreDatabaseUntouched:true,sharedMainPreserved:true,errors};
  fs.mkdirSync('qa/experience',{recursive:true});fs.writeFileSync('qa/experience/local-chat-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await app?.close().catch(()=>{});fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});}
})().catch(e=>{console.error(e);process.exitCode=1;});
