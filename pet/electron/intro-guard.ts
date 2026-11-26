import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';

// Fixed, read-only Windows calls. No desktop capture or input injection.
const script = String.raw`
$ErrorActionPreference='Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class IntroGuard {
 [StructLayout(LayoutKind.Sequential)] public struct Rect { public int L,T,R,B; }
 [DllImport("shell32.dll")] public static extern int SHQueryUserNotificationState(out int state);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect r);
 [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr h, uint flags);
 [StructLayout(LayoutKind.Sequential)] public struct Monitor { public int Size; public Rect Bounds,Work; public uint Flags; }
 [DllImport("user32.dll")] public static extern bool GetMonitorInfo(IntPtr h, ref Monitor m);
 [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int key);
 [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
}
'@
[IntroGuard]::SetThreadDpiAwarenessContext([IntPtr](-4)) | Out-Null
while($true) {
 $state=0; $hr=[IntroGuard]::SHQueryUserNotificationState([ref]$state)
 $fg=[IntroGuard]::GetForegroundWindow(); $r=New-Object IntroGuard+Rect
 $m=New-Object IntroGuard+Monitor; $m.Size=[Runtime.InteropServices.Marshal]::SizeOf($m)
 $ok=[IntroGuard]::GetWindowRect($fg,[ref]$r) -and [IntroGuard]::GetMonitorInfo([IntroGuard]::MonitorFromWindow($fg,2),[ref]$m)
 $full=$ok -and $r.L -le $m.Bounds.L -and $r.T -le $m.Bounds.T -and $r.R -ge $m.Bounds.R -and $r.B -ge $m.Bounds.B
 $blocked=$hr -ne 0 -or $state -ne 5 -or $full
 $escape=([IntroGuard]::GetAsyncKeyState(27) -band 0x8000) -ne 0
 [Console]::WriteLine((@{blocked=[bool]$blocked;escape=[bool]$escape;state=$state;full=[bool]$full;foreground=$fg.ToInt64()}|ConvertTo-Json -Compress))
 [Console]::Out.Flush()
 Start-Sleep -Milliseconds 80
}
`;
export class IntroGuard {
  private child?: ChildProcessWithoutNullStreams;
  private timer?: ReturnType<typeof setTimeout>;
  private settle?: (safe: boolean) => void;
  private overlayExpected = false;
  expectOverlay() { this.overlayExpected = true; }
  start(onUnsafe: (reason?: string) => void, allowEscape: boolean): Promise<boolean> {
    if (process.platform !== 'win32') return Promise.resolve(false);
    return new Promise(resolve => {
      this.settle = resolve;
      let first = true, buffer = '', foreground: number | undefined;
      const finish = (safe: boolean) => { clearTimeout(this.timer); this.settle?.(safe); this.settle = undefined; };
      this.child = spawn('powershell.exe', ['-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', Buffer.from(script, 'utf16le').toString('base64')],
        { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
      this.timer = setTimeout(() => { finish(false); onUnsafe(); }, 6000);
      this.child.stdout.setEncoding('utf8').on('data', chunk => {
        buffer += chunk;
        if (buffer.length > 8192) { finish(false); onUnsafe(); return; }
        let end: number;
        while ((end = buffer.indexOf('\n')) >= 0) {
          const line = buffer.slice(0, end); buffer = buffer.slice(end + 1);
          try {
            const state = JSON.parse(line);
            // A full-monitor transparent topmost window itself makes Windows report
            // QUNS_BUSY. Exempt only that state while the original foreground stays
            // unchanged; fullscreen, D3D games, presentation and Escape still win.
            const ownBusy = !first && this.overlayExpected && state.state === 2 && state.full === false && state.foreground === foreground;
            const unsafe = (state.blocked !== false && !ownBusy) || (allowEscape && state.escape !== false);
            if (first) { first = false; foreground = state.foreground; finish(!unsafe); }
            else if (unsafe) onUnsafe(`Windows state=${state.state}, fullscreen=${state.full}, Escape=${state.escape}`);
          } catch { finish(false); onUnsafe(); }
        }
      });
      this.child.stderr.resume();
      this.child.once('error', () => { finish(false); onUnsafe(); });
      this.child.once('exit', () => { finish(false); onUnsafe(); });
    });
  }
  stop() {
    clearTimeout(this.timer); this.settle?.(false); this.settle = undefined;
    const child = this.child; this.child = undefined;
    child?.stdout.removeAllListeners('data');
    child?.removeAllListeners('exit');
    child?.removeAllListeners('error'); child?.on('error', () => {});
    child?.kill();
  }
}
