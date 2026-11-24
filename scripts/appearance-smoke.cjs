const { _electron: electron } = require("@playwright/test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  fs.mkdirSync("qa", { recursive: true });
  // Hydrating a saved accent replaces the first renderer effect while Pixi's
  // asynchronous init may still be pending. This must never destroy its
  // application plugins before they have initialized.
  fs.mkdirSync(".qa-profile", { recursive: true });
  const startupSettings = path.resolve(".qa-profile/settings.json");
  const savedSettings = fs.existsSync(startupSettings) ? JSON.parse(fs.readFileSync(startupSettings, "utf8")) : {};
  fs.writeFileSync(startupSettings, JSON.stringify({ ...savedSettings, accent: "#b6a0f5" }));
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const launch = () => electron.launch({ args: [path.resolve("."), "--qa"], env });
  let app = await launch();
  const errors = [];
  try {
    await app.firstWindow();
    await new Promise(resolve => setTimeout(resolve, 700));
    const panel = app.windows().find(page => page.url().includes("view=settings"));
    const pet = app.windows().find(page => page.url().includes("view=pet"));
    assert(panel && pet);
    for (const page of app.windows()) page.on("pageerror", error => errors.push(error.message));
    await panel.getByRole("button", { name: "Apariencia", exact: true }).click();
    const slider = panel.getByRole("slider", { name: "Tamaño del PET", exact: true });
    for (const scale of [0.5, 2, 1.5]) {
      await slider.fill(String(scale));
      await panel.waitForTimeout(200);
      const bounds = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes("view=pet")).getBounds());
      const area = await app.evaluate(({ screen, BrowserWindow }) => screen.getDisplayMatching(BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes("view=pet")).getBounds()).workArea);
      const fit = Math.min(scale, area.width / 380, area.height / 440);
      assert.equal(bounds.width, Math.round(380 * fit));
      assert.equal(bounds.height, Math.round(440 * fit));
      assert(bounds.x >= area.x && bounds.y >= area.y);
      assert(bounds.x + bounds.width <= area.x + area.width);
      assert(bounds.y + bounds.height <= area.y + area.height);
    }
    await panel.getByRole("button", { name: "Normal 100 %", exact: true }).click();
    assert.equal((await panel.evaluate(() => window.karen.snapshot())).settings.scale, 1);
    await panel.evaluate(() => window.karen.settings({ animations: false, particles: false, cursorTracking: true }));
    // Windows can pause a panel occluded by the always-on-top pet. Test the
    // preview in its actual foreground usage scene instead of a hidden frame.
    await app.evaluate(({ BrowserWindow }) => {
      BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes("view=pet")).hide();
      const settings = BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes("view=settings"));
      settings.show();
      settings.focus();
    });
    await panel.bringToFront();
    assert.equal(await panel.evaluate(() => document.hidden), false);
    // Exercise real browser pointer events in the live preview. The native pet
    // continues reading the OS cursor, which browser automation does not move.
    const preview = panel.locator(".preview-window canvas");
    const previewBounds = await preview.boundingBox();
    assert(previewBounds);
    const cursor = async (x, y) => {
      await panel.mouse.move(previewBounds.x + previewBounds.width * x, previewBounds.y + previewBounds.height * y);
      await panel.waitForTimeout(350);
    };
    await panel.evaluate(() => window.karen.demo("LISTENING"));
    await cursor(0, 0.52);
    const left = await preview.screenshot({ path: "qa/pet-gaze-left.png", omitBackground: true });
    await cursor(1, 0.52);
    const right = await preview.screenshot({ path: "qa/pet-gaze-right.png", omitBackground: true });
    assert(!left.equals(right), "La mirada debe cambiar al mover el cursor");
    await panel.emulateMedia({ reducedMotion: "reduce" });
    await cursor(0.5, 0);
    await preview.screenshot({ path: "qa/pet-reduced-motion.png", omitBackground: true });
    await panel.emulateMedia({ reducedMotion: "no-preference" });
    await panel.evaluate(() => window.karen.settings({ scale: 1.5, animations: true, particles: true }));
    await panel.evaluate(() => window.karen.demo("HAPPY"));
    await panel.waitForTimeout(400);
    await panel.screenshot({ path: "qa/pet-appearance.png" });
    await panel.getByRole("button", { name: "Comportamiento", exact: true }).click();
    await panel.evaluate(() => window.karen.demo("CONFUSED"));
    await panel.waitForTimeout(250);
    await panel.screenshot({ path: "qa/pet-expressions.png" });
    assert.equal(errors.length, 0);
    await app.close();
    app = await launch();
    await app.firstWindow();
    const restartedPet = app.windows().find(page => page.url().includes("view=pet")) ||
      await app.waitForEvent("window", { predicate: page => page.url().includes("view=pet") });
    await restartedPet.waitForSelector("canvas");
    const bounds = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes("view=pet")).getBounds());
    const profile = await app.evaluate(({ app }) => app.getPath("userData"));
    const scale = JSON.parse(fs.readFileSync(path.join(profile, "settings.json"), "utf8")).scale;
    assert.equal(scale, 1.5);
    const area = await app.evaluate(({ screen, BrowserWindow }) => screen.getDisplayMatching(BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes("view=pet")).getBounds()).workArea);
    const fit = Math.min(scale, area.width / 380, area.height / 440);
    assert.equal(bounds.width, Math.round(380 * fit));
    assert.equal(bounds.height, Math.round(440 * fit));
    console.log(JSON.stringify({ sizes: [0.5, 2, 1.5], restartScale: scale, cursorScreenshots: true, reducedMotion: true, errors }));
  } finally {
    await app.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
