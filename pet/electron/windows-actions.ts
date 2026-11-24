import { spawn } from 'node:child_process';

export type ApprovedScreenAction = { x: number; y: number; text?: string };

const powershell = String.raw`
$ErrorActionPreference = 'Stop'
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
if ($request.x -lt -100000 -or $request.y -lt -100000 -or $request.x -gt 100000 -or $request.y -gt 100000) { throw 'Coordenadas fuera de rango.' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class KarenInput {
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public UIntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public UIntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Explicit)] public struct INPUTUNION { [FieldOffset(0)] public KEYBDINPUT ki; [FieldOffset(0)] public MOUSEINPUT mi; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public INPUTUNION U; }
  [DllImport("user32.dll", SetLastError=true)] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
  [DllImport("user32.dll", SetLastError=true)] public static extern uint SendInput(uint count, INPUT[] inputs, int size);
  public static void TypeChar(char value) {
    var down = new INPUT { type=1, U=new INPUTUNION { ki=new KEYBDINPUT { wScan=value, dwFlags=4 } } };
    var up = down; up.U.ki.dwFlags=6;
    if (SendInput(1, new INPUT[] { down }, Marshal.SizeOf(typeof(INPUT))) != 1 || SendInput(1, new INPUT[] { up }, Marshal.SizeOf(typeof(INPUT))) != 1)
      throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
  }
}
'@
if (-not [KarenInput]::SetCursorPos([int]$request.x, [int]$request.y)) { throw 'Windows no permitió mover el puntero.' }
[KarenInput]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
[KarenInput]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
if ($request.text) {
  Start-Sleep -Milliseconds 120
  foreach ($character in $request.text.ToCharArray()) { [KarenInput]::TypeChar($character) }
}
`;

/** Inject one already-approved click, optionally followed by the exact reviewed text. */
export function performApprovedScreenAction(action: ApprovedScreenAction): Promise<void> {
  if (process.platform !== 'win32') return Promise.reject(new Error('Las acciones de pantalla requieren Windows.'));
  if (!Number.isInteger(action.x) || !Number.isInteger(action.y) || action.x < -100000 || action.y < -100000 || action.x > 100000 || action.y > 100000)
    return Promise.reject(new Error('La posición de pantalla no es válida.'));
  if (action.text !== undefined && (typeof action.text !== 'string' || action.text.length < 1 || action.text.length > 500))
    return Promise.reject(new Error('El texto debe tener entre 1 y 500 caracteres.'));
  return new Promise((resolve, reject) => {
    const encoded = Buffer.from(powershell, 'utf16le').toString('base64');
    const child = spawn('powershell.exe', ['-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
    let stderr = '';
    const timeout = setTimeout(() => { child.kill(); reject(new Error('Windows tardó demasiado en completar la acción.')); }, 8000);
    child.stderr.setEncoding('utf8').on('data', chunk => { stderr = (stderr + chunk).slice(-1200); });
    child.once('error', error => { clearTimeout(timeout); reject(new Error(`No se pudo iniciar la acción de Windows: ${error.message}`)); });
    child.once('close', code => {
      clearTimeout(timeout);
      if (code === 0) resolve();
      else reject(new Error(stderr.trim().split(/\r?\n/).at(-1) || 'Windows no completó la acción.'));
    });
    child.stdin.end(JSON.stringify(action));
  });
}
