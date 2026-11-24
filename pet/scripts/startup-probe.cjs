const {_electron:electron}=require('@playwright/test');
const {createCoreQaProfile}=require('./core-qa-profile.cjs');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const qa=createCoreQaProfile('karen-native-startup-');
  fs.writeFileSync(path.join(qa.profile,'settings.json'),JSON.stringify({sttEnabled:false,wakeWordEnabled:false,voiceEnabled:false,petStyle:'aurora',idleAfter:15}));
  const env={...process.env,KAREN_QA_PROFILE:qa.profile};delete env.ELECTRON_RUN_AS_NODE;
  const app=await electron.launch({args:[path.resolve('.'),'--qa'],env});
  const errors=[]; const samples=[];
  try{
    const pet=app.windows().find(w=>w.url().includes('view=pet')) || await app.waitForEvent('window',{predicate:w=>w.url().includes('view=pet')});
    pet.on('pageerror',e=>errors.push(e.stack));
    await pet.waitForSelector('canvas');
    for(const delay of [100,2000,5000]){
      await pet.waitForTimeout(delay);
      samples.push(await pet.evaluate(()=>({hidden:document.hidden,renderer:document.querySelector('.pet-renderer').outerHTML.replace(/<canvas.*<\/canvas>/,'CANVAS'),error:document.querySelector('.error-banner')?.textContent})));
      await pet.screenshot({path:`qa/startup-${delay}.png`,omitBackground:true});
    }
    fs.writeFileSync('qa/startup-results.json',JSON.stringify({at:new Date().toISOString(),errors,samples},null,2));
    assert.deepEqual(errors,[],'Saved appearance startup must not produce rendering errors');
    console.log(JSON.stringify({errors,samples}));
  }finally{await app.close();qa.cleanup();}
})().catch(e=>{console.error(e);process.exitCode=1;});
