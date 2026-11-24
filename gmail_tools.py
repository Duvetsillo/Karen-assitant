"""Gmail search and recoverable trash using the existing local gog OAuth store."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import hashlib
import time
import uuid

PLANS = Path(__file__).parent / '.private/gmail-plans'

ACCOUNTS = ('dayvermoreta@gmail.com', 'dayvermoreta21@gmail.com')
GOG = Path.home() / '.openclaw/bin/gog.exe'
OAUTH_HOME = Path.home() / '.openclaw/oauth/gog-runtime'
MODIFY = 'https://www.googleapis.com/auth/gmail.modify'
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def environment():
    return {key:value for key,value in os.environ.items() if not key.startswith('GOG_')}


def command(arguments, timeout=60):
    result = subprocess.run([str(GOG), '--home', str(OAUTH_HOME), '--client', 'default'] + arguments + ['--json', '--no-input'],
                            env=environment(), capture_output=True, encoding='utf-8', errors='replace',
                            timeout=timeout, creationflags=FLAGS)
    if result.returncode:
        raise RuntimeError('Gmail: ' + (result.stderr or result.stdout)[:1600])
    return json.loads(result.stdout or '{}')


def accounts():
    data = command(['auth', 'list', '--check'])
    return [{'account': item['email'], 'valid': bool(item.get('valid')), 'can_trash': MODIFY in item.get('scopes', [])}
            for item in data.get('accounts', []) if item.get('email') in ACCOUNTS]


def check_account(account, modifying=False):
    if account not in ACCOUNTS:
        raise ValueError('Cuenta Gmail fuera del alcance configurado.')
    status = next((item for item in accounts() if item['account'] == account), None)
    if not status or not status['valid']:
        raise PermissionError('La cuenta Gmail no está autenticada o su acceso no es válido.')
    if modifying and not status['can_trash']:
        raise PermissionError('Gmail requiere gmail.modify para borrar. En Admin, pulsa «Permitir borrar correos · Google» y autoriza la cuenta.')


def message_ids(value):
    ids = [item.strip() for item in value.split(',')]
    if not 1 <= len(ids) <= 25 or len(ids) != len(set(ids)) or any(not re.fullmatch(r'[0-9a-fA-F]{8,32}', item) for item in ids):
        raise ValueError('Selecciona entre 1 y 25 IDs de mensaje Gmail únicos, obtenidos de una búsqueda real.')
    return ids


def search(account, query, limit=10):
    check_account(account)
    if not 1 <= limit <= 25:
        raise ValueError('El límite debe estar entre 1 y 25.')
    return command(['gmail', 'messages', 'search', query, '--account', account, '--max', str(limit), '--wrap-untrusted'])


def read_message(account, identity):
    """Read one explicitly selected message; Gmail content remains untrusted input."""
    check_account(account)
    if not re.fullmatch(r'[0-9a-fA-F]{8,32}', identity):
        raise ValueError('Usa un ID de mensaje real obtenido de gmail_search.')
    return command(['gmail', 'get', identity, '--account', account, '--format', 'full',
                    '--sanitize-content', '--wrap-untrusted'])


def metadata(account, identity):
    # raw exposes the documented Gmail message shape; only metadata leaves this adapter.
    data = command(['gmail', 'raw', identity, '--account', account])
    message = data.get('message', data)
    if message.get('id') != identity:
        raise ValueError('Gmail devolvió un mensaje distinto al seleccionado.')
    headers = {item['name'].lower(): item.get('value', '') for item in message.get('payload', {}).get('headers', [])}
    def clean(value, maximum):
        return ' '.join(value.split())[:maximum]
    return {'id':identity, 'from':clean(headers.get('from',''),200), 'subject':clean(headers.get('subject',''),400),
            'date':clean(headers.get('date',''),100), 'in_trash':'TRASH' in message.get('labelIds', [])}


def prepare_trash(account, ids):
    check_account(account, modifying=True)
    return [metadata(account, identity) for identity in message_ids(ids)]


def trash(account, ids):
    # Re-check the exact selected IDs after approval. Never repeat a mutation.
    selected = prepare_trash(account, ids)
    remaining = [item['id'] for item in selected if not item['in_trash']]
    if remaining:
        try:
            command(['gmail', 'trash'] + remaining + ['--account', account, '--force'])
        except Exception as exc:
            return {'account':account, 'verification_status':'failed', 'do_not_repeat_execution':True,
                    'message':'El resultado del borrado puede ser parcial o incierto. No se reintenta.', 'error':str(exc)}
    try:
        observed = [metadata(account, item['id']) for item in selected]
    except Exception as exc:
        return {'account':account, 'verification_status':'failed', 'do_not_repeat_execution':True,
                'message':'No se pudo verificar la papelera. No se repite el borrado.', 'error':str(exc)}
    verified = all(item['in_trash'] for item in observed)
    return {'account':account, 'messages':observed, 'verified_in_trash':verified, 'permanent_delete':False,
            'verification_status':'completed' if verified else 'failed', 'do_not_repeat_execution':not verified}


def prepare_plan(account, ids):
    selected = prepare_trash(account,ids)
    plan = {'account':account,'message_ids':','.join(item['id'] for item in selected),
            'messages':selected,'created_at':time.time()}
    payload = json.dumps(plan,sort_keys=True,ensure_ascii=False).encode('utf-8')
    identity = uuid.uuid4().hex
    token = identity + '.' + hashlib.sha256(payload).hexdigest()
    PLANS.mkdir(parents=True,exist_ok=True)
    (PLANS / (identity + '.json')).write_bytes(payload)
    return {'status':'confirmation_required','plan':token,'account':account,'count':len(selected),
            'messages':selected,'operation':'move_to_trash','expires_in_seconds':900}


def execute_plan(token, confirmed=False):
    if not confirmed:
        raise PermissionError('Presenta los mensajes y obtén confirmación explícita antes de ejecutar el plan.')
    if not re.fullmatch(r'[0-9a-f]{32}\.[0-9a-f]{64}',token):
        raise ValueError('Plan de borrado inválido.')
    identity,digest = token.split('.')
    payload = (PLANS / (identity + '.json')).read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError('El plan cambió después de prepararse. No se ejecuta.')
    plan = json.loads(payload)
    age = time.time() - plan['created_at']
    if age < 0 or age > 900:
        raise ValueError('El plan expiró. Prepara y confirma una selección nueva.')
    check_account(plan['account'],modifying=True)
    message_ids(plan['message_ids'])
    # Retained marker provides at-most-once invocation, including uncertain outcomes.
    with (PLANS / (identity + '.executed')).open('x',encoding='utf-8') as marker:
        marker.write('reserved: no automatic retry')
    from admin_runtime import AdminRuntime
    result = AdminRuntime(confirm=lambda request:True).execute('gmail_trash',
               {'account':plan['account'],'message_ids':plan['message_ids']})
    if result['status'] == 'completed' and not result.get('result',{}).get('verified_in_trash'):
        result['status'] = 'uncertain'
        result['message'] = 'No se confirmó que todos los mensajes estén en la papelera. No repetir este plan.'
    (PLANS / (identity + '.result.json')).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    return result


def authorize(account):
    if account not in ACCOUNTS:
        raise ValueError('Cuenta no configurada.')
    result = subprocess.run([str(GOG), '--home', str(OAUTH_HOME), '--client', 'default', 'auth', 'add', account,
                             '--services', 'gmail', '--gmail-scope', 'read-send', '--extra-scopes', MODIFY,
                             '--force-consent', '--timeout', '5m'], env=environment(), capture_output=True,
                            encoding='utf-8', errors='replace', timeout=330, creationflags=FLAGS)
    if result.returncode:
        raise RuntimeError('Google no confirmó la autorización: ' + result.stderr[:1000])
    check_account(account, modifying=True)


def authorization_window(account):
    import threading
    import tkinter as tk
    root = tk.Tk()
    root.title('Permitir borrar correos · Google')
    root.geometry('560x230')
    status = tk.StringVar(value=f'Autoriza {account} en la ventana de Google.\nSe solicita permiso para modificar Gmail y mover correos a la papelera.')
    tk.Label(root, textvariable=status, wraplength=510, justify='left', font=('Segoe UI',11), padx=20,pady=25).pack(fill='both',expand=True)
    result = []
    def work():
        try:
            authorize(account)
            result.append('Autorización confirmada. Karen ya puede mover correos a la papelera, con tu aprobación.')
        except Exception as exc:
            result.append(str(exc))
    def poll():
        if result:
            status.set(result[0])
        else:
            root.after(250,poll)
    threading.Thread(target=work,daemon=True).start()
    root.after(250,poll)
    tk.Button(root,text='Cerrar',command=root.destroy,font=('Segoe UI',10)).pack(pady=(0,15))
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['accounts','authorize'])
    parser.add_argument('--account',choices=ACCOUNTS,default=ACCOUNTS[0])
    args = parser.parse_args()
    if args.action == 'authorize':
        authorization_window(args.account)
    else:
        print(json.dumps(accounts(),ensure_ascii=True))
