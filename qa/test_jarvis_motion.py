"""Browser regression: a visible Jarvis sphere keeps moving during conversation."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class JarvisMotionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node') and (ROOT / 'desktop-pet/node_modules/playwright').is_dir(),
                         'Uses existing optional Playwright installation')
    def test_native_home_card_escapes_metadata_and_preserves_drafts(self):
        script = r'''
const assert=require('node:assert/strict');
const {chromium}=require('./desktop-pet/node_modules/playwright');
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--disable-gpu']});
  try {
    const page=await browser.newPage();
    await page.setContent('<main></main>');
    await page.addScriptTag({path:'integrations/home_assistant/karen-home-card.js'});
    const result=await page.evaluate(()=>{
      const card=document.createElement('karen-home-card');document.querySelector('main').append(card);
      let rejected=0;
      for(const agent_id of ['javascript:alert(1)','script.other','conversation.bad/command']) {
        try{card.setConfig({agent_id});}catch{rejected++;}
      }
      card.setConfig({media_entities:['media_player.fire_test','media_player.jellyfin_test']});
      card.hass={states:{}};
      const absent=card.shadowRoot.textContent.includes('Sin datos de reproducción');
      card.hass={states:{
        'media_player.fire_test':{entity_id:'media_player.fire_test',state:'playing',attributes:{app_name:'YouTube'}},
        'media_player.jellyfin_test':{entity_id:'media_player.jellyfin_test',state:'unavailable',attributes:{media_title:'Título antiguo'}}
      }};
      const noStale= !card.shadowRoot.textContent.includes('Título antiguo');
      card.hass={states:{'media_player.fire_test':{entity_id:'media_player.fire_test',state:'playing',attributes:{media_title:'<img src=x onerror=alert(1)>',app_name:'YouTube'}}}};
      card.shadowRoot.querySelector('textarea').value='Borrador importante';
      card.hass={states:{'media_player.fire_test':{entity_id:'media_player.fire_test',state:'playing',attributes:{media_title:'<img src=x onerror=alert(1)>',app_name:'YouTube'}}}};
      const draft=card.shadowRoot.querySelector('textarea').value;
      let selected;card.addEventListener('hass-more-info',event=>selected=event.detail.entityId);
      card.shadowRoot.querySelector('#media-info').click();
      return {rejected,absent,noStale,selected,draft,title:card.shadowRoot.querySelector('.title').textContent,imageSource:card.shadowRoot.querySelector('figure img').getAttribute('src'),links:card.shadowRoot.querySelectorAll('a').length};
    });
    assert.deepEqual(result,{rejected:3,absent:true,noStale:true,selected:'media_player.fire_test',draft:'Borrador importante',title:'<img src=x onerror=alert(1)>',imageSource:null,links:0});
    await page.evaluate(()=>{
      const card=document.querySelector('karen-home-card');
      card.hass={user:{id:'owner'},states:{'conversation.karen':{state:'unknown',attributes:{friendly_name:'Karen'}}},callApi:async(method,route,data)=>{
        if(method!=='POST'||route!=='conversation/process'||data.agent_id!=='conversation.karen')throw Error('Native API contract broken');
        return {conversation_id:'synthetic-session',response:{speech:{plain:{speech:'Respuesta sintética'}}}};
      }};
    });
    await page.locator('karen-home-card').getByRole('textbox').fill('Hola');
    await page.locator('karen-home-card').getByRole('button',{name:'Enviar',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('karen-home-card').shadowRoot.querySelector('.messages').textContent.includes('Respuesta sintética'));
    const location=await page.evaluate(()=>{
      const card=document.createElement('karen-location-card');document.querySelector('main').append(card);
      card.setConfig({sources:[{name:'Teléfono QA',entity:'device_tracker.qa'}]});
      const tracker={entity_id:'device_tracker.qa',state:'home',last_updated:new Date().toISOString(),attributes:{latitude:12.34,longitude:45.67,gps_accuracy:30}};
      card.hass={states:{'device_tracker.qa':tracker}};
      const restoredIsOld=card.shadowRoot.querySelector('.place').textContent.includes('Última ubicación conocida');
      card.hass={states:{'device_tracker.qa':tracker,'sensor.qa_report':{entity_id:'sensor.qa_report',state:new Date().toISOString(),attributes:{location_tracker:'device_tracker.qa'}}}};
      const fresh=card.shadowRoot.querySelector('.place').textContent==='Zona informada: Casa';
      tracker.state='unavailable';tracker.attributes.gps_accuracy=0;
      card.hass={states:{'device_tracker.qa':tracker,'sensor.qa_report':{entity_id:'sensor.qa_report',state:new Date().toISOString(),attributes:{location_tracker:'device_tracker.qa'}}}};
      const unavailableIsOld=card.shadowRoot.querySelector('.place').textContent.includes('Última ubicación conocida');
      const zeroAccuracyUnknown=card.shadowRoot.querySelector('.accuracy').textContent==='Precisión no informada';
      tracker.state='home';
      card.hass={states:{'device_tracker.qa':tracker,'sensor.qa_report':{entity_id:'sensor.qa_report',state:new Date(Date.now()-3600000).toISOString(),attributes:{location_tracker:'device_tracker.qa'}}}};
      return {restoredIsOld,fresh,unavailableIsOld,zeroAccuracyUnknown,expiredIsOld:card.shadowRoot.querySelector('.place').textContent.includes('Última ubicación conocida')};
    });
    assert.deepEqual(location,{restoredIsOld:true,fresh:true,unavailableIsOld:true,zeroAccuracyUnknown:true,expiredIsOld:true});
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run(['node', '-'], input=script, text=True, encoding='utf-8', capture_output=True, cwd=ROOT, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('node') and (ROOT / 'desktop-pet/node_modules/playwright').is_dir(),
                         'Uses existing optional Playwright installation; no dependency is installed')
    def test_typing_pending_reply_tools_pause_and_reduced_motion(self):
        script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('./desktop-pet/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({headless:true,args:['--disable-gpu']});
  try {
    for (const viewport of [{width:1365,height:768},{width:390,height:844}]) {
      const context = await browser.newContext({viewport});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      let finish;
      await page.route('http://karen.test/**', async route => {
        const pathname = new URL(route.request().url()).pathname;
        if (pathname.startsWith('/api/')) {
          let data = {};
          if (pathname.endsWith('/message')) data = await new Promise(resolve => {finish = () => resolve({answer:'Respuesta sintética.'});});
          else if (pathname.endsWith('/chats')) data = {id:'a'.repeat(32)};
          else if (pathname.endsWith('/models')) data = {models:[{name:'local-test'}]};
          else if (pathname.endsWith('/status')) data = {models:{hardware:{},latency:[],active_model:null},diagnostics:{samples:0,recommendations:[]},vision:{}};
          return route.fulfill({json:data});
        }
        const name = {'/jarvis':'jarvis.html','/jarvis.js':'jarvis.js','/jarvis.css':'jarvis.css'}[pathname];
        if (!name) return route.fulfill({status:404});
        return route.fulfill({body:fs.readFileSync(path.join('mobile',name)),contentType:name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html'});
      });
      await page.goto('http://karen.test/jarvis');
      await page.waitForFunction(() => Number(document.querySelector('#presence').dataset.frames) > 2);
      // Disable speech in this offline fixture; no voice process is contacted.
      await page.locator('#voice-toggle').click();
      await page.locator('#tools-toggle').click();
      await page.locator('#message').fill('Prueba sintética sin datos personales');
      const frames = () => page.locator('#presence').getAttribute('data-frames').then(Number);
      let before = await frames();
      await page.waitForTimeout(250);
      assert.ok(await frames() > before, 'typing with tools open must animate');
      await page.locator('#send').click();
      await page.waitForFunction(() => document.body.dataset.state === 'busy');
      before = await frames();
      await page.waitForTimeout(250);
      assert.ok(await frames() > before, 'pending reply must animate');
      finish();
      await page.locator('#send').waitFor({state:'visible'});
      await page.waitForFunction(() => !document.querySelector('#send').disabled);
      await page.locator('#motion').click();
      await page.waitForTimeout(80);
      before = await frames();
      await page.waitForTimeout(200);
      assert.equal(await frames(), before, 'explicit pause must stop animation');
      await page.locator('#motion').click();
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.waitForTimeout(80);
      before = await frames();
      await page.waitForTimeout(200);
      assert.equal(await frames(), before, 'reduced motion must stop animation');
      await page.emulateMedia({reducedMotion:'no-preference'});
      before = await frames();
      await page.waitForTimeout(250);
      assert.ok(await frames() > before, 'animation must resume');
      assert.deepEqual(errors, []);
      console.log(`Jarvis motion ${viewport.width}x${viewport.height}: OK`);
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});
'''
        result = subprocess.run(['node', '-'], input=script, text=True, encoding='utf-8', capture_output=True, cwd=ROOT, timeout=50)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
