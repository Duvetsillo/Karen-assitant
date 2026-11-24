"""Install the reminder correction in Karen's existing OpenClaw workspace."""
from datetime import datetime, timezone
from pathlib import Path
import shutil


GUIDANCE = '''

## Recordatorios relativos: ejecución real

Una petición «recuérdame TEXTO en N minutos» ya proporciona plazo y contenido;
no pidas otra hora ni otra aprobación si el runtime no las exige. Ejecuta con
exec en PowerShell, host=gateway:
& 'C:/Users/Dayve/AppData/Local/Programs/Python/Python311/python.exe' 'C:/karen/friday_reminders.py' --in-minutes N --message 'TEXTO'
N debe ser el plazo real pedido, no el ejemplo literal. Pasa TEXTO como un único
argumento con quoting correcto; nunca como código ni mediante interpolación.
Para horas absolutas sigue usando --at con zona. Si falta el texto, pregunta
solo qué recordar. No programes un ejemplo para probar capacidades.
Solo confirma «programado» con id real, enabled=true y fecha correcta. --dry-run
no programa. --check solo comprueba el scheduler. No dupliques el job con cron.
Una lista Approved executables vacía o Active exec sessions vacía no es una
denegación. Llama a exec y observa su resultado; nunca inventes permisos
faltantes. Para saber si Windows está elevado, ejecuta karen_admin_status.py;
no confundas la política full de OpenClaw con un token administrador de Windows.
'''


def main():
    workspace = Path.home() / '.openclaw/workspace'
    paths = [workspace / 'AGENTS.md', workspace / 'TOOLS.md']
    originals = {path: path.read_text(encoding='utf-8') for path in paths}
    backup = Path(__file__).resolve().parent / '.private/whatsapp-guidance-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    changed = 0
    for path, original in originals.items():
        if '## Recordatorios relativos: ejecución real' in original:
            continue
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / path.name)
        # Keep current identity and all existing instructions; add the narrow correction.
        first_break = original.find('\n')
        updated = original[:first_break] + GUIDANCE + '\n' + original[first_break:]
        path.write_text(updated, encoding='utf-8')
        changed += 1
    print(f'Guias de recordatorios actualizadas: {changed}. Respaldos privados conservados.')


if __name__ == '__main__':
    main()
