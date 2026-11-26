const { execFileSync } = require('node:child_process');
const { existsSync, mkdirSync, readdirSync } = require('node:fs');
const path = require('node:path');
if (process.platform !== 'win32') { console.log('Puente GSMTC: compilación disponible en Windows.'); process.exit(0); }
const windows = process.env.WINDIR || 'C:\\Windows';
const framework = path.join(windows, 'Microsoft.NET/Framework64/v4.0.30319');
const gac = name => {
  const root = path.join(windows, 'Microsoft.NET/assembly/GAC_MSIL', name);
  const version = readdirSync(root).find(v => v.startsWith('v4.0_4.0.0.0_'));
  if (!version) throw new Error(`Falta el ensamblado de Windows ${name}.`);
  return path.join(root, version, `${name}.dll`);
};
const fixture = process.argv.includes('--fixture');
const output = fixture ? 'qa/music/KarenMusicFixture.exe' : 'dist-native/KarenMusicBridge.exe';
mkdirSync(path.dirname(output), { recursive: true });
const references = ['Windows.Media', 'Windows.Foundation', 'Windows.Storage'].map(name => path.join(windows, 'System32/WinMetadata', `${name}.winmd`));
references.push(path.join(framework, 'System.Runtime.WindowsRuntime.dll'), gac('System.Runtime'), path.join(framework, 'System.Web.Extensions.dll'));
if (!references.every(existsSync)) throw new Error('Faltan contratos WinRT del sistema.');
execFileSync(path.join(framework, 'csc.exe'), ['/nologo', '/target:exe', '/optimize+', `/out:${path.resolve(output)}`, ...references.map(r => `/r:${r}`), path.resolve(fixture ? 'native/music/MusicFixture.cs' : 'native/music/MusicBridge.cs')], { stdio: 'inherit', windowsHide: true });
console.log('Puente GSMTC compilado con .NET de Windows, sin SDK adicional.');
