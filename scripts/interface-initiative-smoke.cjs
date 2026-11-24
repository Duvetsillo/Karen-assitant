// Real Electron/WebGL/IPC on Windows. Presence, clock and task rows are controlled fixtures.
// Optional voice mode performs real local Qwen synthesis with muted playback. No microphone or Gateway.
const {_electron:electron,expect}=require('@playwright/test');
const {createCoreQaProfile}=require('./core-qa-profile.cjs');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const qa=createCoreQaProfile('karen-native-initiative-');
  const core=path.join(qa.directory,'core.sqlite3'),tasks=path.join(qa.directory,'tasks.sqlite3');
  execFileSync('python',['-c',"from conversations import Conversations; import sqlite3,sys; Conversations(sys.argv[1]).current(); d=sqlite3.connect(sys.argv[2]); d.executescript(\"CREATE TABLE task_jobs(id TEXT,status TEXT,cursor INTEGER,created_at TEXT,updated_at TEXT,cancel_requested INTEGER); CREATE TABLE task_steps(task_id TEXT,ordinal INTEGER,tool TEXT,permission TEXT,status TEXT); INSERT INTO task_jobs VALUES ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','running',0,'2026-11-02','2026-11-02T00:00:00',0);\"); d.commit()",core,tasks],{cwd:path.resolve('..')});
  fs.writeFileSync(path.join(qa.profile,'settings.json'),JSON.stringify({sttEnabled:false,wakeWordEnabled:false,voiceEnabled:false,petStyle:'aurora',cursorTracking:false,initiativeQuietStart:0,initiativeQuietEnd:0,sleepAfter:3600}));
  const env={...process.env,KAREN_QA_PROFILE:qa.profile,KAREN_CORE_DB:core,KAREN_TASKS_DB:tasks,KAREN_PROJECT_ROOT:path.resolve('..')};delete env.ELECTRON_RUN_AS_NODE;
  const executable=process.env.KAREN_SMOKE_EXECUTABLE;
  const launch=()=>electron.launch({...(executable?{executablePath:executable,args:['--qa','--qa-core']}:{args:[path.resolve('.'),'--qa','--qa-core']}),env});
  let app=await launch();
  const report={at:new Date().toISOString(),build:executable?'packaged':'source',simulations:['presence','main-process clock offset','task database fixture'],rendererErrors:[],layout:[],voice:false};
  const output='qa/initiative';fs.mkdirSync(output,{recursive:true});
  async function close(){
    const child=app.process(),closing=app.close();
    let timer;
    try{
      const result=await Promise.race([closing.then(()=>true),new Promise(r=>{timer=setTimeout(()=>r(false),12000);})]);
      if(!result){
        if(child.exitCode!==0)throw new Error('The QA Electron process did not exit cleanly');
        // On Windows a detached TTS child can retain inherited pipe handles after
        // Electron has exited. Release only this test runner's ended-process streams.
        child.stdout?.destroy();child.stderr?.destroy();
        report.endedProcessPipesReleased=true;
      }
    }finally{clearTimeout(timer);}
  }
  async function pages(){
    const panel=app.windows().find(w=>w.url().includes('view=settings'))||await app.waitForEvent('window',{predicate:w=>w.url().includes('view=settings')});
    const pet=app.windows().find(w=>w.url().includes('view=pet'))||await app.waitForEvent('window',{predicate:w=>w.url().includes('view=pet')});
    for(const page of [panel,pet])page.on('pageerror',e=>report.rendererErrors.push(e.stack));
    await panel.waitForSelector('h1');await pet.waitForSelector('canvas');
    await app.evaluate(({powerMonitor})=>{powerMonitor.getSystemIdleTime=()=>0;powerMonitor.getSystemIdleState=()=> 'active';});
    return {panel,pet};
  }
  try{
    let {panel,pet}=await pages();
    report.version=(await panel.evaluate(()=>window.karen.snapshot())).version;
    await pet.waitForTimeout(1000);
    await pet.screenshot({path:`${output}/startup.png`,omitBackground:true});
    await panel.screenshot({path:`${output}/conversation.png`});
    await pet.evaluate(()=>{window.__qaCanvas=document.querySelector('canvas');window.__qaCursors=0;window.karen.event(e=>{if(e.type==='cursor')window.__qaCursors++;});});
    await pet.waitForTimeout(400);
    assert(await pet.evaluate(()=>window.__qaCursors>0),'Native hit testing must receive cursor positions with eye tracking off');
    report.hitTestingWithoutGaze=true;
    await panel.getByRole('button',{name:'Apariencia',exact:true}).click();
    const switchStart=performance.now();
    for(const style of ['midnight','ember','cloud','aurora','sprite','orbit','bloom','crystal','aurora'])
      await panel.evaluate(style=>window.karen.settings({petStyle:style}),style);
    report.nineStyleUpdatesIpcMs=performance.now()-switchStart;
    await pet.waitForTimeout(500);
    assert(await pet.evaluate(()=>window.__qaCanvas===document.querySelector('canvas')),'Style changes must keep one renderer');
    report.singleRenderer=true;
    await panel.screenshot({path:`${output}/appearance.png`});
    for(const width of [1180,900,820]){
      await app.evaluate(({BrowserWindow},width)=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=settings')).setSize(width,740),width);
      await panel.waitForTimeout(200);
      for(const tab of ['Conversación','Iniciativa','Apariencia']){
        await panel.getByRole('button',{name:tab,exact:true}).click();
        assert(await panel.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`No document overflow: ${tab} ${width}`);
        if(tab==='Conversación')await expect(panel.getByRole('button',{name:'Enviar mensaje',exact:true})).toBeInViewport();
        report.layout.push({tab,width,overflow:false});
      }
    }
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=settings')).setSize(1180,820));
    await panel.getByRole('button',{name:'Iniciativa',exact:true}).click();
    await panel.getByRole('switch',{name:'Karen puede iniciar conversación',exact:true}).click();
    await panel.getByRole('button',{name:'Sugerir ahora',exact:true}).click();
    await expect(panel.locator('.initiative-notice')).toHaveCount(1);
    await expect(pet.locator('.pet-initiative')).toHaveCount(1);
    const first=await panel.evaluate(()=>window.karen.snapshot());
    assert.equal(first.initiative.todayCount,1);
    report.manualNotice=true;
    await panel.screenshot({path:`${output}/initiative.png`});
    await pet.screenshot({path:`${output}/suggestion-pet.png`,omitBackground:true});
    await panel.evaluate(()=>window.karen.settings({scale:.5}));
    await pet.waitForTimeout(200);
    const smallNotice=await pet.locator('.pet-initiative').boundingBox();
    assert(smallNotice.height<=90,'Small pet suggestion must leave its face visible');
    assert(await pet.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Small pet notice must not overflow');
    report.halfScaleNotice=true;
    await pet.screenshot({path:`${output}/suggestion-pet-small.png`,omitBackground:true});
    await panel.evaluate(()=>window.karen.settings({scale:1}));
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=settings')).setSize(820,620));
    await panel.getByRole('button',{name:'Conversación',exact:true}).click();
    await expect(panel.getByRole('button',{name:'Enviar mensaje',exact:true})).toBeInViewport();
    await panel.locator('.conversation-model summary').click();
    await expect(panel.getByRole('button',{name:'Enviar mensaje',exact:true})).toBeInViewport();
    report.minimumWindowComposer=true;
    await panel.screenshot({path:`${output}/compact-conversation.png`});
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=settings')).setSize(1180,820));
    await panel.getByRole('button',{name:'Iniciativa',exact:true}).click();
    await panel.getByRole('button',{name:'Silencio durante 1 h',exact:true}).click();
    await expect(pet.locator('.pet-initiative')).toHaveCount(0);
    assert((await panel.evaluate(()=>window.karen.snapshot())).initiative.snoozedUntil>Date.now());
    report.snooze=true;
    await panel.getByRole('button',{name:'Reanudar iniciativa',exact:true}).click();
    // Change a previously observed running task; native timer reads the actual SQLite fixture.
    await app.evaluate(()=>{global.__qaRealNow=Date.now;global.__qaOffset=46*60000;Date.now=()=>global.__qaRealNow()+global.__qaOffset;});
    execFileSync('python',['-c',"import sqlite3,sys; d=sqlite3.connect(sys.argv[1]); d.execute(\"UPDATE task_jobs SET status='failed',updated_at='2026-11-02T01:00:00'\"); d.commit()",tasks]);
    // Establish task observation if the first periodic sample has not happened yet.
    // Main now explicitly samples the baseline when initiative is enabled.
    await expect.poll(async()=> (await panel.evaluate(()=>window.karen.snapshot())).initiative.notices.some(n=>n.kind==='task'),{timeout:35000}).toBe(true);
    const state=await panel.evaluate(()=>window.karen.snapshot());
    assert(state.initiative.notices.at(-1).command==='/tareas estado '+'a'.repeat(32));
    report.automaticTaskNotice=true;
    await app.evaluate(()=>{Date.now=global.__qaRealNow;});
    await panel.getByRole('button',{name:'Revisar tarea',exact:true}).click();
    await expect(panel.getByRole('textbox',{name:'Mensaje para Karen',exact:true})).toHaveValue('/tareas estado '+'a'.repeat(32));
    await panel.getByRole('button',{name:'Enviar mensaje',exact:true}).click();
    await expect(panel.getByRole('log',{name:'Conversación con Karen'})).toContainText('failed');
    report.taskReadRequiresSend=true;
    await panel.getByRole('combobox',{name:'Modo de Karen',exact:true}).selectOption('do_not_disturb');
    await assert.rejects(panel.evaluate(()=>window.karen.initiative('now')),/libre|visible|modo/);
    report.doNotDisturb=true;
    await panel.getByRole('combobox',{name:'Modo de Karen',exact:true}).selectOption('normal');
    if(process.env.KAREN_QA_INITIATIVE_VOICE==='1'){
      await panel.evaluate(()=>window.karen.settings({voiceEnabled:true,initiativeSpeak:true,ttsEngine:'local',voiceRoot:'C:/karen',volume:0}));
      await pet.evaluate(()=>{window.__qaPlayed=0;const play=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.__qaPlayed++;return play.call(this);};});
      await panel.evaluate(()=>window.karen.initiative('now'));
      await expect.poll(()=>pet.evaluate(()=>window.__qaPlayed),{timeout:150000}).toBeGreaterThan(0);
      await panel.evaluate(()=>window.karen.initiative('snooze'));
      await expect.poll(async()=>(await panel.evaluate(()=>window.karen.snapshot())).capture.phase).toBe('idle');
      report.voice={engine:'local Qwen',playback:'muted real audio',microphone:false,cancelled:true};
    }
    const before=(await panel.evaluate(()=>window.karen.snapshot())).initiative;
    fs.writeFileSync(`${output}/${executable?'packaged':'source'}-results.json`,JSON.stringify(report,null,2));
    await close();app=await launch();({panel,pet}=await pages());
    const after=(await panel.evaluate(()=>window.karen.snapshot())).initiative;
    assert.equal(after.notices.length,before.notices.length);assert.equal(after.lastAt,before.lastAt);
    report.persistent=true;
    await expect(pet.locator('canvas')).toHaveCount(1);
    assert.deepEqual(report.rendererErrors,[]);
  }finally{
    fs.writeFileSync(`${output}/${executable?'packaged':'source'}-results.json`,JSON.stringify(report,null,2));
    await close();qa.cleanup();
  }
  console.log(JSON.stringify(report,null,2));
  process.exit(0);
})().catch(e=>{console.error(e);process.exitCode=1;});
