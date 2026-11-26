const { spawn } = require('node:child_process');
const path = require('node:path');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const child = spawn(path.resolve('dist-native/KarenMusicBridge.exe'), [], { windowsHide: true, stdio: ['pipe','pipe','pipe'] });
let buffer = '', received = false, context = false, initial;
const timeout = setTimeout(() => { child.kill(); throw new Error('GSMTC no respondió.'); }, 15000);
child.on('error', error => { clearTimeout(timeout); throw error; });
child.stderr.resume();
child.stdout.on('data', chunk => {
  buffer += chunk;
  let end;
  while ((end = buffer.indexOf('\n')) >= 0) {
    const row = JSON.parse(buffer.slice(0, end)); buffer = buffer.slice(end + 1);
    if (row.type === 'sessions') {
      received = true;
      // Never persist real titles, artwork, artists or session identifiers.
      console.log(JSON.stringify({ nativeSessions: row.sessions.length, eventSnapshot: true }));
      child.stdin.write(JSON.stringify({ id: 'probe', action: 'context' }) + '\n');
    } else if (row.type === 'result' && row.id === 'probe') {
      context = true;
      console.log(JSON.stringify({ contextRead: true, safeDesktop: row.safeDesktop, callsClear: row.callsClear }));
      initial={at:Date.now(),cpu:row.cpuSeconds,ram:row.workingSetBytes};
      setTimeout(()=>child.stdin.write(JSON.stringify({id:'measured',action:'context'})+'\n'),5000);
    } else if (row.type === 'result' && row.id === 'measured') {
      const elapsed=(Date.now()-initial.at)/1000;
      const report={source:'Owned GSMTC helper, idle subscription for five seconds; context probes included',elapsedSeconds:elapsed,
        cpuOneCorePercent:(row.cpuSeconds-initial.cpu)/elapsed*100,workingSetBeforeMiB:initial.ram/1048576,workingSetAfterMiB:row.workingSetBytes/1048576};
      fs.mkdirSync('qa/music',{recursive:true});fs.writeFileSync('qa/music/native-metrics.json',JSON.stringify(report,null,2));
      console.log(JSON.stringify(report));child.stdin.end();
    } else if (row.type === 'error') { clearTimeout(timeout); child.kill(); throw new Error(row.error); }
  }
});
child.on('exit', code => { clearTimeout(timeout); assert.equal(code, 0); assert(received && context); });
