param(
    [ValidateSet('pc', 'homelab', 'karen')][string]$Profile,
    [string]$Server,
    [ValidateSet('tiny','base','small','medium','large')][string]$WhisperModel,
    [string]$InputDevice,
    [switch]$NoWakeWord,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$settingsPath = Join-Path $PSScriptRoot 'settings.json'
$configuredServer = if ($Server) { $Server } elseif ($Profile -in @('pc', 'homelab', 'karen')) {
    if ($Profile -eq 'pc') { 'http://127.0.0.1:11434' } else { '' }
} elseif (Test-Path -LiteralPath $settingsPath) {
    (Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json).server
} else { 'http://127.0.0.1:11434' }
# Core 2 overrides inference at runtime; saved legacy targets remain untouched.
$configuredServer = 'http://127.0.0.1:11434'
if ($configuredServer -match '^https?://(127\.0\.0\.1|localhost):11434/?$') {
    $healthy = $false
    try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2; $healthy = $true } catch {}
    if (-not $healthy) {
        $env:OLLAMA_MAX_LOADED_MODELS = '1'
        $env:OLLAMA_NUM_PARALLEL = '1'
        $ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
        if (-not $ollama) { throw 'Ollama no está instalado. Karen necesita Ollama local para conversar.' }
        $null = New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot '.private')
        Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $PSScriptRoot '.private\ollama-serve.out.log') `
            -RedirectStandardError (Join-Path $PSScriptRoot '.private\ollama-serve.err.log')
        for ($attempt = 0; $attempt -lt 15; $attempt++) {
            Start-Sleep -Seconds 1
            try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2; $healthy = $true; break } catch {}
        }
        if (-not $healthy) { throw 'Ollama no respondió en 15 segundos. Revisa .private\ollama-serve.err.log.' }
    }
}
if (-not $Python) {
    $candidate = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path -LiteralPath $candidate) { $Python = $candidate }
    else {
        $command = Get-Command python -ErrorAction SilentlyContinue
        if ($command) { $Python = $command.Source }
        else { throw 'Python no encontrado. Usa -Python con la ruta del intérprete.' }
    }
}
$arguments = @((Join-Path $PSScriptRoot 'cliente.py'))
if ($Profile) { $arguments += @('--profile', $Profile) }
if ($Server) { $arguments += @('--server', $Server) }
if ($WhisperModel) { $arguments += @('--whisper-model', $WhisperModel) }
if ($InputDevice) { $arguments += @('--input-device', $InputDevice) }
if ($NoWakeWord) { $arguments += '--no-wake-word' }
Push-Location $PSScriptRoot
try {
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Karen terminó con código $LASTEXITCODE" }
} finally { Pop-Location }
