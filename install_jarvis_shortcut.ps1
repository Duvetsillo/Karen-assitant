$ErrorActionPreference = 'Stop'
$jarvisDesktop = [Environment]::GetFolderPath('DesktopDirectory')
$jarvisLink = Join-Path $jarvisDesktop 'Karen Jarvis.lnk'
if (Test-Path -LiteralPath $jarvisLink) {
    New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot '.private') -Force | Out-Null
    $jarvisPrevious = Join-Path $PSScriptRoot ('.private\Karen-Jarvis-shortcut-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.lnk')
    Copy-Item -LiteralPath $jarvisLink -Destination $jarvisPrevious
}
$jarvisShell = New-Object -ComObject WScript.Shell
$jarvisShortcut = $jarvisShell.CreateShortcut($jarvisLink)
$jarvisShortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$jarvisShortcut.Arguments = '-NoProfile -WindowStyle Hidden -File "' + (Join-Path $PSScriptRoot 'launch_jarvis.ps1') + '"'
$jarvisShortcut.WorkingDirectory = $PSScriptRoot
$jarvisShortcut.Description = 'Karen · interfaz holográfica alternativa con chat local'
$jarvisShortcut.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',20'
$jarvisShortcut.WindowStyle = 7
$jarvisShortcut.Save()
Write-Output $jarvisLink
