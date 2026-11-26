"""Code-owned skill manifests and adapters for existing validated Karen tools."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import threading

from karen_tasks import ToolSpec
from karen_task_tools import pc_report_tools
from .privacy import SECRET

ROLES = {'SYSTEM', 'DEVELOPER', 'RESEARCHER', 'HOME', 'ANALYST', 'ORCHESTRATOR'}


def validate_schema(schema, value):
    if not isinstance(value, dict) or set(value) - set(schema.get('properties', {})) or set(schema.get('required', [])) - set(value):
        raise ValueError('Parámetros ausentes o desconocidos.')
    for key, item in value.items():
        spec = schema['properties'][key]
        kind = spec.get('type')
        if kind == 'string' and (not isinstance(item, str) or not spec.get('minLength', 0) <= len(item) <= spec.get('maxLength', 4000) or '\0' in item):
            raise ValueError('Texto de parámetro inválido: ' + key)
        if kind == 'integer' and (type(item) is not int or not spec.get('minimum', 0) <= item <= spec.get('maximum', 2**31 - 1)):
            raise ValueError('Número de parámetro inválido: ' + key)
        if kind == 'boolean' and type(item) is not bool:
            raise ValueError('Booleano de parámetro inválido: ' + key)
        if 'enum' in spec and item not in spec['enum']:
            raise ValueError('Operación no permitida: ' + key)
        if SECRET.search(key):
            raise ValueError('Las credenciales no son parámetros de un plan.')


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    description: str
    role: str
    permission: str
    parameters: dict
    spec: ToolSpec


class SkillRegistry:
    def __init__(self):
        self.skills = {}

    def register(self, skill):
        if not isinstance(skill, Skill) or skill.id in self.skills or skill.role not in ROLES or skill.permission != skill.spec.permission:
            raise ValueError('Manifiesto de habilidad inválido o duplicado.')
        if skill.spec.verify is None or skill.spec.validate is None:
            raise ValueError('Cada habilidad requiere validación y verificación por código.')
        self.skills[skill.id] = skill

    def tools(self):
        return {name: skill.spec for name, skill in self.skills.items()}

    def manifests(self):
        return [{'id': s.id, 'name': s.name, 'description': s.description, 'role': s.role,
                 'permission': s.permission, 'parameters': s.parameters} for s in self.skills.values()]


def cancellable_process(argv, stop, timeout=30):
    import time
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + timeout
    try:
        while True:
            if stop.is_set() or time.monotonic() > deadline:
                if __import__('os').name == 'nt':
                    subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=5,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                else:
                    process.kill()
                process.communicate(timeout=5)
                raise InterruptedError('Proceso cancelado o agotado.')
            try:
                stdout, stderr = process.communicate(timeout=.1)
                if process.returncode:
                    raise RuntimeError('La herramienta terminó con código ' + str(process.returncode))
                return stdout.decode('utf-8', errors='replace')[:16000]
            except subprocess.TimeoutExpired:
                continue
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def builtins(task_path):
    registry = SkillRegistry()
    empty = {'type': 'object', 'properties': {}, 'additionalProperties': False}
    for name, spec in pc_report_tools().items():
        validated = ToolSpec(spec.permission, spec.handler, lambda args: validate_schema(empty, args), spec.verify, spec.timeout)
        registry.register(Skill(name, name.replace('_', ' ').title(), 'Medición real del PC, sin modificarlo.', 'SYSTEM', 'read', empty, validated))
    from admin_runtime import AdminRuntime, AdminAudit, DEFINITIONS, validate

    class ControlledRuntime(AdminRuntime):
        def powershell(self, script, timeout=30):
            wrapped = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new(); " + script
            return cancellable_process(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', wrapped], self.stop, timeout)

    # These adapters expose named operations only. Generated shell is never registered.
    permissions = {'admin_inventory': 'read', 'admin_files': 'read', 'admin_file_change': 'sensitive',
                   'admin_service': 'sensitive', 'admin_process_stop': 'sensitive'}
    for name, permission in permissions.items():
        parameters = DEFINITIONS[name]['parameters']

        def check(args, name=name, parameters=parameters):
            validate_schema(parameters, args)
            validate(name, args)
            if name == 'admin_file_change' and args['operation'] not in {'mkdir', 'copy', 'write'}:
                raise ValueError('El planificador no ejecuta borrado ni movimiento; usa revisión administrativa explícita.')
            runtime = AdminRuntime(audit=AdminAudit(task_path))
            runtime.preflight(name, args)
            if name in {'admin_files', 'admin_file_change'}:
                for key in ('path', 'destination'):
                    if key in args:
                        runtime.path(args[key])

        def execute(args, stop, name=name):
            if stop.is_set():
                raise InterruptedError()
            runtime = ControlledRuntime(audit=AdminAudit(task_path))
            runtime.stop = stop
            result = runtime.dispatch(name, args)
            if stop.is_set():
                raise InterruptedError()
            return result

        def verify(args, result, name=name):
            if name == 'admin_file_change':
                path = Path(args.get('destination', args['path']))
                if args['operation'] == 'mkdir':
                    return path.is_dir()
                if args['operation'] == 'copy':
                    return path.is_file() and hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(Path(args['path']).read_bytes()).digest()
                return path.is_file() and path.read_text(encoding='utf-8') == args['content']
            if name == 'admin_service':
                data = json.loads(result)
                expected = 1 if args['operation'] == 'stop' else 4
                return data.get('Name') == args['name'] and data.get('Status') in (expected, 'Stopped' if expected == 1 else 'Running')
            if name == 'admin_process_stop':
                return json.loads(result).get('Stopped') is True
            return result is not None and bool(result)

        registry.register(Skill(name, name, DEFINITIONS[name]['description'],
                                'DEVELOPER' if name == 'admin_files' else 'SYSTEM', permission,
                                parameters, ToolSpec(permission, execute, check, verify, timeout=40)))
    base = registry.skills['admin_file_change'].spec
    for operation in ('mkdir', 'copy'):
        properties = {'path': {'type': 'string', 'minLength': 1, 'maxLength': 1024}}
        if operation == 'copy':
            properties['destination'] = {'type': 'string', 'minLength': 1, 'maxLength': 1024}
        schema = {'type': 'object', 'properties': properties, 'required': list(properties)}
        def check_file(args, operation=operation, schema=schema):
            validate_schema(schema, args)
            base.validate({'operation': operation, **args})
            if operation == 'copy' and Path(args['path']).stat().st_size > 64 * 1024**2:
                raise ValueError('La copia en planes está limitada a 64 MiB; usa la administración revisada para archivos mayores.')
        registry.register(Skill('file_' + operation, 'Crear carpeta' if operation == 'mkdir' else 'Copiar archivo',
            'Operación reversible validada; nunca sobrescribe un destino.', 'DEVELOPER', 'reversible', schema,
            ToolSpec('reversible', lambda args, stop, op=operation: base.handler({'operation': op, **args}, stop),
                     check_file, lambda args, result, op=operation: base.verify({'operation': op, **args}, result), 40)))
    return registry
