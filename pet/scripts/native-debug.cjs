const { _electron } = require("@playwright/test");
const fs = require("node:fs");
(async () => {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await _electron.launch({ args: [process.cwd(), "--qa"], env });
  const attach = (w) => {
    w.on("pageerror", (e) => console.log("PAGEERROR", e.message));
    w.on("console", (m) => {
      if (m.type() === "error" || m.type() === "warning")
        console.log("CONSOLE", m.text());
    });
  };
  app.on("window", attach);
  app.windows().forEach(attach);
  try {
    await new Promise((r) => setTimeout(r, 3000));
    for (const [i, w] of app.windows().entries()) {
      console.log("PAGE", w.url(), await w.locator("body").innerText());
      await w.screenshot({ path: `qa/debug-${i}.png` });
    }
  } finally {
    await app.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
