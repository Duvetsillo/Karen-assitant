param([string]$VoiceDirectory = (Join-Path $env:APPDATA 'karen-desktop-pet\voice'))
$ErrorActionPreference = 'Stop'
$VoiceDirectory = [IO.Path]::GetFullPath($VoiceDirectory)
if ($VoiceDirectory -eq [IO.Path]::GetPathRoot($VoiceDirectory)) { throw 'Elige una carpeta de recursos.' }
New-Item -ItemType Directory -Force -Path $VoiceDirectory | Out-Null
$python = Join-Path $VoiceDirectory 'expressive-runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & py -3.11 -m venv (Join-Path $VoiceDirectory 'expressive-runtime')
    if ($LASTEXITCODE -ne 0) { throw 'Se necesita Python 3.11.' }
}
& $python -m pip install --disable-pip-version-check 'torch==2.6.0' 'torchaudio==2.6.0' --index-url https://download.pytorch.org/whl/cu126
if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar PyTorch CUDA.' }
& $python -m pip install --disable-pip-version-check 'qwen-tts==0.1.1' 'transformers==4.57.3' 'soundfile==0.14.0' 'huggingface-hub==0.36.2'
if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar el motor de voz.' }
$download = @'
from huggingface_hub import snapshot_download
from pathlib import Path
import sys
models = Path(sys.argv[1]) / 'voice-models'
snapshot_download('Qwen/Qwen3-TTS-12Hz-0.6B-Base', revision='5d83992436eae1d760afd27aff78a71d676296fc', local_dir=models / 'qwen3-stable-base')
snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign', revision='5ecdb67327fd37bb2e042aab12ff7391903235d3', local_dir=models / 'qwen3-voice-design')
'@
& $python -c $download $VoiceDirectory
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron descargar los modelos propios.' }
Write-Output "Modelos preparados. Genera una referencia con python/design_voice.py --root y actívala con --activate."
