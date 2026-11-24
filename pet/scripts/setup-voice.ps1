param([string]$VoiceDirectory = (Join-Path $env:APPDATA 'karen-desktop-pet\voice'))
$ErrorActionPreference = 'Stop'
$VoiceDirectory = [IO.Path]::GetFullPath($VoiceDirectory)
if ($VoiceDirectory -eq [IO.Path]::GetPathRoot($VoiceDirectory)) { throw 'Elige una carpeta de recursos, no la raíz del disco.' }
New-Item -ItemType Directory -Force -Path $VoiceDirectory | Out-Null
$python = Join-Path $VoiceDirectory 'voice-runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & py -3.11 -m venv (Join-Path $VoiceDirectory 'voice-runtime')
    if ($LASTEXITCODE -ne 0) { throw 'Instala Python 3.11 para crear el runtime opcional.' }
}
& $python -m pip install --disable-pip-version-check 'faster-whisper==1.2.1' 'PyAudioWPatch==0.2.12.9' 'edge-tts==7.3.1'
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de reconocimiento.' }
$modelPath = Join-Path $VoiceDirectory 'voice-models\faster-whisper-small'
& $python -c 'import sys; from huggingface_hub import snapshot_download; snapshot_download(repo_id="Systran/faster-whisper-small", local_dir=sys.argv[1])' $modelPath
if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar el modelo. Revisa tu conexión.' }
Write-Output "Recursos de voz preparados en $VoiceDirectory. Selecciona esa carpeta en Voz."
