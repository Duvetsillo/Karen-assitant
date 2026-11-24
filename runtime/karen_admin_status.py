"""Report Windows elevation for OpenClaw processes without reading credentials."""
import ctypes
from ctypes import wintypes
import json
import subprocess


def process_elevated(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID,
                                          wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    process = kernel.OpenProcess(0x1000, False, pid)
    if not process:
        return None
    token = wintypes.HANDLE()
    try:
        if not advapi.OpenProcessToken(process, 0x0008, ctypes.byref(token)):
            return None
        value, size = wintypes.DWORD(), wintypes.DWORD()
        if not advapi.GetTokenInformation(token, 20, ctypes.byref(value), ctypes.sizeof(value), ctypes.byref(size)):
            return None
        return bool(value.value)
    finally:
        if token:
            kernel.CloseHandle(token)
        kernel.CloseHandle(process)


def main():
    # Unelevated CIM cannot read elevated command lines. The loopback listener
    # identifies the Gateway even when CommandLine is intentionally unavailable.
    command = r'''
    $adminRecords = @(Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" |
      Where-Object { $_.CommandLine -match 'openclaw' -and $_.CommandLine -match '(gateway|node run)' } |
      Select-Object ProcessId,@{Name='role';Expression={if($_.CommandLine -match 'gateway'){ 'gateway' }else{ 'node' }}})
    $adminListeners = @(Get-NetTCPConnection -LocalPort 18789 -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($adminPid in $adminListeners) {
      if ($adminRecords.ProcessId -notcontains $adminPid) {
        $adminRecords += [pscustomobject]@{ProcessId=$adminPid;role='gateway'}
      }
    }
    ConvertTo-Json -InputObject @($adminRecords) -Compress
    '''
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, timeout=15,
                            creationflags=0x08000000)
    if result.returncode:
        raise RuntimeError('No se pudieron consultar los procesos de OpenClaw.')
    records = json.loads(result.stdout or '[]')
    if isinstance(records, dict):
        records = [records]
    for record in records:
        record['elevated'] = process_elevated(record['ProcessId'])
    print(json.dumps({'processes': records}, ensure_ascii=True))


if __name__ == '__main__':
    main()
