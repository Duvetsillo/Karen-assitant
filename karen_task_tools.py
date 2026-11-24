"""Fixed, read-only Windows probes for an explicit local PC report task."""

import ctypes
from ctypes import wintypes
import os
import re
import shutil

from karen_tasks import TaskEngine, ToolSpec


class _FileTime(ctypes.Structure):
    _fields_ = [('low', wintypes.DWORD), ('high', wintypes.DWORD)]

    @property
    def ticks(self):
        return (self.high << 32) | self.low


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ('length', wintypes.DWORD), ('memory_load', wintypes.DWORD),
        ('total_phys', ctypes.c_ulonglong), ('avail_phys', ctypes.c_ulonglong),
        ('total_page', ctypes.c_ulonglong), ('avail_page', ctypes.c_ulonglong),
        ('total_virtual', ctypes.c_ulonglong), ('avail_virtual', ctypes.c_ulonglong),
        ('avail_extended', ctypes.c_ulonglong),
    ]


def _windows_kernel():
    if os.name != 'nt':
        raise OSError('Informe del PC disponible solo en Windows.')
    return ctypes.WinDLL('kernel32', use_last_error=True)


def _cpu_times():
    kernel = _windows_kernel()
    kernel.GetSystemTimes.argtypes = [ctypes.POINTER(_FileTime)] * 3
    kernel.GetSystemTimes.restype = wintypes.BOOL
    idle, system, user = _FileTime(), _FileTime(), _FileTime()
    if not kernel.GetSystemTimes(ctypes.byref(idle), ctypes.byref(system), ctypes.byref(user)):
        raise OSError('No pude leer el uso de CPU.')
    return idle.ticks, system.ticks + user.ticks


def cpu_sample(_args, stop):
    idle_before, total_before = _cpu_times()
    if stop.wait(0.2):
        raise InterruptedError('Medición cancelada.')
    idle_after, total_after = _cpu_times()
    elapsed = total_after - total_before
    if elapsed <= 0:
        raise OSError('Muestra de CPU no válida.')
    percent = 100 * (elapsed - (idle_after - idle_before)) / elapsed
    return {'cpu_percent': round(max(0, min(percent, 100)), 1)}


def memory_sample(_args, stop):
    if stop.is_set():
        raise InterruptedError('Medición cancelada.')
    kernel = _windows_kernel()
    kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatus)]
    kernel.GlobalMemoryStatusEx.restype = wintypes.BOOL
    status = _MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)) or not status.total_phys:
        raise OSError('No pude leer la memoria física.')
    return {'ram_total_bytes': status.total_phys, 'ram_available_bytes': status.avail_phys}


def disk_sample(_args, stop):
    if stop.is_set():
        raise InterruptedError('Medición cancelada.')
    _windows_kernel()
    drive = os.getenv('SystemDrive', 'C:')
    if not re.fullmatch(r'[A-Za-z]:', drive):
        raise ValueError('Unidad del sistema inválida.')
    usage = shutil.disk_usage(drive + '\\')
    return {'drive': drive.upper(), 'disk_total_bytes': usage.total, 'disk_free_bytes': usage.free}


def pc_report_tools():
    return {
        'cpu_sample': ToolSpec('read', cpu_sample, verify=lambda _a, r: 0 <= r['cpu_percent'] <= 100, timeout=3),
        'memory_sample': ToolSpec('read', memory_sample,
                                  verify=lambda _a, r: 0 <= r['ram_available_bytes'] <= r['ram_total_bytes'], timeout=3),
        'disk_sample': ToolSpec('read', disk_sample,
                                verify=lambda _a, r: 0 <= r['disk_free_bytes'] <= r['disk_total_bytes'], timeout=3),
    }


def run_pc_report(engine=None, on_started=None):
    engine = engine or TaskEngine(pc_report_tools())
    steps = [{'tool': name, 'args': {}} for name in ('cpu_sample', 'memory_sample', 'disk_sample')]
    task_id = engine.create(steps)
    if on_started:
        on_started(task_id)
    state = engine.run(task_id, steps)
    if state['status'] != 'completed':
        return f"Informe del PC detenido. ID: {task_id}; estado: {state['status']}."
    values = {row['tool']: row['result'] for row in state['results']}
    cpu, memory, disk = (values[name] for name in ('cpu_sample', 'memory_sample', 'disk_sample'))
    gib = 1024 ** 3
    return (f"Informe del PC. ID: {task_id}. CPU: {cpu['cpu_percent']:.1f}% (muestra de 0,2 s). "
            f"RAM disponible: {memory['ram_available_bytes'] / gib:.2f}/{memory['ram_total_bytes'] / gib:.2f} GiB. "
            f"Disco {disk['drive']} {disk['disk_free_bytes'] / gib:.2f}/{disk['disk_total_bytes'] / gib:.2f} GiB libres.")
