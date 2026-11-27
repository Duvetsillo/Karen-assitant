const { _electron: electron } = require('@playwright/test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { execFileSync, execFile } = require('node:child_process');
const profile = fs.mkdtempSync(path.join(os.tmpdir(),'karen-music-ui-'));
const output = path.resolve('qa/music'); fs.mkdirSync(output,{recursive:true});
const core = path.join(profile,'core.sqlite');
execFileSync('python',['-c','from karen_core2.memory import ContextMemory; import sys; ContextMemory(sys.argv[1])',core], { env:{...process.env,PYTHONPATH:fs.existsSync(path.resolve('../runtime/karen_core2'))?path.resolve('../runtime'):path.resolve('..')},windowsHide:true });
fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({musicEnabled:true,musicHistory:true,musicHoverExpand:false,musicAutoHideSeconds:20,musicPlatforms:['youtube','youtube-music'],introEnabled:false}));
const env={...process.env,KAREN_QA_PROFILE:profile,KAREN_CORE_DB:core}; delete env.ELECTRON_RUN_AS_NODE;delete env.KAREN_TASKS_DB;
const report={source:'Electron y HTTP local reales, metadatos/controles de navegador simulados',errors:[],commands:[],samples:[],gpu:[]};
const client='synthetic-music-browser-client';
let app,panel,mini,token,controller,keepListening=true,timer,gpuTimer,sampling=false;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const sessions=new Map();
const post=async body=>{
 const response=await fetch(`http://127.0.0.1:18796/events?client=${client}`,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify(body)});
 assert.equal(response.status,200);
};
const send=async(tabId,session)=>{sessions.set(tabId,session);await post({type:'session',tabId,session});};
async function browserLoop(){
 while(keepListening){
  try{
   const response=await fetch(`http://127.0.0.1:18796/commands?client=${client}`,{headers:{Authorization:`Bearer ${token}`},signal:controller.signal});
   for(const command of await response.json()){
    const tabId=Number(command.sessionId.split(':').at(-1)),s=sessions.get(tabId);let ok=Boolean(s&&s.trackId===command.trackId);
    if(ok){
     if(command.action==='pause')s.status='paused';else if(command.action==='play')s.status='playing';
     else if(command.action==='next'){s.trackId='qa-next';s.title='Siguiente QA';s.position=0;}
     else if(command.action==='previous'){s.trackId='qa-track';s.title='Canción QA';s.position=0;}
     else if(command.action==='seek')s.position=command.value;else ok=false;
     if(ok){report.commands.push(command.action);await send(tabId,s);}
    }
    await post({type:'result',id:command.id,ok});
   }
  }catch(error){if(keepListening)throw error;}
 }
}
const until=async(predicate,message)=>{for(let i=0;i<100;i++){if(await predicate())return;await delay(100);}throw new Error(message);};
(async()=>{
 try{
  app=await electron.launch({args:[path.resolve('.'),'--qa','--qa-core'],env,timeout:30000});
  await until(()=>app.windows().some(w=>w.url().includes('view=settings')),'No aparece ajustes');
  panel=app.windows().find(w=>w.url().includes('view=settings'));await panel.waitForSelector('h1');
  panel.on('pageerror',e=>report.errors.push(e.message));
  await panel.keyboard.press('Control+k');await panel.getByRole('searchbox',{name:'Buscar sección'}).fill('Música');await panel.keyboard.press('Enter');
  token=await panel.evaluate(()=>window.karen.music.action({action:'pair-browser'}));
  await until(async()=>{try{await post({type:'remove',tabId:5});return true;}catch{return false;}},'No arranca el canal local');
  controller=new AbortController();const listening=browserLoop();void listening.catch(e=>report.errors.push(e.message));
  const song={sessionId:'placeholder',source:'browser',trackId:'qa-track',title:'Canción QA',artist:'Artista QA',album:'Álbum temporal',status:'playing',position:10,duration:180,controls:['play','pause','next','previous','seek'],domain:'www.youtube.com',videoId:'abcdefghijk',category:'Music'};
  await send(5,song);const id=`browser:${client}:5`;
  await panel.evaluate(id=>window.karen.music.action({action:'select',sessionId:id}),id);
  await panel.evaluate(()=>window.karen.music.action({action:'open'}));
  await until(()=>app.windows().some(w=>w.url().includes('view=music')),'No aparece el reproductor');
  mini=app.windows().find(w=>w.url().includes('view=music'));mini.on('pageerror',e=>report.errors.push(e.message));
  await mini.getByRole('heading',{name:'Canción QA',exact:true}).waitFor();
  assert.equal(await mini.getByLabel('Volumen de esta sesión').count(),0);
  assert.match(await mini.evaluate(()=>window.karen.snapshot().then(()=>'',e=>e.message)),/Origen no autorizado/);
  const bounds=await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=music'));return {bounds:w.getBounds(),focused:w.isFocused()};});
  assert(bounds.bounds.height<=100);assert.equal(bounds.focused,false);report.compactBounds=bounds.bounds;report.openWithoutFocus=true;
  await delay(250);await mini.screenshot({path:path.join(output,'mini-player.png'),omitBackground:true});
  await assert.rejects(()=>panel.evaluate(()=>window.karen.music.layout(true)),/Origen de cápsula no autorizado/);
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=music'));w.show();w.focus();});
  await mini.getByRole('button',{name:'Expandir reproductor',exact:true}).click();
  await until(async()=>await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=music')).getBounds().height)>100,'No se expande la cápsula');
  await delay(250);assert(await mini.evaluate(()=>document.querySelector('.music-capsule').getBoundingClientRect().bottom<=innerHeight+1));await mini.screenshot({path:path.join(output,'mini-player-expanded.png'),omitBackground:true});
  await mini.getByRole('button',{name:'Pausar música',exact:true}).click();await mini.getByRole('button',{name:'Reproducir música',exact:true}).waitFor();
  await mini.getByRole('button',{name:'Reproducir música',exact:true}).click();await mini.getByRole('button',{name:'Pausar música',exact:true}).waitFor();
  await mini.getByRole('button',{name:'Siguiente canción',exact:true}).click();await mini.getByRole('heading',{name:'Siguiente QA',exact:true}).waitFor();
  await mini.getByRole('button',{name:'Canción anterior',exact:true}).click();await mini.getByRole('heading',{name:'Canción QA',exact:true}).waitFor();
  await mini.getByRole('slider',{name:'Posición de reproducción'}).fill('42');
  await until(()=>report.commands.includes('seek'),'Seek no confirmado');
  await panel.evaluate(()=>window.karen.send('Karen, me gusta esta canción'));
  assert.equal((await panel.evaluate(()=>window.karen.music.history()))[0].preference,1);
  await panel.evaluate(()=>window.karen.send('Karen, no me gusta esta canción'));
  await panel.evaluate(()=>window.karen.send('Karen, recuerda esta canción'));
  assert.equal((await panel.evaluate(()=>window.karen.music.history()))[0].preference,-1);
  for(const title of ['Gameplay QA','Tutorial QA','Podcast QA','Vídeo ambiguo QA']){
   await send(8,{...song,trackId:'rejected',title,category:title.includes('ambiguo')?'Gaming':'Music'});
   assert(!(await panel.evaluate(()=>window.karen.music.snapshot())).sessions.some(s=>s.title===title));
  }
  await send(6,{...song,trackId:'platform-change',title:'YouTube Music QA',domain:'music.youtube.com',category:'Music'});
  await send(7,{...song,trackId:'other-session',title:'Segunda sesión QA',domain:'music.youtube.com',category:'Music'});
  await mini.getByLabel('Sesión multimedia').selectOption(`browser:${client}:7`);
  assert.equal((await mini.evaluate(()=>window.karen.music.snapshot())).activeId,`browser:${client}:7`);
  timer=setInterval(async()=>{if(sampling)return;sampling=true;try{report.samples.push(await app.evaluate(({app})=>app.getAppMetrics().map(m=>({type:m.type,cpu:m.cpu.percentCPUUsage,workingSetKB:m.memory.workingSetSize}))));}finally{sampling=false;}},500);
  gpuTimer=setInterval(()=>execFile('nvidia-smi',['--query-gpu=utilization.gpu,memory.used','--format=csv,noheader,nounits'],{windowsHide:true,timeout:2000},(e,out)=>{if(!e)report.gpu.push(out.trim());}),1500);
  await delay(7000);
  await mini.getByRole('button',{name:'Anclar reproductor'}).click();
  assert.equal((await panel.evaluate(()=>window.karen.snapshot())).settings.musicPlayerPinned,true);
  await panel.evaluate(()=>window.karen.settings({musicAutoHideSeconds:.25}));
  await send(7,{...sessions.get(7),status:'paused'});
  await until(()=>app.evaluate(({BrowserWindow})=>!BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=music')).isVisible()),'La cápsula no se oculta al pausar');report.pauseAutoHide=true;
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=settings'));w.show();w.focus();});
  await send(7,{...sessions.get(7),status:'playing'});await delay(3000);
  report.autoResumeShown=await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=music')).isVisible());
  if(!report.autoResumeShown){report.resumeGuardedByDesktop=true;await panel.evaluate(()=>window.karen.music.action({action:'open'}));}
  await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=music'));w.show();w.focus();});
  await mini.getByRole('button',{name:'Cerrar reproductor'}).click();
  for(const tabId of [5,6,7,8])await post({type:'remove',tabId});
  await panel.evaluate(()=>window.karen.music.action({action:'clear-history'}));
  assert.deepEqual(await panel.evaluate(()=>window.karen.music.history()),[]);
  keepListening=false;controller.abort();await listening;
  await panel.evaluate(()=>window.karen.settings({musicEnabled:false,musicCommentProbability:.2,musicCooldownMinutes:40}));
  const saved=JSON.parse(fs.readFileSync(path.join(profile,'settings.json'),'utf8'));assert.equal(saved.musicCommentProbability,.2);assert.equal(saved.musicCooldownMinutes,40);
  report.controls=true;report.history=true;report.multipleSessions=true;report.filtering=true;report.preferencesPersisted=true;report.resourcesStopped=true;
  assert.deepEqual(report.errors,[]);console.log(JSON.stringify({controls:true,history:true,multipleSessions:true,filtering:true,errors:[]}));
 }catch(error){report.failure=error.stack;console.error(error);process.exitCode=1;}
 finally{
  keepListening=false;controller?.abort();clearInterval(timer);clearInterval(gpuTimer);await app?.close().catch(()=>{});
  fs.writeFileSync(path.join(output,'ui-metrics.json'),JSON.stringify(report,null,2));fs.rmSync(profile,{recursive:true,force:true});
 }
})();
