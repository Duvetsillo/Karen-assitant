"""Conservative Markdown edits. Unknown YAML syntax is never parsed as instructions."""
import json
import re


def frontmatter(text):
    match = re.match(r'\A(\ufeff?---\r?\n)(.*?)(\r?\n---(?:\r?\n|$))(.*)\Z', text, re.S)
    if match:
        return match.groups()
    if text.lstrip('\ufeff').startswith('---'):
        raise ValueError('Frontmatter ambiguo o sin cierre; requiere edición explícita del documento.')
    newline = '\r\n' if '\r\n' in text else '\n'
    bom = '\ufeff' if text.startswith('\ufeff') else ''
    return bom + '---' + newline, '', newline + '---' + newline, text[len(bom):]


def properties_json(value):
    if len(value.encode('utf-8')) > 65536:
        raise ValueError('Propiedades demasiado extensas.')
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError('Propiedad JSON duplicada.')
            result[key] = item
        return result
    try:
        data = json.loads(value, object_pairs_hook=unique)
        json.dumps(data, allow_nan=False)
    except (RecursionError, OverflowError) as exc:
        raise ValueError('Propiedades demasiado anidadas.') from exc
    if (not isinstance(data, dict) or not 1 <= len(data) <= 50 or
            any(not re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}', key) for key in data)):
        raise ValueError('Usa un objeto JSON con hasta 50 nombres de propiedades simples.')
    return data


def set_properties(text, changes):
    opening, header, closing, body = frontmatter(text)
    newline = '\r\n' if opening.endswith('\r\n') else '\n'
    lines = header.splitlines(keepends=True)
    # A subset is intentional: keep complex YAML intact instead of guessing its meaning.
    key_pattern = re.compile(r'''^(?:([A-Za-z_][A-Za-z0-9_-]*)|'([A-Za-z_][A-Za-z0-9_-]*)'|"([A-Za-z_][A-Za-z0-9_-]*)"):\s*(.*)$''')
    fields = []
    for index, line in enumerate(lines):
        if not line.strip() or line.startswith(('#', ' ', '\t', '- ')):
            continue
        match = key_pattern.match(line.rstrip('\r\n'))
        if not match:
            raise ValueError('Sintaxis YAML compleja; usa update con contenido revisado.')
        fields.append((index, next(group for group in match.groups()[:3] if group is not None)))
    names = [key for _, key in fields]
    if len(set(names)) != len(names):
        raise ValueError('Frontmatter contiene propiedades duplicadas.')
    for index, key in reversed(fields):
        if key not in changes:
            continue
        end = next((i for i, _ in fields if i > index), len(lines))
        # Keep trailing standalone comments and blank lines attached to the next field.
        while end > index + 1 and (not lines[end - 1].strip() or lines[end - 1].startswith('#')):
            end -= 1
        lines[index:end] = [key + ': ' + json.dumps(changes[key], ensure_ascii=False, allow_nan=False) + newline]
    for key, value in changes.items():
        if key not in names:
            if lines and not lines[-1].endswith(('\n', '\r')):
                lines[-1] += newline
            lines.append(key + ': ' + json.dumps(value, ensure_ascii=False, allow_nan=False) + newline)
    return opening + ''.join(lines).rstrip('\r\n') + closing + body


def tag_list(value):
    tags = json.loads(value)
    if (not isinstance(tags, list) or len(tags) > 100 or any(not isinstance(tag, str) or
            not re.fullmatch(r'[\w/-]{1,100}', tag) or not re.search(r'[^\W\d]', tag) for tag in tags)):
        raise ValueError('Etiquetas deben ser una lista JSON de nombres sin espacios ni #.')
    return sorted(set(tags))


def yaml_tags(text):
    _, header, _, _ = frontmatter(text)
    match = re.search(r'^tags:[ \t]*(\[[^\r\n]*\]|[^\r\n]*)', header, re.M)
    if not match:
        return []
    value = match[1].strip()
    if not value:
        tail = header[match.end():]
        items = []
        for line in tail.splitlines():
            if not line.strip():
                continue
            item = re.match(r'^\s*-\s+([\w/-]+)\s*$', line)
            if not item:
                break
            items.append(item[1])
        return items
    if value.startswith('[') and value.endswith(']'):
        return [item.strip().strip('"\'') for item in value[1:-1].split(',') if item.strip()]
    return [value.strip('"\'')]


def set_task(text, line, done):
    lines = text.splitlines(keepends=True)
    if not 1 <= line <= len(lines):
        raise ValueError('Línea de tarea fuera del documento.')
    match = re.match(r'^(\s*[-*+] \[)([ xX])(\] .*)$', lines[line - 1].rstrip('\r\n'))
    if not match:
        raise ValueError('La línea seleccionada no es una tarea Markdown.')
    ending = lines[line - 1][len(lines[line - 1].rstrip('\r\n')):]
    lines[line - 1] = match[1] + ('x' if done else ' ') + match[3] + ending
    return ''.join(lines)
