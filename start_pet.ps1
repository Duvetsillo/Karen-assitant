[CmdletBinding()]
param(
    [string]$PetRoot,
    [string]$CoreDatabase,
    [string]$ProjectRoot,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
if (-not $PetRoot) {
    $PetRoot = Join-Path $PSScriptRoot 'pet'
    if (-not (Test-Path -LiteralPath (Join-Path $PetRoot 'package.json') -PathType Leaf)) {
        $PetRoot = Join-Path $PSScriptRoot 'runtime\desktop-pet'
    }
}
if (-not $CoreDatabase) { $CoreDatabase = $env:KAREN_CORE_DB }
if (-not $CoreDatabase) { $CoreDatabase = [Environment]::GetEnvironmentVariable('KAREN_CORE_DB', 'User') }
if (-not $CoreDatabase) {
    throw 'Indica -CoreDatabase con la base local existente o configura KAREN_CORE_DB.'
}
if (-not (Test-Path -LiteralPath $CoreDatabase -PathType Leaf)) {
    throw 'La base de memoria no existe. Indica una base Core existente; no se creará otra automáticamente.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PetRoot 'package.json') -PathType Leaf)) {
    throw 'No se encontró el código de Pet. Indica -PetRoot con su carpeta preparada.'
}
$resolvedPersonalDb = (Resolve-Path -LiteralPath $CoreDatabase).ProviderPath
$resolvedPetRoot = (Resolve-Path -LiteralPath $PetRoot).ProviderPath
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'Pet requiere Node y npm instalados.'
}
if (-not $ProjectRoot) { $ProjectRoot = $env:KAREN_PROJECT_ROOT }
if (-not $ProjectRoot -and (Split-Path -Leaf (Split-Path -Parent $resolvedPersonalDb)) -eq '.private') {
    $ProjectRoot = Split-Path -Parent (Split-Path -Parent $resolvedPersonalDb)
}
if ($ProjectRoot -and -not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw 'La carpeta de recursos de voz no existe; revisa -ProjectRoot.'
}
if ($CheckOnly) {
    Write-Output 'Pet: código localizado, base local existente y Node/npm disponibles. No se inició la aplicación.'
    return
}
if (-not (Test-Path -LiteralPath (Join-Path $resolvedPetRoot 'node_modules') -PathType Container)) {
    throw 'Faltan dependencias del Pet. Ejecuta npm ci en su carpeta antes de iniciarlo.'
}
$env:KAREN_CORE_DB = $resolvedPersonalDb
if ($ProjectRoot) { $env:KAREN_PROJECT_ROOT = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath }
Push-Location $resolvedPetRoot
try {
    & npm run dev
    if ($LASTEXITCODE -ne 0) { throw "Pet terminó con código $LASTEXITCODE." }
} finally { Pop-Location }
