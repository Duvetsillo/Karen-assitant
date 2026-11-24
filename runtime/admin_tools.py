"""Bounded LAN inventory and named administration operations for Karen/FRIDAY."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import socket
import subprocess
import unicodedata

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / 'admin_policy.json'
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def load_policy():
    """A fresh checkout grants no SSH or network scope; never creates a policy."""
    try:
        data = json.loads(POLICY.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {'allowed_subnets': [], 'ssh_aliases': [], 'default_subnet': ''}
    if (not isinstance(data, dict) or
            any(not isinstance(data.get(key), list) or
                any(not isinstance(value, str) for value in data[key])
                for key in ('allowed_subnets', 'ssh_aliases')) or
            not isinstance(data.get('default_subnet', ''), str)):
        raise ValueError('Política administrativa inválida; revisa admin_policy.json.')
    return {**data, 'default_subnet': data.get('default_subnet', '')}


def run(args, timeout=20):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=timeout, creationflags=FLAGS)
    if result.returncode:
        raise RuntimeError(f'La operación falló (código {result.returncode}).')
    return result.stdout.strip()


def powershell(script, timeout=20):
    return run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script], timeout)


def checked_network(value):
    network = ipaddress.ip_network(value, strict=True)
    allowed = [ipaddress.ip_network(x) for x in load_policy()['allowed_subnets']]
    if network.version != 4 or not network.is_private or network.num_addresses > 256:
        raise ValueError('Usa una subred IPv4 privada de hasta 256 direcciones.')
    if not any(network.subnet_of(item) for item in allowed):
        raise ValueError('La subred no pertenece al alcance autorizado en admin_policy.json.')
    return network


def inventory():
    return json.loads(powershell("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); @(Get-NetNeighbor -AddressFamily IPv4 | Where-Object {$_.State -notin @('Unreachable','Incomplete') -and $_.IPAddress -like '192.168.*'} | Select-Object IPAddress,LinkLayerAddress,State,InterfaceAlias) | ConvertTo-Json -Compress" ) or '[]')


def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=.4):
            return True
    except OSError:
        return False


def scan(subnet):
    network = checked_network(subnet)
    def alive(address):
        host = str(address)
        result = subprocess.run(['ping.exe', '-n', '1', '-w', '300', host],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=3, creationflags=FLAGS)
        return host if result.returncode == 0 else None
    with ThreadPoolExecutor(max_workers=24) as pool:
        hosts = [host for host in pool.map(alive, network.hosts()) if host]
    ports = {22: 'SSH', 80: 'HTTP', 443: 'HTTPS', 445: 'SMB', 8006: 'Proxmox', 8123: 'Home Assistant', 11434: 'Ollama'}
    def inspect(host):
        return {'ip': host, 'services': [{'port': p, 'label': label} for p, label in ports.items() if port_open(host, p)]}
    with ThreadPoolExecutor(max_workers=16) as pool:
        devices = list(pool.map(inspect, hosts))
    result = {'subnet': str(network), 'observed_at': datetime.now(timezone.utc).isoformat(),
              'devices': devices, 'neighbors': inventory(),
              'limitation': 'Los equipos que no responden a ICMP pueden faltar; un puerto abierto no confirma el producto ni la versión.'}
    output = ROOT / 'qa/network-last-scan.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return result


def host_status():
    script = Path.home() / '.openclaw/workspace/automation/friday_probe.py'
    import sys
    result = json.loads(run([sys.executable, str(script)]))
    import ctypes
    result['windows_elevated'] = bool(ctypes.windll.shell32.IsUserAnAdmin())
    return result


def ssh_status(alias):
    allowed = load_policy()['ssh_aliases']
    if alias not in allowed:
        raise ValueError('Alias SSH fuera del alcance autorizado.')
    return run(['C:/Windows/System32/OpenSSH/ssh.exe', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                '-o', 'StrictHostKeyChecking=yes', alias,
                'uptime; free -m; df -h /; qm list; pct list'], timeout=20)


def restart_gateway(confirmed=False):
    if not confirmed:
        raise PermissionError('Confirma reiniciar la tarea OpenClaw Gateway: interrumpirá temporalmente WhatsApp.')
    powershell("Stop-ScheduledTask -TaskName 'OpenClaw Gateway'; Start-ScheduledTask -TaskName 'OpenClaw Gateway'")
    return {'requested': 'restart', 'task': 'OpenClaw Gateway',
            'state': powershell("(Get-ScheduledTask -TaskName 'OpenClaw Gateway').State"),
            'limitation': 'Tarea iniciada; el canal debe comprobarse después de la preparación.'}


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def route_local(prompt):
    text = normalize(prompt)
    try:
        if re.search(r'\b(escanear|escanea|escan[eé]a|escaneo)\b', text) and 'red' in text:
            supplied = re.search(r'\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b', text)
            subnet = supplied.group() if supplied else load_policy()['default_subnet']
            result = scan(subnet)
            lines = [f"Encontré {len(result['devices'])} equipos que responden en {subnet}."]
            for device in result['devices']:
                lines.append(device['ip'] + ': ' + (', '.join(f"{s['label']} ({s['port']})" for s in device['services']) or 'sin los puertos comprobados abiertos'))
            return '\n'.join(lines) + '\n' + result['limitation']
        if ('dispositivos' in text or 'equipos' in text) and 'red' in text and any(w in text for w in ('lista', 'muestra', 'inventario', 'que hay')):
            return 'Vecinos conocidos de la red (la caché no es un inventario completo):\n' + json.dumps(inventory(), ensure_ascii=False, indent=2)
        if any(w in text for w in ('estado', 'diagnostico', 'revisa')) and any(w in text for w in ('servidor home', 'homelab', 'datacenter')):
            alias = 'friday-datacenter' if 'datacenter' in text else 'friday-home'
            return 'Estado real de ' + alias + ':\n' + ssh_status(alias)
        if any(w in text for w in ('estado', 'diagnostico', 'revisa', 'cuanta')) and any(w in text for w in ('mi pc', 'esta pc', 'memoria ram', 'disco')):
            return 'Estado real del PC:\n' + json.dumps(host_status(), ensure_ascii=False, indent=2)
        calendar_read = re.search(r'\b(lee|leer|leeme|leelo|revisa|ver|ves|mirar|mira|abre|abrir|accede|acceder|consulta|consultar|muestra|mostrar|lista|listar)\b', text)
        calendar_write = re.search(r'\b(crea|crear|agrega|agregar|anade|programa|borra|elimina|modifica|cambia)\b', text)
        if any(w in text for w in ('agenda', 'calendario', 'eventos', 'icloud')) and not calendar_write and (calendar_read or any(w in text for w in ('hoy', 'manana', 'semana', 'que tengo', 'proximo', 'puedes'))):
            from icloud_calendar import query_via_runtime
            return query_via_runtime(prompt)
        if re.search(r'\breinicia\b', text) and any(w in text for w in ('gateway', 'whatsapp')):
            return 'Operación preparada: reiniciar OpenClaw Gateway interrumpe WhatsApp temporalmente. Usa el botón de administración «Reiniciar Gateway» para confirmar y ejecutar.'
    except Exception as exc:
        return 'No pude completar la operación: ' + str(exc)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['inventory', 'scan', 'host-status', 'ssh-status', 'restart-gateway'])
    parser.add_argument('--subnet')
    parser.add_argument('--alias', choices=['friday-home', 'friday-datacenter'])
    parser.add_argument('--confirm', action='store_true')
    args = parser.parse_args()
    operations = {'inventory': inventory, 'scan': lambda: scan(args.subnet), 'host-status': host_status,
                  'ssh-status': lambda: ssh_status(args.alias), 'restart-gateway': lambda: restart_gateway(args.confirm)}
    try:
        print(json.dumps(operations[args.action](), ensure_ascii=True, indent=2))
    except Exception as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
