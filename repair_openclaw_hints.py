"""Clarify misleading Windows runtime hints; never alter execution policy."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil


APPROVAL_HINT = ('No executable-specific preapprovals are registered. This is NOT an exec denial. '
                 'Use exec for an authorized request; the runtime enforces the effective policy.')
SESSION_HINT = 'No running exec sessions. A new exec call starts a process; no existing session is required.'


def repair_text(source):
    start = source.find('function buildApprovedExecutablesRuntimeContext(')
    end = source.find('async function buildRuntimeFactsContext(', start)
    if start < 0 or end < 0:
        raise ValueError('La version instalada no tiene el bloque esperado; no se modifico.')
    before, section, after = source[:start], source[start:end], source[end:]
    marker = '["none"]].join("\\n")'
    if APPROVAL_HINT not in section:
        if section.count(marker) != 1:
            raise ValueError('El bloque de ejecutables cambio; revisa la version antes de editar.')
        section = section.replace(marker, '["' + APPROVAL_HINT + '"]].join("\\n")')
    # Scope replacement to the process-session block, leaving other facts alone.
    process_start = after.find('if (params.capabilityToolNames.has("process"))')
    process_end = after.find('const canSpawn', process_start)
    if process_start < 0 or process_end < 0:
        raise ValueError('No se encontro el bloque esperado de sesiones.')
    process_section = after[process_start:process_end]
    if SESSION_HINT not in process_section:
        if process_section.count(marker) != 1:
            raise ValueError('El bloque de sesiones cambio; no se modifico.')
        process_section = process_section.replace(marker, '["' + SESSION_HINT + '"]].join("\\n")')
    return before + section + after[:process_start] + process_section + after[process_end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dist = Path(os.environ['APPDATA']) / 'npm/node_modules/openclaw/dist'
    candidates = [path for path in dist.glob('system-prompt-report-*.mjs')
                  if 'function buildApprovedExecutablesRuntimeContext(' in path.read_text(encoding='utf-8')]
    if len(candidates) != 1:
        parser.error('Se esperaba un unico modulo de runtime; no se modifico la instalacion.')
    path = candidates[0]
    source = path.read_text(encoding='utf-8')
    updated = repair_text(source)
    if updated == source:
        print('Las aclaraciones de permisos ya estan instaladas.')
        return
    if not args.apply:
        print('Reparacion disponible. Usa --apply; no cambia permisos ni ejecuta herramientas.')
        return
    backup = Path(__file__).resolve().parent / '.private/openclaw-hint-backups' / hashlib.sha256(source.encode()).hexdigest()[:16]
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup / path.name)
    path.write_text(updated, encoding='utf-8')
    print('Aclaraciones instaladas con respaldo privado. Reinicia Gateway para cargarlas.')


if __name__ == '__main__':
    main()
