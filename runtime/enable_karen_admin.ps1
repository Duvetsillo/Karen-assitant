param([switch]$Elevated)
$ErrorActionPreference = 'Stop'
$adminRoot = $PSScriptRoot
$statusPath = Join-Path $adminRoot '.private\admin-setup-status.json'
New-Item -ItemType Directory -Path (Split-Path $statusPath) -Force | Out-Null
function Save-AdminStatus([string]$Phase, [string]$Message) {
    @{phase=$Phase; message=$Message; timestamp=(Get-Date -Format o)} |
        ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
}
$adminIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$adminPrincipal = New-Object Security.Principal.WindowsPrincipal($adminIdentity)
if (-not $adminPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if ($Elevated) { throw 'Windows no concedio elevacion de administrador.' }
    Save-AdminStatus 'awaiting_uac' 'Acepta el aviso de Windows para elevar las tareas de Karen.'
    try {
        $adminArguments = '-NoProfile -File "' + $PSCommandPath + '" -Elevated'
        Start-Process -FilePath 'powershell.exe' -Verb RunAs -WindowStyle Hidden -ArgumentList $adminArguments | Out-Null
        Write-Output 'Configuracion iniciada. Estado: .private/admin-setup-status.json'
    } catch {
        Save-AdminStatus 'not_elevated' 'Windows no autorizo la elevacion. Las tareas conservan sus permisos anteriores.'
        throw
    }
    exit
}
try {
    Save-AdminStatus 'configuring' 'Configurando privilegios de Windows para Karen.'
    $backupRoot = Join-Path $adminRoot ('.private\admin-task-backups\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    foreach ($taskName in @('OpenClaw Gateway','OpenClaw Node')) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        $actionText = ($task.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -join ' '
        if ($actionText -notmatch '(?i)openclaw|gateway\.(cmd|vbs)|node\.(cmd|vbs)') {
            throw "La tarea $taskName no coincide con OpenClaw; no se modifico."
        }
        Export-ScheduledTask -TaskName $taskName | Set-Content -LiteralPath (Join-Path $backupRoot ($taskName + '.xml')) -Encoding UTF8
        $task.Principal.RunLevel = 'Highest'
        Set-ScheduledTask -InputObject $task | Out-Null
    }
    Save-AdminStatus 'restarting' 'Reiniciando Gateway y Node con sus nuevos privilegios.'
    $nodePath = 'C:\Program Files\nodejs\node.exe'
    $entryPath = Join-Path $env:APPDATA 'npm\node_modules\openclaw\dist\index.js'
    & $nodePath $entryPath gateway restart *> (Join-Path $backupRoot 'gateway-restart.log')
    if ($LASTEXITCODE -ne 0) { throw 'Windows actualizo las tareas, pero Gateway no confirmo el reinicio.' }
    & $nodePath $entryPath node restart *> (Join-Path $backupRoot 'node-restart.log')
    if ($LASTEXITCODE -ne 0) { throw 'Gateway reiniciado; Node no confirmo su reinicio.' }
    foreach ($taskName in @('OpenClaw Gateway','OpenClaw Node')) {
        if ((Get-ScheduledTask -TaskName $taskName).Principal.RunLevel -ne 'Highest') {
            throw "No se confirmo Highest para $taskName."
        }
    }
    Save-AdminStatus 'configured' 'Tareas de Gateway y Node configuradas con Highest y reiniciadas. Verifica el token del proceso con karen_admin_status.py.'
} catch {
    Save-AdminStatus 'error' $_.Exception.Message
    throw
}
