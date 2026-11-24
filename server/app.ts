import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { readFileSync, statSync } from "node:fs";
import { extname, resolve, sep } from "node:path";
import { OpenClawAdapter } from "../electron/gateway.js";
import type {
  DesktopEvent,
  Diagnostic,
  Snapshot,
  Settings,
} from "../shared/types.js";
import { PET_STATES } from "../shared/types.js";
import { ServerStorage } from "./storage.js";
import { APP_VERSION } from "../shared/version.js";

export interface ServerOptions {
  dataDirectory: string;
  staticDirectory: string;
  publicOrigin: string;
  accessToken: string;
  secureCookies?: boolean;
  env?: NodeJS.ProcessEnv;
  autoConnect?: boolean;
}
const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".svg": "image/svg+xml",
};
const loginHtml = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Karen · Acceso</title></head><body><main><h1>Karen</h1><p>Introduce el token de acceso de tu servidor. No es el token del Gateway de OpenClaw.</p><form method="post" action="/login"><label>Token de acceso <input name="token" type="password" required autocomplete="current-password"></label><button>Entrar</button></form></main></body></html>`;
export function createKarenServer(options: ServerOptions) {
  if (options.accessToken.length < 32)
    throw new Error(
      "KAREN_ACCESS_TOKEN debe tener al menos 32 caracteres aleatorios.",
    );
  const origin = new URL(options.publicOrigin);
  if (
    !["http:", "https:"].includes(origin.protocol) ||
    origin.username ||
    origin.password ||
    origin.search ||
    origin.hash ||
    origin.pathname !== "/"
  )
    throw new Error(
      "KAREN_PUBLIC_ORIGIN debe ser un origen HTTP/HTTPS sin ruta ni credenciales.",
    );
  const expectedOrigin = origin.origin;
  const secure = options.secureCookies ?? true;
  if (!secure && !["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname))
    throw new Error(
      "Las cookies sin HTTPS solo se permiten para pruebas loopback.",
    );
  const storage = new ServerStorage(options.dataDirectory, options.env);
  const sessions = new Map<string, number>();
  const attempts = new Map<string, { count: number; until: number }>();
  const streams = new Map<ServerResponse, number>();
  const diagnostics: Diagnostic[] = [];
  const secrets = [
    options.accessToken,
    ...Object.values(storage.credential()),
  ].filter((value): value is string => Boolean(value));
  function emit(event: DesktopEvent) {
    const frame = `data: ${JSON.stringify(event)}\n\n`;
    for (const [stream, expires] of streams) {
      if (expires < Date.now() || stream.writableLength > 65536) {
        stream.end();
        streams.delete(stream);
      } else stream.write(frame);
    }
  }
  function log(level: Diagnostic["level"], area: string, message: string) {
    for (const value of secrets)
      message = message.split(value).join("[oculto]");
    message = message
      .replace(/(Bearer\s+)[^\s]+/gi, "$1[oculto]")
      .replace(
        /(token|password|secret)\s*[:=]\s*["']?[^\s,"']+/gi,
        "$1=[oculto]",
      );
    const item: Diagnostic = {
      time: Date.now(),
      level,
      area,
      message: message.slice(0, 1600),
    };
    diagnostics.push(item);
    if (diagnostics.length > 120) diagnostics.shift();
    emit({ type: "diagnostic", item });
  }
  const gateway = new OpenClawAdapter(storage, emit, log);
  const server = createServer((request, response) => {
    void route(request, response).catch(() => {
      if (!response.headersSent)
        json(response, 500, {
          error:
            "No se pudo completar la operación. Revisa la configuración del servidor.",
        });
      else response.end();
    });
  });
  function json(response: ServerResponse, status: number, value: unknown) {
    response.writeHead(status, {
      "Content-Type": "application/json; charset=utf-8",
    });
    response.end(JSON.stringify(value));
  }
  async function body(request: IncomingMessage): Promise<string> {
    let size = 0;
    const chunks: Buffer[] = [];
    for await (const part of request) {
      const chunk = Buffer.from(part);
      size += chunk.length;
      if (size > 65536) throw new Error("Solicitud demasiado grande.");
      chunks.push(chunk);
    }
    return Buffer.concat(chunks).toString("utf8");
  }
  async function route(request: IncomingMessage, response: ServerResponse) {
    response.setHeader("Cache-Control", "no-store");
    response.setHeader("X-Content-Type-Options", "nosniff");
    response.setHeader("Referrer-Policy", "same-origin");
    response.setHeader(
      "Content-Security-Policy",
      "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
    );
    if (request.headers.host !== origin.host) {
      json(response, 403, { error: "Host no autorizado." });
      return;
    }
    const url = new URL(request.url || "/", expectedOrigin);
    if (url.pathname === "/healthz" && request.method === "GET") {
      json(response, 200, { status: "ok" });
      return;
    }
    if (
      request.method === "POST" &&
      request.headers.origin !== expectedOrigin
    ) {
      json(response, 403, { error: "Origen no autorizado." });
      return;
    }
    const now = Date.now();
    for (const [key, expires] of sessions)
      if (expires < now) sessions.delete(key);
    if (url.pathname === "/login" && request.method === "POST") {
      const address = request.socket.remoteAddress || "local";
      for (const [key, attempt] of attempts)
        if (attempt.until < now) attempts.delete(key);
      const attempt = attempts.get(address) || { count: 0, until: now + 60000 };
      attempt.count++;
      attempts.set(address, attempt);
      if (attempt.count > 10 || attempts.size > 1000) {
        json(response, 429, {
          error: "Demasiados intentos; espera un minuto.",
        });
        return;
      }
      const token = new URLSearchParams(await body(request)).get("token") || "";
      if (
        !timingSafeEqual(
          createHash("sha256").update(token).digest(),
          createHash("sha256").update(options.accessToken).digest(),
        )
      ) {
        json(response, 401, { error: "Acceso no autorizado." });
        return;
      }
      if (sessions.size >= 1000) {
        json(response, 503, { error: "Demasiadas sesiones activas." });
        return;
      }
      const session = randomBytes(32).toString("hex");
      sessions.set(session, now + 8 * 60 * 60 * 1000);
      response.writeHead(303, {
        Location: "/?view=settings",
        "Set-Cookie": `karen_session=${session}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800${secure ? "; Secure" : ""}`,
      });
      response.end();
      return;
    }
    const cookie = request.headers.cookie
      ?.split(";")
      .map((v) => v.trim())
      .find((v) => v.startsWith("karen_session="))
      ?.slice("karen_session=".length);
    const expires = cookie ? sessions.get(cookie) : undefined;
    if (!expires) {
      if (url.pathname.startsWith("/api/"))
        json(response, 401, { error: "Inicia sesión para continuar." });
      else {
        response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        response.end(loginHtml);
      }
      return;
    }
    if (url.pathname === "/api/events" && request.method === "GET") {
      if (streams.size >= 50) {
        json(response, 503, { error: "Demasiadas conexiones de eventos." });
        return;
      }
      response.writeHead(200, {
        "Content-Type": "text/event-stream",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      });
      response.write(": connected\n\n");
      streams.set(response, expires);
      request.on("close", () => streams.delete(response));
      return;
    }
    if (url.pathname === "/api/snapshot" && request.method === "GET") {
      const snapshot: Snapshot = {
        settings: storage.settings,
        connection: gateway.info,
        diagnostics: [...diagnostics],
        messages: gateway.messages,
        hasCredential: Boolean(
          Object.values(storage.credential()).some(Boolean),
        ),
        native: false,
        runtime: "server",
        version: APP_VERSION,
      };
      json(response, 200, snapshot);
      return;
    }
    if (url.pathname.startsWith("/api/") && request.method === "POST") {
      if (request.headers["x-karen-client"] !== "browser") {
        json(response, 403, { error: "Cabecera de cliente requerida." });
        return;
      }
      const payload = JSON.parse((await body(request)) || "{}") as Record<
        string,
        unknown
      >;
      try {
        switch (url.pathname) {
          case '/api/models':
            json(response, 200, await gateway.models());
            return;
          case '/api/select-model':
            json(response, 200, await gateway.selectModel(payload.model));
            return;
          case "/api/settings": {
            if (
              !payload.patch ||
              typeof payload.patch !== "object" ||
              Array.isArray(payload.patch)
            )
              throw new Error("Ajustes inválidos.");
            const settings = storage.saveSettings(
              payload.patch as Partial<Settings>,
            );
            emit({ type: "settings", settings });
            json(response, 200, settings);
            return;
          }
          case "/api/send":
            if (typeof payload.text !== "string")
              throw new Error("Mensaje inválido.");
            await gateway.send(payload.text);
            break;
          case "/api/connect":
            await gateway.connect();
            break;
          case "/api/disconnect":
            gateway.disconnect();
            break;
          case "/api/abort":
            await gateway.abort();
            break;
          case "/api/demo":
            if (!PET_STATES.includes(payload.state as never))
              throw new Error("Estado inválido.");
            emit({
              type: "pet",
              state: payload.state as (typeof PET_STATES)[number],
              reason: "Demostración visual local",
            });
            break;
          default:
            json(response, 501, {
              error:
                "Esta función requiere Windows o un adaptador de voz externo; no está configurada en este servidor.",
            });
            return;
        }
        json(response, 200, {});
      } catch {
        json(response, 400, {
          error:
            "No se pudo ejecutar la acción. Revisa la conexión, el diagnóstico y la configuración del servidor.",
        });
      }
      return;
    }
    if (request.method !== "GET") {
      json(response, 405, { error: "Método no permitido." });
      return;
    }
    const root = resolve(options.staticDirectory);
    const pathname = decodeURIComponent(url.pathname);
    const file = resolve(
      root,
      pathname === "/" ? "index.html" : "." + pathname,
    );
    if (!file.startsWith(root + sep)) {
      json(response, 403, { error: "Ruta no permitida." });
      return;
    }
    try {
      if (!statSync(file).isFile()) {
        json(response, 404, { error: "No encontrado." });
        return;
      }
      let content = readFileSync(file);
      if (extname(file) === ".html")
        content = Buffer.from(
          content
            .toString("utf8")
            .replace(
              "<head>",
              '<head><meta name="karen-runtime" content="server"/>',
            ),
        );
      response.writeHead(200, {
        "Content-Type": MIME[extname(file)] || "application/octet-stream",
      });
      response.end(content);
    } catch {
      json(response, 404, { error: "No encontrado." });
    }
  }
  const heartbeat = setInterval(() => {
    for (const [stream, expires] of streams) {
      if (expires < Date.now() || stream.destroyed) {
        stream.end();
        streams.delete(stream);
      } else stream.write(": keep-alive\n\n");
    }
  }, 15000);
  heartbeat.unref();
  async function close() {
    gateway.disconnect(false);
    clearInterval(heartbeat);
    for (const stream of streams.keys()) stream.end();
    streams.clear();
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
      server.closeAllConnections();
    });
  }
  if (options.autoConnect !== false)
    void gateway
      .connect()
      .catch(() =>
        log(
          "error",
          "OpenClaw",
          "No se pudo iniciar la conexión con el Gateway.",
        ),
      );
  return { server, gateway, storage, close };
}
