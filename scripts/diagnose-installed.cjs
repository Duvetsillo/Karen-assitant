// Read startup diagnostics from the installed app. Never sends messages or UI input.
const {_electron:electron}=require('@playwright/test');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
  const env={...process.env,KAREN_CORE_DB:'C:/karen/.private/conversations.sqlite3'};
  delete env.ELECTRON_RUN_AS_NODE;delete env.KAREN_QA_PROFILE;
  const app=await electron.launch({executablePath:path.join(process.env.LOCALAPPDATA,'Programs/Karen Desktop Pet/Karen Desktop Pet.exe'),args:['--settings'],env});
  const errors=[];
  try{
    for(const page of app.windows()){
      page.on('pageerror',e=>errors.push({type:'pageerror',message:e.message}));
      page.on('console',e=>{if(e.type()==='error')errors.push({type:'console',message:e.text()});});
    }
    await new Promise(r=>setTimeout(r,2500));
    const pages=[];
    for(const page of app.windows())pages.push(await page.evaluate(()=>({
      title:document.title,ready:document.readyState,rootBytes:document.getElementById('root')?.innerHTML.length,
      scripts:[...document.scripts].map(s=>s.src.split('/').at(-1)),
      appBackground:document.querySelector('.app-shell')?getComputedStyle(document.querySelector('.app-shell')).backgroundColor:null,
      canvas:document.querySelectorAll('canvas').length,version:document.querySelector('.sidebar-foot small')?.textContent,
    })));
    const result={errors,pages};
    fs.writeFileSync('qa/initiative/installed-startup.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  }finally{await app.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
