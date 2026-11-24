param([switch]$NoOpen)
$ErrorActionPreference = 'Stop'
$jarvisUrl = 'http://127.0.0.1:18793/jarvis'
$jarvisLock = [System.Threading.Mutex]::new($false, 'Local\KarenJarvisLaunch')
$jarvisOwnsLock = $false

function Test-KarenJarvis {
    try {
        $page = Invoke-WebRequest -Uri $jarvisUrl -TimeoutSec 2 -UseBasicParsing
        return $page.StatusCode -eq 200 -and $page.Content -match 'id="workbench"'
    } catch { return $false }
}

try {
    $jarvisOwnsLock = $jarvisLock.WaitOne(30000)
    if (-not $jarvisOwnsLock) { throw 'Karen está iniciándose. Vuelve a abrir el acceso directo en unos segundos.' }
    if (-not (Test-KarenJarvis)) {
        # Never stop or replace an unrelated listener on the existing mobile port.
        if (Get-NetTCPConnection -State Listen -LocalPort 18793 -ErrorAction SilentlyContinue) {
            throw 'El puerto 18793 está ocupado y no responde como Karen. Revisa el servidor móvil.'
        }
        $jarvisPython = (Get-Command python -ErrorAction Stop).Source
        $jarvisArguments = @(('"' + (Join-Path $PSScriptRoot 'mobile_server.py') + '"'), 'serve')
        if (Get-Command tailscale -ErrorAction SilentlyContinue) {
            try {
                $jarvisTailnet = tailscale status --json 2>$null | ConvertFrom-Json
                $jarvisDns = $jarvisTailnet.Self.DNSName.TrimEnd('.')
                $jarvisIp = @($jarvisTailnet.Self.TailscaleIPs | Where-Object { $_ -match '^100\.\d+\.\d+\.\d+$' }) | Select-Object -First 1
                if ($jarvisTailnet.BackendState -eq 'Running' -and $jarvisDns -match '^[a-zA-Z0-9.-]+$') {
                    $jarvisArguments += @('--origin', "https://$jarvisDns")
                    if ($jarvisIp) { $jarvisArguments += @('--tailnet-origin', "http://${jarvisIp}:18795") }
                }
            } catch { <# Local desktop access remains available without Tailscale. #> }
        }
        $jarvisPrivate = Join-Path $PSScriptRoot '.private'
        New-Item -ItemType Directory -Path $jarvisPrivate -Force | Out-Null
        Start-Process -FilePath $jarvisPython -ArgumentList $jarvisArguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $jarvisPrivate 'jarvis-server.stdout.log') -RedirectStandardError (Join-Path $jarvisPrivate 'jarvis-server.stderr.log') | Out-Null
        $jarvisReady = $false
        for ($jarvisAttempt = 0; $jarvisAttempt -lt 20; $jarvisAttempt++) {
            if (Test-KarenJarvis) { $jarvisReady = $true; break }
            Start-Sleep -Milliseconds 500
        }
        if (-not $jarvisReady) { throw 'Karen no inició. Revisa .private\jarvis-server.stderr.log en la carpeta del proyecto.' }
    }
    if (-not $NoOpen) {
        $jarvisEdge = @(
            (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
            (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe')
        ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if ($jarvisEdge) { Start-Process -FilePath $jarvisEdge -ArgumentList "--app=$jarvisUrl",'--start-maximized' }
        else { Start-Process $jarvisUrl }
    }
    Write-Output 'Karen Jarvis lista en http://127.0.0.1:18793/jarvis'
} catch {
    if (-not $NoOpen) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Karen Jarvis') | Out-Null
    }
    throw
} finally {
    if ($jarvisOwnsLock) { $jarvisLock.ReleaseMutex() }
    $jarvisLock.Dispose()
}
