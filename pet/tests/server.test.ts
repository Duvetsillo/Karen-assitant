import { afterEach, describe, expect, it } from "vitest";
import { request as httpRequest } from "node:http";
import {
  mkdtempSync,
  readFileSync,
  rmSync,
  mkdirSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createKarenServer } from "../server/app";
import { ServerStorage } from "../server/storage";
const accessToken = "test-only-browser-token-32-characters-minimum";
const gatewayToken = "test-only-gateway-bootstrap-secret";
const roots: string[] = [];
const runtimes: ReturnType<typeof createKarenServer>[] = [];
afterEach(async () => {
  for (const runtime of runtimes.splice(0)) await runtime.close();
  for (const root of roots.splice(0))
    rmSync(root, { recursive: true, force: true });
});
function directory() {
  const path = mkdtempSync(join(tmpdir(), "karen-server-test-"));
  roots.push(path);
  return path;
}
async function setup() {
  const root = directory();
  const site = join(root, "site");
  mkdirSync(site);
  writeFileSync(
    join(site, "index.html"),
    "<html><head></head><body>Karen</body></html>",
  );
  const runtime = createKarenServer({
    dataDirectory: join(root, "data"),
    staticDirectory: site,
    publicOrigin: "http://localhost",
    accessToken,
    secureCookies: false,
    autoConnect: false,
    env: {
      KAREN_GATEWAY_URL: "ws://127.0.0.1:18789",
      OPENCLAW_GATEWAY_TOKEN: gatewayToken,
    },
  });
  runtimes.push(runtime);
  await new Promise<void>((resolve) =>
    runtime.server.listen(0, "127.0.0.1", resolve),
  );
  const address = runtime.server.address();
  if (!address || typeof address === "string") throw new Error("Sin puerto");
  const call = (
    path: string,
    options: {
      method?: string;
      body?: unknown;
      cookie?: string;
      origin?: string;
      client?: boolean;
      host?: string;
      form?: boolean;
    } = {},
  ) =>
    new Promise<{
      status: number;
      headers: import("node:http").IncomingHttpHeaders;
      text: string;
    }>((resolve) => {
      const raw =
        options.body === undefined
          ? ""
          : options.form
            ? String(options.body)
            : JSON.stringify(options.body);
      const req = httpRequest(
        {
          hostname: "127.0.0.1",
          port: address.port,
          path,
          method: options.method || "GET",
          headers: {
            Host: options.host || "localhost",
            ...(options.origin ? { Origin: options.origin } : {}),
            ...(options.cookie ? { Cookie: options.cookie } : {}),
            ...(options.client ? { "X-Karen-Client": "browser" } : {}),
            ...(raw
              ? {
                  "Content-Type": options.form
                    ? "application/x-www-form-urlencoded"
                    : "application/json",
                  "Content-Length": Buffer.byteLength(raw),
                }
              : {}),
          },
        },
        (response) => {
          let text = "";
          response.setEncoding("utf8");
          response.on("data", (part) => (text += part));
          response.on("end", () =>
            resolve({
              status: response.statusCode || 0,
              headers: response.headers,
              text,
            }),
          );
        },
      );
      req.end(raw);
    });
  const login = async () => {
    const response = await call("/login", {
      method: "POST",
      form: true,
      body: new URLSearchParams({ token: accessToken }).toString(),
      origin: "http://localhost",
    });
    expect(response.status).toBe(303);
    return response.headers["set-cookie"]![0].split(";")[0];
  };
  return { runtime, call, login, root };
}
describe("servidor autónomo", () => {
  it('protege el selector de modelos con sesión, origen y cabecera de cliente', async () => {
    const t = await setup();
    for (const path of ['/api/models', '/api/select-model']) {
      expect((await t.call(path, {method:'POST', origin:'http://localhost', client:true, body:{model:null}})).status).toBe(401);
      const cookie = await t.login();
      expect((await t.call(path, {method:'POST', origin:'https://attacker.example', cookie, client:true, body:{model:null}})).status).toBe(403);
      expect((await t.call(path, {method:'POST', origin:'http://localhost', cookie, body:{model:null}})).status).toBe(403);
      expect((await t.call(path, {method:'POST', origin:'http://localhost', cookie, client:true, body:{model:null}})).status).toBe(400);
    }
  });
  it("exige autenticación y separa el token del Gateway del acceso al navegador", async () => {
    const t = await setup();
    expect((await t.call("/healthz")).status).toBe(200);
    expect((await t.call("/api/snapshot")).status).toBe(401);
    expect((await t.call("/")).text).toContain('type="password"');
    const rejected = await t.call("/login", {
      method: "POST",
      form: true,
      origin: "http://localhost",
      body: new URLSearchParams({ token: gatewayToken }).toString(),
    });
    expect(rejected.status).toBe(401);
    const cookie = await t.login();
    const snapshot = await t.call("/api/snapshot", { cookie });
    expect(snapshot.status).toBe(200);
    expect(snapshot.text).not.toContain(gatewayToken);
    expect(snapshot.text).not.toContain(accessToken);
    expect(JSON.parse(snapshot.text).runtime).toBe("server");
    expect((await t.call("/", { cookie })).text).toContain(
      'name="karen-runtime" content="server"',
    );
  });
  it("bloquea CSRF, Host ajeno y modificación del destino autenticado", async () => {
    const t = await setup(),
      cookie = await t.login();
    expect(
      (await t.call("/healthz", { host: "attacker.example" })).status,
    ).toBe(403);
    expect(
      (
        await t.call("/api/demo", {
          method: "POST",
          cookie,
          origin: "https://attacker.example",
          client: true,
          body: { state: "HAPPY" },
        })
      ).status,
    ).toBe(403);
    expect(
      (
        await t.call("/api/demo", {
          method: "POST",
          cookie,
          origin: "http://localhost",
          body: { state: "HAPPY" },
        })
      ).status,
    ).toBe(403);
    expect(
      (
        await t.call("/api/settings", {
          method: "POST",
          cookie,
          origin: "http://localhost",
          client: true,
          body: { patch: { gatewayUrl: "wss://attacker.example" } },
        })
      ).status,
    ).toBe(400);
    expect(
      (
        await t.call("/api/settings", {
          method: "POST",
          cookie,
          origin: "http://localhost",
          client: true,
          body: { patch: { brightness: 0.7 } },
        })
      ).status,
    ).toBe(200);
    expect(
      (
        await t.call("/api/send", {
          method: "POST",
          cookie,
          origin: "http://localhost",
          client: true,
          body: { text: "Hola" },
        })
      ).status,
    ).toBe(400);
  });
  it("limita intentos de acceso y no finge funciones nativas", async () => {
    const t = await setup(),
      cookie = await t.login();
    expect(
      (
        await t.call("/api/synthesize", {
          method: "POST",
          cookie,
          origin: "http://localhost",
          client: true,
          body: {},
        })
      ).status,
    ).toBe(501);
    for (let i = 0; i < 10; i++)
      await t.call("/login", {
        method: "POST",
        origin: "http://localhost",
        form: true,
        body: "token=wrong",
      });
    expect(
      (
        await t.call("/login", {
          method: "POST",
          origin: "http://localhost",
          form: true,
          body: "token=wrong",
        })
      ).status,
    ).toBe(429);
  });
  it("cifra y restaura la identidad de dispositivo sin guardar el bootstrap", () => {
    const root = directory(),
      env = {
        KAREN_GATEWAY_URL: "wss://gateway.example",
        OPENCLAW_GATEWAY_TOKEN: gatewayToken,
      };
    const storage = new ServerStorage(root, env);
    const host = storage.hostDeps();
    const identity = host.loadOrCreateDeviceIdentity!()!;
    host.storeDeviceAuthToken!({
      deviceId: identity.deviceId,
      role: "operator",
      token: "test-only-device-secret",
      scopes: ["operator.read"],
    });
    const encrypted = readFileSync(join(root, "vault.enc"));
    expect(encrypted.includes(Buffer.from(identity.privateKeyPem))).toBe(false);
    expect(encrypted.includes(Buffer.from(gatewayToken))).toBe(false);
    const restored = new ServerStorage(root, env);
    expect(restored.hostDeps().loadOrCreateDeviceIdentity!()?.deviceId).toBe(
      identity.deviceId,
    );
    expect(
      restored.hostDeps().loadDeviceAuthToken!({
        deviceId: identity.deviceId,
        role: "operator",
      })?.token,
    ).toBe("test-only-device-secret");
    const changed = new ServerStorage(root, {
      ...env,
      KAREN_GATEWAY_URL: "wss://another.example",
    });
    expect(
      changed.hostDeps().loadDeviceAuthToken!({
        deviceId: identity.deviceId,
        role: "operator",
      }),
    ).toBe(null);
  });
});
