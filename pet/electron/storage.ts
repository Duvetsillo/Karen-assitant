import { safeStorage } from "electron";
import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  existsSync,
  renameSync,
} from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import {
  createHash,
  generateKeyPairSync,
  createPublicKey,
  sign,
} from "node:crypto";
import type {
  DeviceIdentity,
  DeviceAuthTokenRecord,
  GatewayClientHostDeps,
} from "@openclaw/gateway-client";
import { defaults, validateSettings } from "../shared/settings.js";
import type { Settings } from "../shared/types.js";

interface Vault {
  identity?: DeviceIdentity;
  credentials: Record<string, string>;
  devices: Record<string, DeviceAuthTokenRecord>;
}
export class Storage {
  settings: Settings = { ...defaults };
  private vault: Vault = { credentials: {}, devices: {} };
  constructor(private directory: string) {
    mkdirSync(directory, { recursive: true });
    const settingsPath = join(directory, "settings.json");
    if (existsSync(settingsPath))
      this.settings = validateSettings(
        JSON.parse(readFileSync(settingsPath, "utf8")),
      );
    const secretPath = join(directory, "vault.dpapi");
    if (existsSync(secretPath))
      this.vault = JSON.parse(
        safeStorage.decryptString(readFileSync(secretPath)),
      );
  }
  private atomic(name: string, data: string | Buffer) {
    const file = join(this.directory, name);
    writeFileSync(file + ".tmp", data, { mode: 0o600 });
    renameSync(file + ".tmp", file);
  }
  saveSettings(patch: Partial<Settings>) {
    this.settings = validateSettings(patch, this.settings);
    this.atomic("settings.json", JSON.stringify(this.settings, null, 2));
    return this.settings;
  }
  private saveVault() {
    if (!safeStorage.isEncryptionAvailable())
      throw new Error(
        "Windows no permite cifrar las credenciales en esta sesión.",
      );
    this.atomic(
      "vault.dpapi",
      safeStorage.encryptString(JSON.stringify(this.vault)),
    );
  }
  setCredential(value: string) {
    if (value.length > 8192) throw new Error("Credencial demasiado larga.");
    if (value) this.vault.credentials[this.origin] = value;
    else delete this.vault.credentials[this.origin];
    this.saveVault();
  }
  get origin() {
    return new URL(this.settings.gatewayUrl).origin;
  }
  credential(): { token?: string; password?: string } {
    if (this.settings.authSource === "stored")
      return { token: this.vault.credentials[this.origin] };
    const url = new URL(this.settings.gatewayUrl);
    if (!["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))
      throw new Error(
        "La autenticación local solo se usa con el Gateway de este equipo. Guarda un token para el Gateway remoto.",
      );
    const path =
      process.env.OPENCLAW_CONFIG_PATH ||
      join(homedir(), ".openclaw", "openclaw.json");
    const cfg = JSON.parse(readFileSync(path, "utf8"));
    if (
      Number(url.port || (url.protocol === "wss:" ? 443 : 80)) !==
      Number(cfg.gateway?.port ?? 18789)
    )
      throw new Error(
        "El puerto no coincide con la configuración local de OpenClaw.",
      );
    const auth = cfg.gateway?.auth;
    if (auth?.mode === "password")
      return {
        password:
          process.env.OPENCLAW_GATEWAY_PASSWORD ||
          (typeof auth.password === "string" ? auth.password : undefined),
      };
    return {
      token:
        process.env.OPENCLAW_GATEWAY_TOKEN ||
        (typeof auth?.token === "string" ? auth.token : undefined),
    };
  }
  hasCredential() {
    try {
      const a = this.credential();
      return Boolean(a.token || a.password || this.vault.devices[this.origin]);
    } catch {
      return false;
    }
  }
  hostDeps(): GatewayClientHostDeps {
    const origin = this.origin;
    return {
      loadOrCreateDeviceIdentity: () => {
        if (!this.vault.identity) {
          const { publicKey, privateKey } = generateKeyPairSync("ed25519");
          const publicKeyPem = publicKey
            .export({ format: "pem", type: "spki" })
            .toString();
          const raw = publicKey
            .export({ format: "der", type: "spki" })
            .subarray(-32);
          this.vault.identity = {
            deviceId: createHash("sha256").update(raw).digest("hex"),
            publicKeyPem,
            privateKeyPem: privateKey
              .export({ format: "pem", type: "pkcs8" })
              .toString(),
          };
          this.saveVault();
        }
        return this.vault.identity;
      },
      signDevicePayload: (key, payload) =>
        sign(null, Buffer.from(payload), key).toString("base64url"),
      publicKeyRawBase64UrlFromPem: (key) =>
        createPublicKey(key)
          .export({ format: "der", type: "spki" })
          .subarray(-32)
          .toString("base64url"),
      loadDeviceAuthToken: () => this.vault.devices[origin] ?? null,
      storeDeviceAuthToken: (value) => {
        this.vault.devices[origin] = {
          token: value.token,
          scopes: value.scopes,
        };
        this.saveVault();
      },
      clearDeviceAuthToken: () => {
        delete this.vault.devices[origin];
        this.saveVault();
      },
      logDebug: () => {},
      logError: () => {},
    };
  }
}
