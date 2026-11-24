param([string]$Origin = '', [switch]$ShowCode)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($ShowCode) { python mobile_server.py code; exit $LASTEXITCODE }
if (Get-Command tailscale -ErrorAction SilentlyContinue) {
    $mobileTailnet = tailscale status --json | ConvertFrom-Json
    if (-not $Origin -and $mobileTailnet.BackendState -eq 'Running' -and $mobileTailnet.Self.DNSName) {
        $Origin = 'https://' + $mobileTailnet.Self.DNSName.TrimEnd('.')
    }
}
Write-Host 'Tu codigo privado para conectar el iPhone:'
python mobile_server.py code
if ($Origin) { Write-Host "Abre en Safari (con Tailscale conectado): $Origin" }
$mobileTailnetIp = @($mobileTailnet.Self.TailscaleIPs | Where-Object { $_ -match '^100\.' }) | Select-Object -First 1
if ($Origin -and $mobileTailnetIp) {
    $mobileDirectOrigin = "http://${mobileTailnetIp}:18795"
    Write-Host "Acceso directo por Tailscale: $mobileDirectOrigin"
    python mobile_server.py serve --origin $Origin --tailnet-origin $mobileDirectOrigin
}
elseif ($Origin) { python mobile_server.py serve --origin $Origin }
else { python mobile_server.py serve }
