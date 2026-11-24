const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const files = execFileSync(
  "git",
  ["ls-files", "--cached", "--others", "--exclude-standard", "-z"],
  { encoding: "utf8" },
)
  .split("\0")
  .filter(Boolean);
const forbidden =
  /(^|\/)(?:data|secrets|\.qa-profile|\.private|node_modules|release|qa)(?:\/|$)|(?:^|\/)\.env$|\.(?:dpapi|pem|key|wav|sqlite3?)$/i;
const patterns = [
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /\bgh[pousr]_[A-Za-z0-9]{30,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{30,}\b/,
  /\bsk-[A-Za-z0-9]{32,}\b/,
];
const issues = [];
for (const file of files) {
  if (forbidden.test(file)) {
    issues.push(file);
    continue;
  }
  if (!fs.existsSync(file) || /\.(png|ico)$/.test(file)) continue;
  const text = fs.readFileSync(file, "utf8");
  if (patterns.some((pattern) => pattern.test(text))) issues.push(file);
}
if (issues.length) {
  console.error(
    "Potential private material in source paths:",
    [...new Set(issues)].join(", "),
  );
  process.exitCode = 1;
} else
  console.log(
    `Source audit passed: ${files.length} paths; no matching secrets or runtime data.`,
  );
