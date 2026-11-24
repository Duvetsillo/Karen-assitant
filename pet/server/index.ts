import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createKarenServer } from "./app.js";
import { secret } from "./storage.js";
const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error("PORT inválido.");
const directory = dirname(fileURLToPath(import.meta.url));
const runtime = createKarenServer({
  dataDirectory: resolve(process.env.KAREN_DATA_DIR || "data"),
  staticDirectory: resolve(directory, "../../dist"),
  publicOrigin: process.env.KAREN_PUBLIC_ORIGIN || `http://127.0.0.1:${port}`,
  accessToken: secret("KAREN_ACCESS_TOKEN"),
  secureCookies: process.env.KAREN_SECURE_COOKIES !== "false",
});
runtime.server.listen(port, process.env.HOST || "127.0.0.1", () =>
  console.log(
    `Karen server listening on port ${port}. No credentials are logged.`,
  ),
);
for (const signal of ["SIGTERM", "SIGINT"] as const)
  process.once(signal, () => {
    void runtime.close().then(() => process.exit(0));
  });
