const { _electron: electron } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");
const os = require('node:os');
const assert = require("node:assert/strict");
(async () => {
  fs.mkdirSync("qa", { recursive: true });
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  delete env.KAREN_CORE_DB;delete env.KAREN_TASKS_DB;
  const profile=fs.mkdtempSync(path.join(os.tmpdir(),'karen-native-'));
  env.KAREN_QA_PROFILE=profile;
  fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify({fullscreenHide:false,introEnabled:false,mode:'normal',alwaysOnTop:true,gatewayUrl:'ws://127.0.0.1:1',authSource:'stored'}));
  const packaged = process.env.KAREN_SMOKE_EXECUTABLE;
  const app = await electron.launch({
    ...(packaged ? { executablePath: packaged, args: ["--qa"] }
      : { args: [path.resolve(__dirname, ".."), "--qa"] }),
    env,
    timeout: 30000,
  });
  const errors = [];
  const findings = {};
  try {
    await new Promise((r) => setTimeout(r, 1700));
    const windows = app.windows();
    const panel = windows.find((w) => w.url().includes("view=settings"));
    const pet = windows.find((w) => w.url().includes("view=pet"));
    assert(panel && pet, "Las dos ventanas deben arrancar");
    for (const w of windows) w.on("pageerror", (e) => errors.push(e.message));
    await panel.waitForSelector("h1");
    const select=async name=>{await panel.keyboard.press('Control+k');const field=panel.getByRole('searchbox',{name:'Buscar sección'});await field.fill(name);await field.press('Enter');};
    await pet.waitForSelector("canvas");
    await panel.screenshot({ path: "qa/settings-conversation.png" });
    await pet.screenshot({ path: "qa/pet-idle.png", omitBackground: true });
    findings.windows = await app.evaluate(({ BrowserWindow }) =>
      BrowserWindow.getAllWindows().map((w) => ({
        title: w.getTitle(),
        backgroundColor: w.getBackgroundColor(),
        top: w.isAlwaysOnTop(),
        bounds: w.getBounds(),
      })),
    );
    console.log("Ventanas:", JSON.stringify(findings.windows));
    findings.topmostReported=findings.windows.some(w=>w.top&&w.title==='Karen Desktop Pet');
    assert.equal((await panel.evaluate(()=>window.karen.snapshot())).settings.alwaysOnTop,true);
    await select('Apariencia');
    await panel
      .getByRole("slider", { name: "Luminosidad", exact: true })
      .fill("1.1");
    await panel.waitForTimeout(200);
    assert.equal(
      (await panel.evaluate(() => window.karen.snapshot())).settings.brightness,
      1.1,
    );
    await panel.screenshot({ path: "qa/settings-appearance.png" });
    await select('Comportamiento');
    for (const name of [
      "Feliz",
      "Con duda",
      "Descansando",
      "Escuchando",
      "Pensando",
      "Algo ocurrió",
    ]) {
      await panel.getByRole("button", { name, exact: true }).click();
      await panel.waitForTimeout(250);
    }
    await panel
      .getByRole("button", { name: "Descansando", exact: true })
      .click();
    await panel.waitForTimeout(450);
    await pet.screenshot({ path: "qa/pet-sleeping.png", omitBackground: true });
    await panel.getByRole("button", { name: "En calma", exact: true }).click();
    findings.voice = await panel.evaluate(async () => {
      const bytes = await window.karen.synthesize("Hola. Soy Karen.");
      const length = bytes.byteLength;
      const c = new AudioContext();
      try {
        const audio = await c.decodeAudioData(bytes);
        let sum = 0;
        for (const x of audio.getChannelData(0)) sum += x * x;
        return {
          bytes: length,
          duration: audio.duration,
          rms: Math.sqrt(sum / audio.length),
        };
      } finally {
        await c.close();
      }
    });
    assert(
      findings.voice.duration > 0.2 && findings.voice.rms > 0.001,
      "Windows debe generar audio real",
    );
    await panel.evaluate(() => window.karen.connect());
    await panel.waitForTimeout(1800);
    findings.gateway = (
      await panel.evaluate(() => window.karen.snapshot())
    ).connection;
    await select('Diagnóstico');
    await panel.screenshot({ path: "qa/settings-diagnostics.png" });
    findings.processes = await app.evaluate(({ app }) =>
      app
        .getAppMetrics()
        .map((m) => ({
          type: m.type,
          cpu: m.cpu.percentCPUUsage,
          memoryKB: m.memory.workingSetSize,
        })),
    );
    await panel.evaluate(() =>
      window.karen.credential("test-only-encrypted-secret"),
    );
    assert(
      !fs
        .readFileSync(path.join(profile,'vault.dpapi'))
        .includes(Buffer.from("test-only-encrypted-secret")),
    );
    await panel.evaluate(() => window.karen.credential(""));
    await panel.evaluate(() => window.karen.hide());
    assert(
      await app.evaluate(
        ({ BrowserWindow }) =>
          BrowserWindow.getAllWindows()
            .find((w) => w.webContents.getURL().includes('view=pet'))
            ?.isVisible() === false,
      ),
    );
    await panel.evaluate(() => window.karen.show());
    assert(
      await app.evaluate(
        ({ BrowserWindow }) =>
          BrowserWindow.getAllWindows()
            .find((w) => w.webContents.getURL().includes('view=pet'))
            ?.isVisible() === true,
      ),
    );
    findings.errors = errors;
    assert.equal(errors.length, 0, "No debe haber errores del renderizador");
    fs.writeFileSync(
      "qa/native-results.json",
      JSON.stringify(findings, null, 2),
    );
    console.log(JSON.stringify(findings, null, 2));
  } finally {
    await app.close();
    fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
