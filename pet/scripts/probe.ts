import { createConnection } from "node:net";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
const file =
  process.env.OPENCLAW_CONFIG_PATH ||
  join(homedir(), ".openclaw", "openclaw.json");
let cfg: Record<string, unknown> = {};
try {
  cfg = JSON.parse(readFileSync(file, "utf8"));
} catch {}
const gateway = cfg.gateway as
  | {
      port?: number;
      auth?: { mode?: string; token?: unknown; password?: unknown };
    }
  | undefined;
const port = gateway?.port ?? 18789;
const tcp = await new Promise<boolean>((resolve) => {
  const socket = createConnection({ host: "127.0.0.1", port });
  socket.setTimeout(3000);
  socket.once("connect", () => {
    socket.destroy();
    resolve(true);
  });
  socket.once("error", () => resolve(false));
  socket.once("timeout", () => {
    socket.destroy();
    resolve(false);
  });
});
console.log(
  JSON.stringify(
    {
      time: new Date().toISOString(),
      host: "127.0.0.1",
      port,
      tcp,
      authMode: gateway?.auth?.mode || "unknown",
      credentialPresent: Boolean(
        gateway?.auth?.token || gateway?.auth?.password,
      ),
      modifiedConfiguration: false,
      startedServices: false,
      note: tcp
        ? "El puerto responde; autentica desde la aplicación para verificar mensajes."
        : "Gateway inaccesible. No se verificaron autenticación ni mensajes con el asistente real.",
    },
    null,
    2,
  ),
);
