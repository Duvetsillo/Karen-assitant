// Real Electron UI + Python executor + SQLite; synthetic tools, no audio/network.
const { _electron: electron, expect } = require('@playwright/test');
const { execFileSync, spawn } = require('node:child_process');
const { writeFileSync, existsSync } = require('node:fs');
const { createCoreQaProfile } = require('./core-qa-profile.cjs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const root = path.resolve('..');
  const { directory, profile, cleanup } = createCoreQaProfile('karen-native-tasks-');
  const core = path.join(directory, 'core.sqlite3'), tasks = path.join(directory, 'tasks.sqlite3');
  const python = process.env.KAREN_TEST_PYTHON || 'python';
  const fixture = `import sys
from conversations import Conversations
from karen_tasks import TaskEngine, ToolSpec
Conversations(sys.argv[1]).current()
engine = TaskEngine({'check': ToolSpec('read', lambda args, stop: True, verify=lambda a, r: r is True)}, sys.argv[2])
print(engine.create([{'tool': 'check', 'args': {'private': 'SYNTHETIC-NOT-FOR-PET'}}]))`;
  const env = { ...process.env, KAREN_CORE_DB: core, KAREN_TASKS_DB: tasks, KAREN_QA_PROFILE: profile };
  delete env.ELECTRON_RUN_AS_NODE;
  const packaged = process.env.KAREN_SMOKE_EXECUTABLE;
  let application;
  let runner;
  let runnerExit;
  try {
    const id = execFileSync(python, ['-c', fixture, core, tasks], { cwd: root, windowsHide: true }).toString().trim();
    application = await electron.launch({
      ...(packaged ? { executablePath: packaged, args: ['--qa', '--qa-core'] }
        : { args: [path.resolve('.'), '--qa', '--qa-core'] }), env,
    });
    let panel;
    for (let attempt = 0; attempt < 100; attempt++) {
      panel = application.windows().find(window => window.url().includes('view=settings'));
      if (panel) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert(panel, 'Falta panel nativo');
    await panel.waitForSelector('#message');
    const input = panel.locator('#message');
    const send = panel.getByRole('button', { name: 'Enviar mensaje', exact: true });
    await input.fill(`/tareas estado ${id}`);
    await expect(send).toBeEnabled();
    await send.click();
    await expect(panel.getByText(`Tarea ${id}: pending;`, { exact: false })).toBeVisible();
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).connection.state, 'disconnected');
    const started = path.join(directory, 'started'), release = path.join(directory, 'release');
    const complete = `import sys
from pathlib import Path
from karen_tasks import TaskEngine, ToolSpec
def check(args, stop):
    Path(sys.argv[3]).write_text('started')
    while not stop.wait(0.02):
        if Path(sys.argv[4]).exists(): return True
    raise InterruptedError()
engine = TaskEngine({'check': ToolSpec('read', check, verify=lambda a, r: r is True, timeout=10)}, sys.argv[1])
assert engine.run(sys.argv[2], [{'tool': 'check', 'args': {'private': 'SYNTHETIC-NOT-FOR-PET'}}])['status'] == 'completed'`;
    runner = spawn(python, ['-c', complete, tasks, id, started, release], { cwd: root, windowsHide: true, stdio: 'ignore' });
    runnerExit = new Promise((resolve, reject) => { runner.once('exit', resolve); runner.once('error', reject); });
    void runnerExit.catch(() => {});
    for (let attempt = 0; attempt < 100 && !existsSync(started); attempt++)
      await new Promise(resolve => setTimeout(resolve, 25));
    assert(existsSync(started), 'El ejecutor sintético no inició el paso');
    await input.fill(`/tareas estado ${id}`);
    await send.click();
    await expect(panel.getByText(`Tarea ${id}: running;`, { exact: false })).toBeVisible();
    writeFileSync(release, 'continue');
    assert.equal(await runnerExit, 0);
    await input.fill(`/tareas estado ${id}`);
    await send.click();
    await expect(panel.getByText(`Tarea ${id}: completed;`, { exact: false })).toBeVisible();
    await input.fill('/tareas estado ' + 'b'.repeat(32));
    await send.click();
    await expect(panel.getByText('Tarea desconocida.', { exact: true })).toBeVisible();
    const snapshot = await panel.evaluate(() => window.karen.snapshot());
    assert(!snapshot.settings.wakeWordEnabled && !snapshot.settings.sttEnabled && !snapshot.settings.voiceEnabled);
    assert.equal(snapshot.connection.state, 'disconnected');
    assert(!JSON.stringify(snapshot.messages).includes('SYNTHETIC-NOT-FOR-PET'));
    console.log('CORE_TASKS_NATIVE_OK: same task ID pending/running/completed, offline UI, unknown task, no private arguments');
  } finally {
    if (application) await application.close();
    if (runner && runner.exitCode === null) runner.kill();
    if (runnerExit) await runnerExit.catch(() => {});
    cleanup();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
