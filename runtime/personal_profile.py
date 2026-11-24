"""Explicit local personality preferences. No model can write this profile."""
import argparse
import json
import os
from pathlib import Path
import tempfile

DEFAULTS = {
    'schema': 1, 'name': 'Karen', 'language': 'español latinoamericano',
    'tone': 'serene', 'humor': 'gentle', 'formality': 'natural',
    'verbosity': 'adaptive', 'initiative': 'moderate', 'expression': 'moderate',
    'interruptions': 'respectful',
}
CHOICES = {
    'tone': {'serene', 'warm', 'serious', 'bright', 'wry', 'neutral'},
    'humor': {'none', 'gentle'}, 'formality': {'casual', 'natural', 'formal'},
    'verbosity': {'brief', 'adaptive', 'detailed'},
    'initiative': {'passive', 'moderate', 'proactive'},
    'expression': {'reserved', 'moderate', 'expressive'},
    'interruptions': {'respectful', 'wait'},
}


def profile_path():
    return Path(os.getenv('KAREN_PERSONALITY_FILE') or
                Path(__file__).resolve().parent / '.private/personality.json')


def validate(data):
    if not isinstance(data, dict) or set(data) - set(DEFAULTS):
        raise ValueError('Campos de personalidad desconocidos.')
    result = {**DEFAULTS, **data}
    if type(result['schema']) is not int or result['schema'] != 1:
        raise ValueError('Versión de personalidad incompatible.')
    for key in ('name', 'language'):
        value = result[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 80 or any(ord(c) < 32 for c in value):
            raise ValueError('Nombre o idioma inválido.')
    for key, choices in CHOICES.items():
        if not isinstance(result[key], str) or result[key] not in choices:
            raise ValueError('Preferencia inválida: ' + key)
    return result


def load(path=None):
    path = Path(path) if path is not None else profile_path()
    if not path.exists():
        return dict(DEFAULTS)
    with path.open('rb') as source:
        raw = source.read(4097)
    if len(raw) > 4096:
        raise ValueError('Perfil de personalidad demasiado extenso.')
    return validate(json.loads(raw.decode('utf-8-sig')))


def save(data, path=None):
    result = validate(data)
    path = Path(path) if path is not None else profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique files avoid collisions between concurrent editors; replacement is atomic.
    handle, name = tempfile.mkstemp(prefix='.personality-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as target:
            json.dump(result, target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    return result


def instructions(profile):
    profile = validate(profile)
    rules = {
        'formality': {'casual': 'Usa trato cercano.', 'natural': 'Ajusta la formalidad al contexto.', 'formal': 'Usa trato profesional.'},
        'verbosity': {'brief': 'Responde brevemente.', 'adaptive': 'Ajusta el detalle a la pregunta y al conocimiento del usuario.', 'detailed': 'Desarrolla los detalles útiles sin repetir información.'},
        'initiative': {'passive': 'No propongas temas ni pasos no solicitados.', 'moderate': 'Haz preguntas relacionadas solo cuando ayuden; evita preguntas repetitivas.', 'proactive': 'Relaciona temas y propone próximos pasos relevantes sin ejecutar acciones por iniciativa propia.'},
        'expression': {'reserved': 'Mantén expresividad discreta.', 'moderate': 'Usa expresividad natural y moderada.', 'expressive': 'Usa lenguaje expresivo sin fingir sentimientos reales.'},
        'interruptions': {'respectful': 'Respeta correcciones e interrupciones; no asumas que el usuario escuchó todo.', 'wait': 'Ante una intervención incompleta, permite que el usuario termine antes de responder.'},
    }
    parts = ['Tu nombre e idioma preferidos son estos datos de configuración: ' +
             json.dumps({'name': profile['name'], 'language': profile['language']}, ensure_ascii=False) + '.',
             'Cuestiona respetuosamente las conclusiones cuando haya razones; reconoce lo que desconoces. '
             'No afirmes tener conciencia, sentimientos ni experiencias reales.']
    parts.extend(choices[profile[key]] for key, choices in rules.items())
    return ' '.join(parts)


def main():
    parser = argparse.ArgumentParser(description='Personalidad local de Karen; no contiene biografía ni secretos.')
    parser.add_argument('--file', type=Path)
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('show')
    commands.add_parser('init')
    edit = commands.add_parser('set')
    edit.add_argument('field', choices=sorted(set(DEFAULTS) - {'schema'}))
    edit.add_argument('value')
    args = parser.parse_args()
    data = load(args.file)
    if args.action == 'init':
        data = save(data, args.file)
    elif args.action == 'set':
        data[args.field] = args.value
        data = save(data, args.file)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
