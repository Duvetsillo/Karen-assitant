const { _electron: electron } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const executablePath = process.env.KAREN_TEST_INSTALLED_EXE;
  if (!executablePath) throw new Error('Define KAREN_TEST_INSTALLED_EXE con la ruta del ejecutable instalado.');
  const voiceRoot = process.env.KAREN_TEST_VOICE_ROOT;
  if (!voiceRoot) throw new Error('Define KAREN_TEST_VOICE_ROOT con la carpeta de recursos.');
  const env = {...process.env};
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await electron.launch({executablePath, args:['--qa'], cwd:path.resolve('.'), env});
  try {
    const panel = app.windows().find(page => page.url().includes('view=settings')) ||
      await app.waitForEvent('window',{predicate:page=>page.url().includes('view=settings')});
    await panel.evaluate(root => window.karen.settings({voiceRoot:root,ttsEngine:'system',sttEnabled:true,wakeWordEnabled:false}),voiceRoot);
    const audio = await panel.evaluate(async () => Array.from(new Uint8Array(await window.karen.synthesize('Hola Karen. Esta es una prueba de reconocimiento local.'))));
    const recognized = await panel.evaluate(async bytes => {
      const context = new AudioContext();
      const buffer = await context.decodeAudioData(new Uint8Array(bytes).buffer);
      await context.close();
      const offline = new OfflineAudioContext(1, Math.ceil(buffer.duration * 16000), 16000);
      const source = offline.createBufferSource(); source.buffer = buffer; source.connect(offline.destination); source.start();
      const floats = (await offline.startRendering()).getChannelData(0);
      const pcm = new Int16Array(floats.length);
      for (let i=0;i<floats.length;i++) pcm[i] = Math.max(-1,Math.min(1,floats[i]))*32767;
      return window.karen.transcribe(pcm.buffer);
    }, audio);
    assert(/prueba|reconocimiento|local/i.test(recognized),`Transcripción inesperada: ${recognized}`);
    const version = await panel.evaluate(async () => (await window.karen.snapshot()).version);
    console.log(JSON.stringify({version,installedStt:true,recognized}));
  } finally {await app.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
