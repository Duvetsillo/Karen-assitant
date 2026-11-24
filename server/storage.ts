import {
  createCipheriv,
  createDecipheriv,
  createHash,
  createPublicKey,
  generateKeyPairSync,
  randomBytes,
  sign,
} from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  renameSync,
} from "node:fs";
import { join } from "node:path";
import type {
  DeviceIdentity,
  DeviceAuthTokenRecord,
  GatewayClientHostDeps,
} from "@openclaw/gateway-client";
import type { Settings } from "../shared/types.js";
import {
  defaults,
  validateSettings,
  gatewayAddress,
} from "../shared/settings.js";
import type { GatewayStorage } from "../electron/gateway.js";

export function secret(
  name: string,
  env: NodeJS.ProcessEnv = process.env,
): string {
  const file = env[`${name}_FILE`];
  return (file ? readFileSync(file, "utf8") : env[name] || "").trim();
}
interface Vault {
  identity?: DeviceIdentity;
  device?: DeviceAuthTokenRecord;
  origin?: string;
}
export class ServerStorage implements GatewayStorage {
  settings: Settings;
  private key: Buffer;
  private vault: Vault = {};
  private readonly endpoint: string;
  private readonly agent: string;
  constructor(
    private directory: string,
    private env: NodeJS.ProcessEnv = process.env,
  ) {
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    this.endpoint = gatewayAddress(
      env.KAREN_GATEWAY_URL || "ws://127.0.0.1:18789",
    );
    this.agent = env.KAREN_AGENT_ID || "main";
    const saved = existsSync(join(directory, "settings.json"))
      ? JSON.parse(readFileSync(join(directory, "settings.json"), "utf8"))
      : {};
    this.settings = validateSettings(
      {
        ...saved,
        gatewayUrl: this.endpoint,
        agentId: this.agent,
        authSource: "stored",
        autoStart: false,
        sttEnabled: false,
      },
      defaults,
    );
    this.settings.voiceEnabled = false;
    const keyFile = join(directory, "vault.key");
    if (!existsSync(keyFile))
      writeFileSync(keyFile, randomBytes(32), { mode: 0o600, flag: "wx" });
    this.key = readFileSync(keyFile);
    if (this.key.length !== 32)
      throw new Error("La clave del almacén del servidor no es válida.");
    const file = join(directory, "vault.enc");
    if (existsSync(file)) {
      const bytes = readFileSync(file);
      const decipher = createDecipheriv(
        "aes-256-gcm",
        this.key,
        bytes.subarray(0, 12),
      );
      decipher.setAuthTag(bytes.subarray(12, 28));
      this.vault = JSON.parse(
        Buffer.concat([
          decipher.update(bytes.subarray(28)),
          decipher.final(),
        ]).toString("utf8"),
      );
      if (this.vault.origin !== new URL(this.endpoint).origin)
        this.vault.device = undefined;
    }
  }
  private save() {
    const iv = randomBytes(12);
    const cipher = createCipheriv("aes-256-gcm", this.key, iv);
    const encrypted = Buffer.concat([
      cipher.update(JSON.stringify(this.vault), "utf8"),
      cipher.final(),
    ]);
    const file = join(this.directory, "vault.enc");
    writeFileSync(
      file + ".tmp",
      Buffer.concat([iv, cipher.getAuthTag(), encrypted]),
      { mode: 0o600 },
    );
    renameSync(file + ".tmp", file);
  }
  credential() {
    return {
      token: secret("OPENCLAW_GATEWAY_TOKEN", this.env) || undefined,
      password: secret("OPENCLAW_GATEWAY_PASSWORD", this.env) || undefined,
    };
  }
  saveSettings(patch: Partial<Settings>) {
    for (const key of [
      "gatewayUrl",
      "agentId",
      "authSource",
      "autoStart",
      "alwaysOnTop",
      "sttEnabled",
      "ttsEngine",
    ] as const) {
      if (patch[key] !== undefined && patch[key] !== this.settings[key])
        throw new Error(
          "La conexión y las funciones nativas se configuran en el servidor, no desde el navegador.",
        );
    }
    if (patch.voiceEnabled === true)
      throw new Error("El modo servidor no tiene motor de voz configurado.");
    this.settings = validateSettings(patch, this.settings);
    const file = join(this.directory, "settings.json");
    writeFileSync(file + ".tmp", JSON.stringify(this.settings, null, 2), {
      mode: 0o600,
    });
    renameSync(file + ".tmp", file);
    return this.settings;
  }
  hostDeps(): GatewayClientHostDeps {
    return {
      loadOrCreateDeviceIdentity: () => {
        if (!this.vault.identity) {
          const { publicKey, privateKey } = generateKeyPairSync("ed25519");
          this.vault.identity = {
            deviceId: createHash("sha256")
              .update(
                publicKey.export({ format: "der", type: "spki" }).subarray(-32),
              )
              .digest("hex"),
            publicKeyPem: publicKey
              .export({ format: "pem", type: "spki" })
              .toString(),
            privateKeyPem: privateKey
              .export({ format: "pem", type: "pkcs8" })
              .toString(),
          };
          this.save();
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
      loadDeviceAuthToken: () => this.vault.device || null,
      storeDeviceAuthToken: (value) => {
        this.vault.device = { token: value.token, scopes: value.scopes };
        this.vault.origin = new URL(this.endpoint).origin;
        this.save();
      },
      clearDeviceAuthToken: () => {
        this.vault.device = undefined;
        this.save();
      },
      logDebug: () => {},
      logError: () => {},
    };
  }
}
