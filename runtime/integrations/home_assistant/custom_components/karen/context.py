"""Small, read-only snapshots. No coordinates, URLs, secrets or tool calls."""
import json
import re
import unicodedata

DOMAINS = {'light', 'switch', 'fan', 'climate', 'weather', 'media_player', 'binary_sensor', 'sensor'}
ATTRS = {'friendly_name', 'unit_of_measurement', 'device_class', 'temperature', 'current_temperature', 'battery_level', 'media_title', 'app_name'}

def words(text):
    return set(re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode()))

def snapshot(states, query):
    terms = words(query)
    domains = set()
    if terms & {'luz', 'luces', 'iluminacion'}: domains.add('light')
    if terms & {'temperatura', 'calor', 'frio', 'clima'}: domains.update(('climate', 'weather'))
    if terms & {'tele', 'tv', 'netflix', 'reproduciendo', 'musica'}: domains.add('media_player')
    records = []
    for state in states:
        domain = state.entity_id.split('.')[0]
        if domain not in DOMAINS or re.search(r'password|token|secret|credential|clave|contrasena', state.entity_id, re.I): continue
        if domain == 'sensor':
            try: float(state.state)
            except (ValueError, TypeError):
                if state.state not in ('unknown', 'unavailable', 'on', 'off'): continue
        attrs = {k: v for k, v in state.attributes.items() if k in ATTRS and type(v) in (str, int, float, bool)}
        attrs = {k: v[:160] if isinstance(v, str) else v for k, v in attrs.items()}
        score = len(terms & words(state.entity_id + ' ' + str(attrs.get('friendly_name', '')))) * 5 + (8 if domain in domains else 0)
        if terms & {'desconectados', 'disponibles', 'conexion'} and state.state == 'unavailable': score += 10
        records.append((score, {'entity_id': state.entity_id, 'state': state.state[:80], 'attributes': attrs}))
    records.sort(key=lambda r: (-r[0], r[1]['entity_id']))
    selected = []
    for score, record in records[:24]:
        if len(json.dumps(selected + [record], ensure_ascii=False)) > 3000: break
        selected.append(record)
    return selected

def direct_answer(states, query):
    terms = words(query)
    # Only explicit questions, never interpret a requested action as performed.
    if not terms & {'que', 'cuales', 'cuantas', 'cuantos'}: return None
    if terms & {'luces', 'luz'} and terms & {'encendidas', 'encendida'}:
        lights = [s for s in states if s.entity_id.startswith('light.') or
                  (s.entity_id.startswith('switch.') and words(str(s.attributes.get('friendly_name', ''))) & {'luz', 'luces', 'lampara', 'iluminacion'})]
        if not lights: return 'No tengo luces accesibles en Home Assistant.'
        on = [str(s.attributes.get('friendly_name', s.entity_id)) for s in lights if s.state == 'on']
        unknown = sum(s.state in ('unknown', 'unavailable') for s in lights)
        result = ('Luces encendidas: ' + ', '.join(on[:20]) + '.') if on else 'Ninguna de las luces disponibles está encendida.'
        if unknown: result += f' Hay {unknown} luces sin estado confirmado.'
        return result
    if terms & {'dispositivos', 'entidades'} and (terms & {'desconectados', 'desconectadas'} or {'no', 'disponibles'} <= terms):
        missing = [str(s.attributes.get('friendly_name', s.entity_id)) for s in states if s.entity_id.split('.')[0] in DOMAINS and s.state == 'unavailable']
        if not missing: return 'No hay entidades no disponibles entre los estados que puedo consultar.'
        return 'Home Assistant marca como no disponibles: ' + ', '.join(missing[:15]) + (f'. Hay {len(missing)} en total.' if len(missing)>15 else '.') + ' Esto no demuestra por sí solo una desconexión física.'
    return None
