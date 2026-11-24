const fs = require('node:fs');
const path = require('node:path');
const { tmpdir } = require('node:os');

/** Disposable, silent QA profile. Cleanup checks the resolved deletion boundary. */
function createCoreQaProfile(prefix) {
  if (!/^karen-native-[a-z-]+-$/.test(prefix)) throw new Error('Prefijo QA inválido');
  const root = fs.realpathSync(tmpdir());
  const directory = fs.mkdtempSync(path.join(root, prefix));
  const profile = path.join(directory, 'profile');
  fs.mkdirSync(profile);
  fs.writeFileSync(path.join(profile, 'settings.json'), JSON.stringify({
    sttEnabled: false, wakeWordEnabled: false, voiceEnabled: false,
  }));
  return { directory, profile, cleanup() {
    if (!fs.existsSync(directory)) return;
    const target = fs.realpathSync(directory);
    if (path.dirname(target) !== root || !path.basename(target).startsWith(prefix))
      throw new Error('Límite de borrado QA inválido');
    fs.rmSync(target, { recursive: true, force: true, maxRetries: 20, retryDelay: 100 });
  } };
}
module.exports = { createCoreQaProfile };
