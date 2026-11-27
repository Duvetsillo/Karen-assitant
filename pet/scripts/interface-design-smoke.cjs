const {_electron:electron}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const sections=['Presencia','Centro de control','Memoria','Obsidian','Herramientas','Personalidad','Privacidad','Conversación','Iniciativa','Música','Apariencia','Comportamiento','Voz','OpenClaw','Percepción','Sistema','Diagnóstico'];
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'karen-interface-'));
 fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({introEnabled:false,voiceEnabled:false,musicEnabled:false}));
 const env={...process.env,KAREN_QA_PROFILE:profile};for(const key of ['ELECTRON_RUN_AS_NODE','KAREN_CORE_DB','KAREN_TASKS_DB'])delete env[key];
 const output=path.resolve('qa/interface-design/after');fs.mkdirSync(output,{recursive:true});let app;const errors=[],checks=[];
 try{
  app=await electron.launch({args:[path.resolve('.'),'--qa'],env});await app.firstWindow();await delay(700);
  const panel=app.windows().find(w=>w.url().includes('view=settings'));assert(panel);await panel.waitForSelector('h1');
  for(const w of app.windows())w.on('pageerror',e=>errors.push(e.message));
  const resize=async(width,height)=>{await app.evaluate(({BrowserWindow},{width,height})=>{for(const w of BrowserWindow.getAllWindows()){if(w.webContents.getURL().includes('view=pet'))w.hide();else if(w.webContents.getURL().includes('view=settings')){w.setBounds({x:40,y:40,width,height});w.show();w.focus();}}},{width,height});await delay(150);};
  const select=async name=>{await panel.keyboard.press('Control+k');const field=panel.getByRole('searchbox',{name:'Buscar sección'});await field.fill(name);await field.press('Enter');await panel.getByRole('heading',{name:name==='Presencia'?'Karen':name,exact:true,level:1}).waitFor();};
  for(const [width,height] of [[1120,800],[820,640]]){
   await resize(width,height);
   for(const name of sections){
    await select(name);await delay(80);
    const overflow=await panel.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert(!overflow,`${name}: desbordamiento de ventana`);
    if(['Presencia','Centro de control','Conversación','Música','Apariencia','Voz'].includes(name))await panel.screenshot({path:path.join(output,`${name}-${width}.png`)});
   }
   checks.push({width,height,navigated:sections.length,noWindowOverflow:true});
  }
  await resize(1120,800);await panel.keyboard.press('Control+k');const search=panel.getByRole('searchbox',{name:'Buscar sección'});await search.fill('musica');assert.equal(await panel.getByRole('navigation').getByRole('button').count(),1);await search.press('Enter');await panel.getByRole('heading',{name:'Música',exact:true,level:1}).waitFor();
  await panel.keyboard.press('Control+k');await search.fill('ninguna-seccion');await panel.getByText('No hay secciones con ese nombre.').waitFor();await search.press('Escape');assert.equal(await panel.getByRole('navigation').getByRole('button').count(),5);
  await select('Centro de control');assert.equal(await panel.locator('.control-directory > button').count(),13);
  await select('Memoria');await panel.getByRole('button',{name:'Consultar memoria',exact:true}).click();await panel.getByRole('textbox',{name:'Mensaje para Karen'}).waitFor();assert.equal(await panel.getByRole('textbox',{name:'Mensaje para Karen'}).inputValue(),'/memoria');
  await select('Conversación');const editor=panel.getByRole('textbox',{name:'Mensaje para Karen'});await editor.fill('Un borrador que conserva mi idea.');await select('Apariencia');await select('Conversación');assert.equal(await editor.inputValue(),'Un borrador que conserva mi idea.');await editor.fill('');
  const sample='Una respuesta clara para seguir trabajando.\n\n- Primer paso\n- Segundo paso\n\n```js\nconst saludo = "Hola Karen";\n'+ 'x'.repeat(250)+'\n```\n\nTexto seguro: <img src=x onerror=alert(1)> · 日本語 · ¡Hola!';
  const broadcast=async(message)=>app.evaluate(({BrowserWindow},message)=>{const w=BrowserWindow.getAllWindows().find(w=>w.webContents.getURL().includes('view=settings'));w.webContents.send('desktop-event',{type:'chat',message,final:!message.pending});},message);
  for(let i=0;i<65;i++)await broadcast({id:`synthetic-${i}`,role:i%2?'assistant':'user',text:i===64?sample:`Mensaje sintético ${i}: contexto de prueba.`});
  await delay(200);assert.equal(await panel.locator('.message').count(),40);assert.equal(await panel.locator('.messages img').count(),0);assert(await panel.locator('.messages pre code').count());
  await panel.locator('.message').last().getByRole('button',{name:'Copiar mensaje'}).click();await panel.locator('.message').last().getByRole('button',{name:'Copiar mensaje'}).getByText('Copiado',{exact:true}).waitFor();assert.equal(await app.evaluate(async ({clipboard},sample)=>(await clipboard.readText()).replace(/\r\n/g,"\n")===sample,sample),true);
  const log=panel.getByRole('log',{name:'Conversación con Karen'});await log.evaluate(e=>{e.scrollTop=0;e.dispatchEvent(new Event('scroll'));});await delay(60);await broadcast({id:'new-response',role:'assistant',text:'Una nueva respuesta.'});await delay(80);assert.equal(await log.evaluate(e=>e.scrollTop),0);await panel.getByRole('button',{name:'Ver mensajes anteriores'}).click();assert.equal(await panel.locator('.message').count(),66);await panel.getByRole('button',{name:'Volver al final'}).click();assert(await log.evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight<3));
  await broadcast({id:'pending',role:'assistant',text:'',pending:true});assert(await panel.getByText('Respondiendo',{exact:true}).isVisible());await broadcast({id:'pending',role:'assistant',text:'Respuesta terminada.',pending:false});
  for(const [width,height] of [[1120,800],[820,640]]){await resize(width,height);await panel.screenshot({path:path.join(output,`chat-${width}.png`)});assert(await panel.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
  await panel.emulateMedia({reducedMotion:'reduce'});await broadcast({id:'pending-reduced',role:'assistant',text:'',pending:true});assert.equal(await panel.locator('.message-working i').first().evaluate(e=>getComputedStyle(e).animationName),'none');
  await select('Música');await panel.getByText('Conectar música del navegador',{exact:true}).click();await panel.getByRole('button',{name:'Generar código del complemento',exact:true}).waitFor();
  await select('Apariencia');await panel.getByText('Movimiento, pantalla y accesibilidad',{exact:true}).click();await panel.getByLabel('Monitor',{exact:true}).waitFor();
  await assert.rejects(()=>panel.evaluate(()=>window.karen.copyText('x'.repeat(65537))),/límite/);
  assert.deepEqual(errors,[]);const report={date:new Date().toISOString(),isolatedProfile:true,syntheticChat:true,sections:checks,keyboardSearch:true,accentInsensitiveSearch:true,emptySearchRecovery:true,draftAcrossTabs:true,paginatedMessages:true,noForcedScroll:true,copyPlainText:true,safeModelOutput:true,reducedMotion:true,advancedDisclosures:true,errors};fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await app?.close().catch(()=>{});fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});}
})().catch(e=>{console.error(e);process.exitCode=1;});
