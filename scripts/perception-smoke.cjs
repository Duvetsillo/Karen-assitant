const { _electron: electron } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({ args: [path.resolve('.'), '--qa'], env });
  const errors = [];
  const result = {};
  try {
    await app.firstWindow();
    await new Promise(resolve => setTimeout(resolve, 600));
    const panel = app.windows().find(page => page.url().includes('view=settings'));
    assert(panel);
    const untilCapture = async (phase, timeout=15000) => {
      const deadline=Date.now()+timeout;
      while(Date.now()<deadline){if((await panel.evaluate(()=>window.karen.snapshot())).capture?.phase===phase)return;await new Promise(resolve=>setTimeout(resolve,100));}
      const alerts=await panel.locator('[role="alert"]').allTextContents();
      const snapshot=await panel.evaluate(()=>window.karen.snapshot());
      throw new Error('Capture did not reach '+phase+': '+JSON.stringify({alerts,capture:snapshot.capture,diagnostics:snapshot.diagnostics.filter(item=>item.area==='Captura')}));
    };
    for (const page of app.windows()) page.on('pageerror', error => errors.push(error.message));
    await panel.evaluate(root => window.karen.settings({ sttEnabled: true, voiceEnabled: true, ttsEngine: 'system', wakeWordEnabled: false, ...(root ? { voiceRoot: root } : {}) }), process.env.KAREN_TEST_VOICE_ROOT || '');
    const audio = await panel.evaluate(async () => Array.from(new Uint8Array(await window.karen.synthesize('Hola Karen. Esta es una prueba de audio del sistema.'))));
    assert(audio.length > 10000);
    result.ttsBytes = audio.length;
    console.log('System TTS generated.');
    if (process.env.KAREN_TEST_VOICE_ROOT) {
      const recognized = await panel.evaluate(async bytes => {
        const context = new AudioContext();
        const buffer = await context.decodeAudioData(new Uint8Array(bytes).buffer);
        await context.close();
        const offline = new OfflineAudioContext(1, Math.ceil(buffer.duration * 16000), 16000);
        const source = offline.createBufferSource(); source.buffer = buffer; source.connect(offline.destination); source.start();
        const floats = (await offline.startRendering()).getChannelData(0);
        const pcm = new Int16Array(floats.length);
        for(let i=0;i<floats.length;i++) pcm[i] = Math.max(-1,Math.min(1,floats[i]))*32767;
        return window.karen.transcribe(pcm.buffer);
      }, audio);
      assert(/prueba|audio|sistema/i.test(recognized));
      result.realOfflineStt = true;
      console.log('Offline STT verified against generated speech.');
    }
    await panel.getByRole('button', {name:'Percepción',exact:true}).click();
    const sourceId = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(window => window.webContents.getURL().includes('view=settings')).getMediaSourceId());
    const image = await panel.evaluate(async id => {
      const sources = await window.karen.captureSources();
      if(!sources.some(source => source.id === id)) throw new Error('QA window unavailable');
      return window.karen.captureScreen(id);
    }, sourceId);
    assert.equal(image.mimeType, 'image/jpeg');
    assert(image.content.length > 1000);
    result.screenBytes = Buffer.from(image.content,'base64').length;
    result.screenSource = 'isolated QA window';
    console.log('Selected QA window capture verified.');
    // An unarmed request must be denied, even from the app itself.
    result.deniedUnarmed = await panel.evaluate(async () => {
      try { const stream=await navigator.mediaDevices.getDisplayMedia({audio:true,video:true});stream.getTracks().forEach(track=>track.stop());return false; } catch { return true; }
    });
    assert.equal(result.deniedUnarmed,true);
    console.log('Unarmed display request denied.');
    await panel.getByRole('button',{name:'Escuchar audio del PC',exact:true}).click();
    await untilCapture('recording');
    result.loopbackStarted = true;
    console.log('Windows loopback recording started.');
    await panel.evaluate(async bytes => {
      const url = URL.createObjectURL(new Blob([new Uint8Array(bytes)],{type:'audio/wav'}));
      const audio = new Audio(url);
      await audio.play();
      await new Promise(resolve => {audio.onended=resolve;audio.onerror=resolve;});
      URL.revokeObjectURL(url);
    }, audio);
    if (process.env.KAREN_TEST_VOICE_ROOT) {
      const capture = (await panel.evaluate(()=>window.karen.snapshot())).capture;
      console.log(JSON.stringify({afterPlayback:capture}));
      if(capture?.phase==='recording') await panel.evaluate(() => window.karen.systemAudio('finish'));
      await panel.getByLabel('Transcripción del PC · revisa antes de enviar').waitFor({timeout:180000});
      const transcript = await panel.getByLabel('Transcripción del PC · revisa antes de enviar').inputValue();
      assert(/prueba|audio|sistema/i.test(transcript));
      assert.equal((await panel.evaluate(()=>window.karen.snapshot())).messages.length,0,'PC audio is reviewed, never auto-sent');
      result.realLoopbackStt = true;
    } else await panel.evaluate(()=>window.karen.abort());
    await panel.screenshot({path:'qa/perception.png'});
    await panel.evaluate(()=>window.karen.abort());
    await untilCapture('idle');
    await panel.getByRole('button',{name:'Elegir pantalla o ventana',exact:true}).click();
    await panel.getByLabel('Fuente de captura').selectOption(sourceId);
    await panel.getByRole('button',{name:'Tomar captura para revisar',exact:true}).click();
    await panel.locator('.screen-preview').waitFor();
    assert.equal(await panel.getByRole('button',{name:'Enviar captura',exact:true}).isDisabled(),true);
    await panel.getByRole('button',{name:'Descartar imagen',exact:true}).click();
    result.screenPreviewReview=true;
    await panel.evaluate(()=>window.karen.testVoice());
    await untilCapture('speaking');
    await panel.evaluate(()=>window.karen.abort());
    await untilCapture('idle');
    result.voicePlayback=true;
    if(process.env.KAREN_TEST_VOICE_ROOT){
      // Exercise the real microphone permission, then discard immediately.
      await panel.evaluate(()=>window.karen.listen());
      await untilCapture('recording');
      await panel.evaluate(()=>window.karen.abort());
      await untilCapture('idle');
      result.microphoneOpenedAndDiscarded=true;
      await panel.evaluate(()=>window.karen.systemAudio('start'));
      await untilCapture('recording');
      await panel.evaluate(()=>window.karen.hide());
      await untilCapture('idle');
      await panel.evaluate(()=>window.karen.show());
      result.hideStopsCapture=true;
    }
    assert.equal(errors.length,0);
    result.errors=errors;
    fs.writeFileSync('qa/perception-results.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } finally {await app.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
