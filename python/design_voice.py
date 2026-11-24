"""Design a new voice once, validate it, then explicitly activate its identity."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import time
import re

DESCRIPTION = ('An original mature adult woman in her thirties speaking clear neutral Latin American Spanish. '
               'A feminine medium-low register with grounded chest resonance and rounded, relaxed vowels. '
               'Warm, calm, confident and attentive, with a natural conversational rhythm and subtle expression. '
               'Clearly adult, never teenage or childlike; no high-pitched cute voice, squeakiness or singsong delivery. '
               'Clear consonants, gentle questions, no whispering, no seductive performance and no announcer voice. '
               'Do not imitate any real person. Keep the same mature vocal identity throughout.')
TEXT = ('Hola, soy Karen. Me alegra acompañarte. Podemos conversar, organizar tus ideas '
        'y resolver las cosas con calma. ¿Qué hacemos hoy?')


def activate(root, folder, replace_active=False):
    from voice_profile import load_profile
    manifest = json.loads((folder / 'profile.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256((folder / manifest['reference']).read_bytes()).hexdigest()
    if digest != manifest['reference_sha256']:
        raise ValueError('La referencia cambió')
    active = root / 'voice-models/active-voice.json'
    if active.exists():
        old = json.loads(active.read_text(encoding='utf-8'))
        if old.get('reference_sha256') != digest and not replace_active:
            raise ValueError('Ya existe otra identidad activa. Conserva una copia y cambia el perfil explícitamente.')
        if old.get('reference_sha256') != digest:
            backup = active.with_name('active-voice-before-' + old['reference_sha256'][:12] + '.json')
            if not backup.exists():
                backup.write_bytes(active.read_bytes())
    previous = active.read_bytes() if active.exists() else None
    temporary = active.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({'schema': 1, 'id': manifest['id'],
        'profile': str((folder / 'profile.json').relative_to(root / 'voice-models')).replace('\\', '/'),
        'reference_sha256': digest}, indent=2), encoding='utf-8')
    temporary.replace(active)
    try:
        load_profile(root)
    except Exception:
        if previous is None:
            active.unlink(missing_ok=True)
        else:
            active.write_bytes(previous)
        raise
    token = root / 'voice-models/.expressive-token'
    try:
        with token.open('x', encoding='ascii') as output:
            output.write(secrets.token_urlsafe(32))
    except FileExistsError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--profile', default='karen-original-v1', help='New identity ID; existing references are never overwritten')
    parser.add_argument('--replace-active', action='store_true', help='Explicitly switch the active identity after preserving its previous pointer')
    parser.add_argument('--activate', action='store_true', help='Activate the existing reviewed reference without regenerating it')
    args = parser.parse_args()
    root = args.root.resolve()
    if not re.fullmatch(r'[a-z0-9-]{1,64}', args.profile):
        parser.error('Identificador de perfil inválido')
    folder = root / 'voice-models' / args.profile
    if args.activate:
        activate(root, folder, args.replace_active)
        print('Perfil original activado. No se regeneró la referencia.')
        return
    if (folder / 'profile.json').exists():
        raise SystemExit('El perfil ya existe. No se regenera implícitamente.')
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel
    started = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(4729)
    model = Qwen3TTSModel.from_pretrained(str(root / 'voice-models/qwen3-voice-design'),
        device_map='cpu', dtype=torch.float16, attn_implementation='sdpa', local_files_only=True)
    model.model.talker.to('cuda:0')
    model.device = torch.device('cuda:0')
    # CPU convolution in FP16 is especially slow on this Windows/Turing setup.
    model.model.speech_tokenizer.model.float()
    waves, rate = model.generate_voice_design(text=TEXT, language='Spanish', instruct=DESCRIPTION,
        temperature=0.65, top_p=0.9, subtalker_temperature=0.65, subtalker_top_p=0.9, max_new_tokens=512)
    wave = np.asarray(waves[0], dtype=np.float32)
    if not np.isfinite(wave).all() or np.sqrt(np.mean(wave ** 2)) < .005 or not 4 < len(wave) / rate < 30:
        raise RuntimeError('Referencia inválida; no se activa')
    folder.mkdir(parents=True, exist_ok=True)
    reference = folder / 'reference.wav'
    sf.write(reference, wave, rate, subtype='PCM_16')
    profile = {'schema': 1, 'id': args.profile, 'name': 'Karen · voz adulta original',
        'language': 'Spanish', 'reference': 'reference.wav', 'reference_text': TEXT,
        'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
        'created_with': 'Qwen3-TTS-12Hz-1.7B-VoiceDesign', 'description': DESCRIPTION,
        'design_seed': 4729, 'human_reference_used': False, 'runtime_model': 'qwen3-stable-base',
        'conditioning': 'speaker-embedding', 'attention': 'eager', 'runtime_precision': 'float32', 'codec_device': 'cpu',
        'generation': {'seed': 42, 'temperature': .55, 'top_p': .9, 'subtalker_temperature': .55, 'subtalker_top_p': .9}}
    (folder / 'profile.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'id': profile['id'], 'audioSeconds': len(wave) / rate, 'elapsedSeconds': time.monotonic() - started}))
    print('Referencia creada. Escucha reference.wav antes de ejecutar --activate.')


if __name__ == '__main__':
    main()
