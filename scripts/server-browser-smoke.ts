import { chromium } from "@playwright/test";
import { WebSocketServer } from "ws";
import { createServer } from "node:net";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { createKarenServer } from "../server/app.js";
import assert from "node:assert/strict";

const access = "synthetic-browser-access-token-32-characters";
let selectedModel: string | null = null;
const root = mkdtempSync(join(tmpdir(), "karen-browser-"));
const fixture = new WebSocketServer({ host: "127.0.0.1", port: 0 });
await new Promise<void>((resolve) => fixture.once("listening", resolve));
const wsAddress = fixture.address();
if (!wsAddress || typeof wsAddress === "string") throw new Error("Sin puerto");
fixture.on("connection", (socket) => {
  socket.send(
    JSON.stringify({
      type: "event",
      event: "connect.challenge",
      payload: { nonce: "synthetic-challenge", ts: Date.now() },
    }),
  );
  socket.on("message", (raw) => {
    const req = JSON.parse(raw.toString());
    let payload: unknown = {};
    if (req.method === "connect")
      payload = {
        type: "hello-ok",
        protocol: 4,
        server: { version: "synthetic-contract-server", connId: "test" },
        features: {
          methods: ["chat.send", "chat.history", "chat.abort"],
          events: ["chat", "agent"],
        },
        snapshot: {
          presence: [],
          health: {},
          stateVersion: { presence: 1, health: 1 },
          uptimeMs: 1,
        },
        auth: {
          role: "operator",
          scopes: ["operator.read", "operator.write"],
          deviceToken: "synthetic-device-token",
        },
        policy: {
          maxPayload: 26214400,
          maxBufferedBytes: 52428800,
          tickIntervalMs: 15000,
        },
      };
    if (req.method === "chat.history") payload = { messages: [] };
    if (req.method === 'models.list') payload = {models:[
      {id:'test-small',name:'Small fixture',provider:'local',available:true},
      {id:'test-large',name:'Large fixture',provider:'cloud',available:true},
    ]};
    if (req.method === 'sessions.list') {
      const [modelProvider, model] = (selectedModel ?? 'local/test-small').split('/');
      payload = {defaults:{modelProvider:'local',model:'test-small'},sessions:[{key:'agent:main:main',modelProvider,model,modelOverrideSource:selectedModel ? 'user' : null}]};
    }
    if (req.method === 'sessions.patch') {
      assert.equal(req.params.key,'agent:main:main');
      selectedModel = req.params.model;
      payload = {ok:true};
    }
    if (req.method === "chat.send")
      payload = { runId: req.params.idempotencyKey, status: "started" };
    socket.send(JSON.stringify({ type: "res", id: req.id, ok: true, payload }));
    if (req.method === "chat.send")
      setTimeout(
        () =>
          socket.send(
            JSON.stringify({
              type: "event",
              event: "chat",
              payload: {
                sessionKey: "agent:main:main",
                runId: req.params.idempotencyKey,
                seq: 1,
                state: "final",
                message: {
                  content: [
                    {
                      type: "text",
                      text: "Respuesta sintética del contrato: conexión completa.",
                    },
                  ],
                },
              },
            }),
          ),
        100,
      );
  });
});
const reservation = createServer();
await new Promise<void>((resolve) =>
  reservation.listen(0, "127.0.0.1", resolve),
);
const address = reservation.address();
if (!address || typeof address === "string") throw new Error("Sin puerto HTTP");
const port = address.port;
await new Promise<void>((resolve) => reservation.close(() => resolve()));
const origin = `http://127.0.0.1:${port}`;
const runtime = createKarenServer({
  dataDirectory: join(root, "data"),
  staticDirectory: resolve("dist"),
  publicOrigin: origin,
  accessToken: access,
  secureCookies: false,
  env: {
    KAREN_GATEWAY_URL: `ws://127.0.0.1:${wsAddress.port}`,
    OPENCLAW_GATEWAY_TOKEN: "synthetic-bootstrap-token",
  },
});
await new Promise<void>((resolve) =>
  runtime.server.listen(port, "127.0.0.1", resolve),
);
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
    : process.platform === "win32"
      ? {
          executablePath:
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        }
      : {}),
});
try {
  const page = await browser.newPage({
    viewport: { width: 1080, height: 760 },
  });
  page.setDefaultTimeout(12000);
  const errors: string[] = [];
  page.on("pageerror", (error) => {
    errors.push(error.message);
    console.error(error.message);
  });
  console.log("Checking browser login...");
  await page.goto(origin);
  await page.getByLabel("Token de acceso").fill(access);
  await page.getByRole("button", { name: "Entrar" }).click();
  console.log("Checking authenticated application...");
  console.log(
    "Page status:",
    page.url(),
    (await page.locator("body").innerText()).slice(0, 700),
  );
  page.on("console", (message) => {
    if (message.type() === "error") console.error("Browser:", message.text());
  });
  await page.waitForSelector("canvas");
  await page.getByText("Modo servidor · conexión", { exact: false }).waitFor();
  console.log("Checking Gateway connection...");
  await page.locator(".conversation-heading .connection.connected").waitFor();
  await page.getByLabel('Modelo de IA',{exact:true}).selectOption('cloud/test-large');
  await page.getByText('En uso: cloud/test-large',{exact:true}).waitFor();
  assert.equal(selectedModel,'cloud/test-large');
  await page.reload();
  await page.getByText('En uso: cloud/test-large',{exact:true}).waitFor();
  await page.getByLabel('Modelo de IA',{exact:true}).selectOption('');
  await page.getByText('En uso: local/test-small',{exact:true}).waitFor();
  assert.equal(selectedModel,null);
  await page
    .getByLabel("Mensaje para Karen", { exact: true })
    .fill("Prueba sintética del navegador");
  await page
    .getByRole("button", { name: "Enviar mensaje", exact: true })
    .click();
  await page
    .getByText("Respuesta sintética del contrato: conexión completa.", {
      exact: true,
    })
    .waitFor();
  assert.equal(await page.evaluate(() => document.cookie), "");
  await page
    .getByText("Prueba sintética del navegador", { exact: true })
    .waitFor();
  assert(
    !(await page
      .content()
      .then((html) => html.includes("synthetic-bootstrap-token"))),
  );
  assert.equal(errors.length, 0);
  mkdirSync("qa", { recursive: true });
  await page.screenshot({ path: "qa/server-browser.png" });
  writeFileSync(
    "qa/server-browser-results.json",
    JSON.stringify(
      {
        authenticated: true,
        httpOnlyCookie: true,
        gatewayContractFixture: true,
        realGateway: false,
        browserChatRoundTrip: true,
        browserModelSwitchAndReset: true,
        modelSelectionPersistsAcrossReload: true,
        rendererErrors: errors,
      },
      null,
      2,
    ),
  );
  console.log(
    "Server browser smoke passed: login, HttpOnly cookie, WebSocket adapter → SSE → UI response. Synthetic contract fixture only.",
  );
} finally {
  await browser.close();
  await runtime.close();
  for (const socket of fixture.clients) socket.terminate();
  await new Promise<void>((resolve) => fixture.close(() => resolve()));
  rmSync(root, { recursive: true, force: true });
}
