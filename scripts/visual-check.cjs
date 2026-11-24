const { chromium } = require("@playwright/test");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({
    executablePath:
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    headless: true,
  });
  fs.mkdirSync("qa", { recursive: true });
  const page = await browser.newPage({
    viewport: { width: 1080, height: 740 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => {
    errors.push(e.message);
    console.log("PAGEERROR", e.message);
  });
  page.on("console", (m) => {
    if (m.type() === "error") console.log("CONSOLE", m.text());
  });
  try {
    await page.goto("http://127.0.0.1:5179/?view=settings");
    await page.waitForSelector("canvas");
    await page.waitForTimeout(700);
    await page.getByRole("button", { name: "Apariencia", exact: true }).click();
    await page.screenshot({ path: "qa/browser-appearance.png" });
    await page.setViewportSize({ width: 820, height: 620 });
    await page.screenshot({ path: "qa/browser-minimum.png" });
    await page.goto("http://127.0.0.1:5179/?view=pet");
    await page.setViewportSize({ width: 380, height: 440 });
    await page.waitForSelector("canvas");
    await page.waitForTimeout(500);
    await page.screenshot({ path: "qa/browser-pet.png", omitBackground: true });
    console.log(JSON.stringify({ errors }));
    if (errors.length) process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
