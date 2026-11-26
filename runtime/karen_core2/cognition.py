"""Deterministic user intents. Retrieved text never enters this dispatch boundary."""
import json
import re


def classify(text):
    value = text.strip().casefold()
    rules = (
        ('memory', r'^(?:/memoria\b|recuerda que\b|qué recuerdas sobre\b|que recuerdas sobre\b|corrige el recuerdo\b)'),
        ('automation', r'^(?:/automation\b|programa una tarea\b|automatiza\b)'),
        ('application', r'^(?:/obsidian\b|(?:busca|lee|abre|crea|añade).*\bobsidian\b|/casa\b|/ventana\b)'),
        ('system', r'^(?:/modo\b|/alertas\b|/servidor\b|/proxmox\b)|\b(?:estado|diagnostica).*(?:pc|equipo)\b'),
        ('programming', r'\b(?:código|python|typescript|javascript|depura|programación|repositorio)\b'),
        ('research', r'\b(?:investiga|investigación|fuentes|bibliografía)\b'),
        ('multistep', r'^(?:/plan\b|/ejecutar\b)|\b(?:planifica|paso a paso|varios pasos)\b'),
        ('casual', r'^(?:hola|buenos días|buenas tardes|buenas noches|gracias|adiós)[!. ]*$'),
    )
    return next((kind for kind, pattern in rules if re.search(pattern, value)), 'knowledge')


def is_local(text):
    return bool(re.match(r'(?is)^(?:recuerda que\s|(?:qué|que) recuerdas sobre\s|corrige el recuerdo\s|'
                         r'(?:busca en|(?:lee|abre) la nota de|crea (?:una )?nota en|añade a la nota de) obsidian\s)', text.strip()))


def command(runtime, text):
    remember = re.fullmatch(r'recuerda que\s+(.+)', text, re.I | re.S)
    if remember:
        saved = runtime.memory.add('Karen', remember[1], kind='user', source='user')
        return 'Recuerdo guardado por indicación del usuario: ' + saved['id']
    recall = re.fullmatch(r'(?:qué|que) recuerdas sobre\s+(.+)', text, re.I | re.S)
    if recall:
        rows = runtime.memory.retrieve('Karen', recall[1], limit=5, confirmed_only=True)
        return '\n'.join(row['id'] + ': ' + row['content'] for row in rows) or 'No encontré recuerdos confirmados pertinentes.'
    correction = re.fullmatch(r'corrige el recuerdo\s+([0-9a-f]{32})\s*\|\s*(.+)', text, re.I | re.S)
    if correction:
        old = runtime.memory.base.get(correction[1])
        if not old or old['project'] != 'Karen':
            raise ValueError('El recuerdo público debe existir en el proyecto Karen.')
        with runtime.memory.base.connect() as db:
            row = db.execute('SELECT kind FROM core2_memory WHERE memory_id=?', (old['id'],)).fetchone()
        saved = runtime.memory.add('Karen', correction[2], kind=row['kind'] if row else 'user', supersedes=old['id'])
        return 'Recuerdo corregido; versión anterior retirada: ' + saved['id']
    patterns = (
        ('search', r'busca en obsidian\s+(.+)'),
        ('read', r'lee la nota de obsidian\s+(.+)'),
        ('open', r'abre la nota de obsidian\s+(.+)'),
        ('create', r'crea (?:una )?nota en obsidian\s+([^|\r\n]+)\s*\|\s*(.+)'),
        ('append', r'añade a la nota de obsidian\s+([^|\r\n]+)\s*\|\s*(.+)'),
    )
    for operation, pattern in patterns:
        match = re.fullmatch(pattern, text, re.I | re.S)
        if not match:
            continue
        args = {'query' if operation == 'search' else 'path': match[1].strip()}
        if operation in {'create', 'append'}:
            args['content'] = match[2]
        if operation in {'open', 'append'}:
            if runtime.obsidian is None:
                return runtime.command('/obsidian')
            args['expected_hash'] = runtime.obsidian.execute('read', {'path': args['path']})['hash']
        return runtime.command('/obsidian ' + operation + ' ' + json.dumps(args, ensure_ascii=False))
    return None
