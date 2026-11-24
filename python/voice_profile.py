"""An immutable voice reference shared by every Karen client."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    reference: Path
    reference_text: str
    reference_sha256: str
    model: Path
    language: str
    generation: dict

    def public(self):
        return {'profileId': self.id, 'referenceSha256': self.reference_sha256}


def inside(root, relative):
    if not isinstance(relative, str):
        raise ValueError('Ruta de perfil inválida')
    path = (root / relative).resolve()
    if path == root or root not in path.parents:
        raise ValueError('Ruta de perfil fuera del directorio de modelos')
    return path


def load_profile(root):
    models = (Path(root) / 'voice-models').resolve()
    active = json.loads((models / 'active-voice.json').read_text(encoding='utf-8'))
    manifest = inside(models, active['profile'])
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not re.fullmatch(r'[a-z0-9-]{1,64}', data.get('id', '')):
        raise ValueError('Perfil de voz inválido')
    reference = inside(manifest.parent, data['reference'])
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    if digest != data['reference_sha256'] or digest != active['reference_sha256'] or data['id'] != active['id']:
        raise ValueError('La referencia fija cambió; vuelve a activar el perfil explícitamente')
    if not isinstance(data.get('reference_text'), str) or not data['reference_text'].strip():
        raise ValueError('El perfil necesita una transcripción de referencia')
    model = inside(models, data['runtime_model'])
    if not (model / 'config.json').is_file():
        raise ValueError('Modelo Base local no instalado')
    return VoiceProfile(data['id'], reference, data['reference_text'], digest, model,
                        data.get('language', 'Spanish'), data.get('generation', {}))
