"""iCloud CalDAV with Windows-user encrypted credentials and local setup UI."""
import argparse
import base64
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
def windows_local_appdata():
    """Use the actual user's known folder; OpenClaw isolates LOCALAPPDATA."""
    import uuid
    guid = ctypes.create_string_buffer(uuid.UUID('F1B32785-6FBA-4FCF-9D55-7B8E7F157091').bytes_le)
    location = ctypes.c_wchar_p()
    api = ctypes.windll.shell32.SHGetKnownFolderPath
    api.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    api.restype = ctypes.c_long
    if api(guid, 0, None, ctypes.byref(location)) != 0:
        raise OSError('Windows no pudo localizar la carpeta de credenciales.')
    try:
        return Path(location.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.ole32.CoTaskMemFree(location)


# Native OpenClaw exec has a restricted profile-file view. Application-local
# encrypted storage is available to both entry points; DPAPI still binds it
# to the same Windows user. No password is stored as plain text.
CREDENTIAL = ROOT / '.private/icloud.dpapi'
URL = 'https://caldav.icloud.com/'


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]


def crypt(data, decrypt=False):
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    output = Blob()
    api = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    api.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    api.restype = wintypes.BOOL
    if not api(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise OSError('Windows no pudo proteger o leer la credencial de iCloud.')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(output.data)


def load_credentials():
    if not CREDENTIAL.is_file():
        raise RuntimeError('iCloud pendiente de vinculación. Abre «Vincular calendario iCloud» y usa una contraseña específica de Apple.')
    return json.loads(crypt(CREDENTIAL.read_bytes(), decrypt=True).decode('utf-8'))


def save_credentials(account, password):
    CREDENTIAL.parent.mkdir(parents=True, exist_ok=True)
    encrypted = crypt(json.dumps({'account': account, 'password': password}).encode())
    temporary = CREDENTIAL.with_suffix('.tmp')
    temporary.write_bytes(encrypted)
    temporary.replace(CREDENTIAL)


def connect(credentials=None):
    import caldav
    credentials = credentials or load_credentials()
    return caldav.DAVClient(url=URL, username=credentials['account'], password=credentials['password'], timeout=25)


def calendars(credentials=None):
    with connect(credentials) as client:
        return [{'name': c.get_display_name(), 'url': str(c.url)} for c in client.principal().calendars()]


def list_events(start, end):
    if start.tzinfo is None or end.tzinfo is None or not start < end or end-start > timedelta(days=32):
        raise ValueError('Consulta fechas con zona horaria, inicio anterior al fin y hasta 32 días.')
    output = []
    with connect() as client:
        for calendar in client.principal().calendars():
            for event in calendar.search(start=start, end=end, event=True, expand=True):
                component = event.get_icalendar_component()
                beginning = component.decoded('DTSTART')
                finish = component.decoded('DTEND') if component.get('DTEND') else None
                if isinstance(beginning, datetime) and beginning.tzinfo:
                    beginning = beginning.astimezone(ZoneInfo('America/La_Paz'))
                output.append({'calendar': calendar.get_display_name(), 'title': str(component.get('SUMMARY', 'Sin título')),
                               'start': beginning.isoformat(), 'end': finish.isoformat() if finish else None,
                               'uid': str(component.get('UID', ''))})
    return sorted(output, key=lambda x: x['start'])


def create_event(name, title, start, end):
    if not title.strip() or len(title) > 300 or start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError('Evento inválido: título y fechas exactas con zona horaria son necesarios.')
    import hashlib
    uid = hashlib.sha256(f'{name}|{title}|{start.isoformat()}|{end.isoformat()}'.encode()).hexdigest() + '@karen.local'
    with connect() as client:
        matches = [c for c in client.principal().calendars() if c.get_display_name() == name]
        if len(matches) != 1:
            raise ValueError('Selecciona un nombre de calendario único de la lista real.')
        calendar = matches[0]
        # Repeating the same exact request reuses its UID and cannot create a second event.
        existing = calendar.search(start=start, end=end, event=True, expand=False)
        for event in existing:
            if str(event.get_icalendar_component().get('UID')) == uid:
                return {'uid': uid, 'created': False, 'already_exists': True}
        event = calendar.add_event(dtstart=start, dtend=end, summary=title, uid=uid)
        event.load()
        return {'uid': uid, 'created': True, 'calendar': name, 'title': title, 'start': start.isoformat()}


def query_via_runtime(prompt):
    from admin_tools import normalize
    text = normalize(prompt)
    action = 'tomorrow' if 'manana' in text else 'today' if 'hoy' in text else 'week'
    python = ROOT / 'calendar-runtime/Scripts/python.exe'
    result = subprocess.run([str(python), str(Path(__file__)), action], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=120,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        return result.stderr.strip() or 'No pude consultar iCloud.'
    events = json.loads(result.stdout)
    if not events:
        return 'No hay eventos en el período consultado en los calendarios vinculados de iCloud.'
    def readable(item):
        beginning = datetime.fromisoformat(item['start']) if 'T' in item['start'] else None
        when = beginning.strftime('%d/%m a las %H:%M') if beginning else item['start'] + ', todo el día'
        return f"{when}: {item['title']} ({item['calendar']})"
    return 'Tu agenda de iCloud:\n' + '\n'.join(readable(x) for x in events)


def setup():
    import tkinter as tk
    from tkinter import messagebox
    import threading
    import queue
    root = tk.Tk()
    root.title('Karen — vincular calendario iCloud')
    root.geometry('520x340')
    tk.Label(root, text='Conectar el calendario del iPhone', font=('Segoe UI', 15)).pack(pady=12)
    tk.Label(root, text='Cuenta Apple (correo)', font=('Segoe UI', 11)).pack()
    account = tk.Entry(root, width=48)
    account.pack(pady=5)
    tk.Label(root, text='Contraseña específica para la app Karen', font=('Segoe UI', 11)).pack()
    password = tk.Entry(root, width=48, show='•')
    password.pack(pady=5)
    tk.Label(root, text='Genérala en account.apple.com → Inicio de sesión y seguridad\n→ Contraseñas específicas para apps. No uses tu contraseña principal.\nSe guardará cifrada para tu usuario Windows.', wraplength=480).pack(pady=10)
    status = tk.StringVar(value='Pendiente de vinculación. No se crearán eventos de prueba.')
    tk.Label(root, textvariable=status, wraplength=480).pack()
    results = queue.Queue()
    def save():
        user, secret = account.get().strip(), password.get().strip()
        if not user or not secret:
            messagebox.showerror('Faltan datos', 'Introduce tu correo Apple y una contraseña específica para apps.')
            return
        button.configure(state='disabled')
        status.set('Verificando acceso a tus calendarios…')
        def verify():
            try:
                items = calendars({'account': user, 'password': secret})
                save_credentials(user, secret)
                results.put((True, f"Vinculado: {len(items)} calendarios. Ya puedes consultar tu agenda en Karen y FRIDAY."))
            except Exception:
                results.put((False, 'No se pudo vincular. Revisa la contraseña específica, la cuenta y la conexión.'))
        threading.Thread(target=verify, daemon=True).start()
    button = tk.Button(root, text='Verificar y vincular', command=save)
    button.pack(pady=12)
    def poll():
        try:
            success, message = results.get_nowait()
            status.set(message)
            if success:
                password.delete(0, tk.END)
            else:
                button.configure(state='normal')
        except queue.Empty:
            pass
        root.after(150, poll)
    poll()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['setup', 'status', 'calendars', 'today', 'tomorrow', 'week', 'create'])
    parser.add_argument('--calendar')
    parser.add_argument('--title')
    parser.add_argument('--start')
    parser.add_argument('--end')
    args = parser.parse_args()
    if args.action == 'setup':
        return setup()
    try:
        if args.action == 'status':
            result = {'configured': CREDENTIAL.is_file(), 'credential_path': str(CREDENTIAL)}
        elif args.action == 'calendars':
            result = calendars()
        elif args.action == 'create':
            result = create_event(args.calendar, args.title, datetime.fromisoformat(args.start), datetime.fromisoformat(args.end))
        else:
            start = datetime.now(ZoneInfo('America/La_Paz')).replace(hour=0, minute=0, second=0, microsecond=0)
            if args.action == 'tomorrow':
                start += timedelta(days=1)
            result = list_events(start, start + timedelta(days=7 if args.action == 'week' else 1))
        sys.stdout.reconfigure(encoding='utf-8')
        # ASCII JSON survives the legacy Windows console used by native exec.
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except Exception as exc:
        # Do not print HTTP objects or library exceptions that could contain credentials.
        if not CREDENTIAL.is_file():
            parser.exit(1, 'iCloud pendiente: abre «Vincular calendario iCloud» e introduce una contraseña específica de Apple.\n')
        parser.exit(1, 'No se pudo completar la operación de iCloud. Verifica credenciales, calendario y fechas.\n')


if __name__ == '__main__':
    main()
