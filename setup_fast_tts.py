"""Install the pinned optional CUDA-graph overlay without upgrading voice dependencies."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true', help='Select acceleration for the next service start')
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Este instalador se ha verificado solamente en Windows.')
    python = ROOT / 'expressive-runtime/Scripts/python.exe'
    probe = subprocess.check_output([str(python), '-c',
        'import sys,torch,transformers,importlib.metadata as m,json; '
        'print(json.dumps([list(sys.version_info[:2]),torch.__version__,transformers.__version__, '
        'm.version("qwen-tts"),torch.cuda.is_available()]))'], text=True)
    if json.loads(probe) != [[3, 11], '2.6.0+cu126', '4.57.3', '0.1.1', True]:
        raise SystemExit('El runtime no coincide con la combinación CUDA validada; no se modificó.')
    overlay = ROOT / 'tts-fast-runtime'
    if not (overlay / 'Scripts/python.exe').is_file():
        subprocess.run([str(python), '-m', 'venv', str(overlay)], check=True)
    subprocess.run([str(overlay / 'Scripts/python.exe'), '-m', 'pip', 'install',
                    '--no-deps', '--require-hashes', '-r', str(ROOT / 'requirements-tts-fast.txt')], check=True)
    # Reuse the existing installation read-only; dependency upgrades remain isolated.
    packages = overlay / 'Lib/site-packages'
    (packages / 'karen_shared_torch.pth').write_text(
        (ROOT / 'expressive-runtime/Lib/site-packages').as_posix() + '\n', encoding='utf-8')
    subprocess.run([str(overlay / 'Scripts/python.exe'), '-c',
        'import torch,qwen_tts,faster_qwen3_tts; print("Entorno acelerado importado correctamente")'], check=True)
    if args.activate:
        path = ROOT / 'voice-models/tts-runtime.json'
        if path.exists():
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            path.with_name(f'tts-runtime-before-{stamp}.json').write_bytes(path.read_bytes())
        temporary = path.with_suffix('.json.new')
        temporary.write_text(json.dumps({'schema': 1, 'backend': 'cuda-graphs-fp32'}, indent=2), encoding='utf-8')
        os.replace(temporary, path)
        print('Aceleración seleccionada. Reinicia solamente el servicio de voz cuando esté inactivo.')
    else:
        print('Entorno preparado. Configuración de voz sin cambios.')


if __name__ == '__main__':
    main()
