const { spawn, execFileSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  execFileSync(process.execPath, ['scripts/build-music-bridge.cjs','--fixture'], { stdio: 'inherit', windowsHide: true });
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'karen-music-native-'));
  const wave = Buffer.alloc(44 + 8000 * 2 * 30);
  wave.write('RIFF'); wave.writeUInt32LE(wave.length - 8,4); wave.write('WAVEfmt ',8); wave.writeUInt32LE(16,16);
  wave.writeUInt16LE(1,20); wave.writeUInt16LE(1,22); wave.writeUInt32LE(8000,24); wave.writeUInt32LE(16000,28);
  wave.writeUInt16LE(2,32); wave.writeUInt16LE(16,34); wave.write('data',36); wave.writeUInt32LE(wave.length-44,40);
  const audio = path.join(directory, 'synthetic-silence.wav'); fs.writeFileSync(audio, wave);
  const fixture = spawn(path.resolve('qa/music/KarenMusicFixture.exe'), [audio], { windowsHide: true, stdio: ['pipe','pipe','pipe'] });
  fixture.stderr.resume();
  fixture.stdin.on('error', () => {});
  const exited = new Promise(resolve => fixture.once('exit', resolve));
  let adapter, sessions = [], fault;
  const until = async predicate => { for(let i=0;i<150;i++) { if(predicate()) return; if(fault) throw new Error(fault); await delay(100); } throw new Error('La sesión sintética no respondió.'); };
  try {
    const { WindowsMediaAdapter } = await import(pathToFileURL(path.resolve('dist-electron/electron/music-adapter.js')).href);
    adapter = new WindowsMediaAdapter(path.resolve('dist-native/KarenMusicBridge.exe'), (value, error) => { sessions = value; if(error) fault = error; });
    adapter.start();
    const current = () => sessions.find(s => s.title === 'Karen Music QA A' || s.title === 'Karen Music QA B');
    await until(() => current()?.status === 'playing');
    assert(current().controls.includes('pause'));
    assert(await adapter.command({ action: 'pause', sessionId: current().sessionId }));
    await until(() => current()?.status === 'paused');
    assert(await adapter.command({ action: 'play', sessionId: current().sessionId }));
    await until(() => current()?.status === 'playing');
    assert(await adapter.command({ action: 'next', sessionId: current().sessionId }));
    await until(() => current()?.title === 'Karen Music QA B');
    assert(await adapter.command({ action: 'previous', sessionId: current().sessionId }));
    await until(() => current()?.title === 'Karen Music QA A');
    assert.equal(await adapter.command({ action: 'volume', sessionId: current().sessionId, value: .1 }), false);
    fixture.stdin.end('\n');
    await until(() => !current());
    const report = { source: 'Muted synthetic Windows MediaPlayer fixture', nativeGSMTC: true, play: true, pause: true, next: true, previous: true, removedSession: true, unsupportedVolumeRejected: true, realPlatformCompatibility: 'Not established' };
    fs.writeFileSync('qa/music/native-controls.json', JSON.stringify(report,null,2)); console.log(JSON.stringify(report));
  } finally {
    adapter?.stop(); if (!fixture.stdin.destroyed) fixture.stdin.end('\n');
    await Promise.race([exited,delay(1500)]); if (fixture.exitCode === null) { fixture.kill(); await exited; }
    fs.rmSync(directory, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
