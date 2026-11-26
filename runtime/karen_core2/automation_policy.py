"""Finite conditions and quiet hours; no expressions, scripts or model evaluation."""
from datetime import timedelta, timezone
import math
import threading

from karen_alerts import AlertEngine, _minutes


def window(value):
    if not isinstance(value, dict) or set(value) - {'start', 'end', 'offset_minutes'} or not {'start', 'end'} <= value.keys():
        raise ValueError('Horario requiere start/end y offset_minutes opcional.')
    if not isinstance(value['start'], str) or not isinstance(value['end'], str):
        raise ValueError('Usa horarios HH:MM.')
    if _minutes(value['start']) == _minutes(value['end']):
        raise ValueError('Inicio y fin deben ser diferentes.')
    if 'offset_minutes' in value and (type(value['offset_minutes']) is not int or not -840 <= value['offset_minutes'] <= 840):
        raise ValueError('Offset horario inválido.')
    return dict(value)


def in_window(now, config):
    local = now.astimezone(timezone(timedelta(minutes=config['offset_minutes']))) if 'offset_minutes' in config else now.astimezone()
    return AlertEngine._quiet(local, {'quiet_start': config['start'], 'quiet_end': config['end']})


def conditions(value):
    if value is None:
        return {}
    allowed = {'weekdays', 'window', 'allowed_modes', 'min_ram_available_mib', 'min_vram_available_mib', 'max_cpu_percent'}
    if not isinstance(value, dict) or value.keys() - allowed:
        raise ValueError('Condición fuera de la lista permitida.')
    result = dict(value)
    if 'weekdays' in value and (not isinstance(value['weekdays'], list) or not value['weekdays'] or len(value['weekdays']) > 7 or
                              any(type(day) is not int or not 0 <= day <= 6 for day in value['weekdays'])):
        raise ValueError('weekdays requiere días 0 a 6.')
    if 'allowed_modes' in value and (not isinstance(value['allowed_modes'], list) or not 1 <= len(value['allowed_modes']) <= 2 or
                                   any(not isinstance(mode, str) or mode not in {'normal', 'do_not_disturb'} for mode in value['allowed_modes'])):
        raise ValueError('Modos permitidos: normal y do_not_disturb.')
    for key in ('min_ram_available_mib', 'min_vram_available_mib'):
        if key in value and (type(value[key]) is not int or not 0 <= value[key] <= 1048576):
            raise ValueError('Umbral de memoria inválido.')
    if 'max_cpu_percent' in value and (type(value['max_cpu_percent']) not in (int, float) or
                                     not math.isfinite(value['max_cpu_percent']) or not 0 <= value['max_cpu_percent'] <= 100):
        raise ValueError('Umbral CPU inválido.')
    if 'window' in value:
        result['window'] = window(value['window'])
    return result


def metrics_needed(value):
    return {metric for key, metric in [('min_ram_available_mib', 'ram_available_bytes'),
                                      ('min_vram_available_mib', 'vram_available_bytes'),
                                      ('max_cpu_percent', 'cpu_percent')] if key in value}


def evaluate(value, now, mode, metrics):
    if 'allowed_modes' in value and mode not in value['allowed_modes']:
        return 'mode_condition'
    local_config = value.get('window', {})
    local = now.astimezone(timezone(timedelta(minutes=local_config['offset_minutes']))) if 'offset_minutes' in local_config else now.astimezone()
    if 'weekdays' in value and local.weekday() not in value['weekdays']:
        return 'weekday_condition'
    if 'window' in value and not in_window(now, value['window']):
        return 'time_window'
    for metric in metrics_needed(value):
        sample = metrics.get(metric)
        if type(sample) not in (int, float) or not math.isfinite(sample) or sample < 0:
            return 'metric_unavailable'
    if 'min_ram_available_mib' in value and metrics['ram_available_bytes'] < value['min_ram_available_mib'] * 1024**2:
        return 'ram_condition'
    if 'min_vram_available_mib' in value and metrics['vram_available_bytes'] < value['min_vram_available_mib'] * 1024**2:
        return 'vram_condition'
    if 'max_cpu_percent' in value and metrics['cpu_percent'] > value['max_cpu_percent']:
        return 'cpu_condition'
    return None


def read_metrics(keys):
    result = {}
    if 'vram_available_bytes' in keys:
        from .models import resources
        result.update(resources())
    elif 'ram_available_bytes' in keys:
        from karen_task_tools import memory_sample
        try:
            result.update(memory_sample({}, threading.Event()))
        except (OSError, ValueError):
            pass
    if 'cpu_percent' in keys:
        from karen_task_tools import cpu_sample
        try:
            result.update(cpu_sample({}, threading.Event()))
        except (OSError, ValueError):
            pass
    return result
