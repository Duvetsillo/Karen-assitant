"""Reversible minimal HA layout; preserves existing cards under explicit details."""
from copy import deepcopy


def tile(entity, name=None):
    result = {'type': 'tile', 'entity': entity}
    if name:
        result['name'] = name
    return result


def group(title, cards, *, columns=1, wide=False, collapsed=False):
    return dict(title=title, cards=cards, columns=columns, wide=wide, collapsed=collapsed)


def original_cards(view):
    cards = list(view.get('cards', []))
    for section in view.get('sections', []):
        cards.extend(section.get('cards', []))
    return cards


def redesign(config):
    """Pure transformation, no entities/services/security settings changed."""
    result = deepcopy(config)
    if result['views'][0].get('cards', [{}])[0].get('type') == 'custom:karen-house-card':
        for view in result['views']:
            cards = view.get('cards', [])
            if cards and cards[0].get('type') == 'custom:karen-house-card':
                view['background'] = '#111b20'
                view['subview'] = view.get('path') != 'panorama'
                for metric in cards[0].get('metrics', []):
                    if metric['entity'] == 'binary_sensor.docsis_estado_wan':
                        metric['states'] = {'on': 'Conectado', 'off': 'Sin conexión'}
                    elif metric['entity'] == 'binary_sensor.bati_cueva_puerta':
                        metric['states'] = {'on': 'Abierta', 'off': 'Cerrada'}
        return result
    existing = {v.get('path'): v for v in result['views']}
    home = existing['panorama']
    root = home['cards'][0]
    native = next(deepcopy(c) for c in root['cards'] if c['type'] == 'custom:karen-home-card')
    native['hide_media'] = True
    location = next(deepcopy(c) for c in root['cards'] if c['type'] == 'custom:karen-location-card')
    controls = [tile('switch.dormitorio_luz_interruptor_1', 'Luz del cuarto'),
                tile('switch.smart_switch_6231', 'Abanico'),
                tile('switch.smart_switch_d557', 'Nevera'),
                tile('binary_sensor.bati_cueva_puerta', 'Puerta')]
    navigate = lambda title, path, icon: {'type': 'button', 'name': title, 'icon': icon,
        'tap_action': {'action': 'navigate', 'navigation_path': '/dashboard-casa/' + path}}
    layouts = {
        'panorama': ('Tu casa.', 'Un lugar para ver lo importante y hacer espacio para lo demás.', [
            group('A mano', controls, columns=2),
            group('Hoy', [{'type': 'weather-forecast', 'entity': 'weather.forecast_casa', 'show_forecast': False},
                          navigate('Conversar con Karen', 'karen', 'mdi:creation')]),
            group('Tus espacios', [navigate('Habitación', 'casa', 'mdi:bed-outline'),
                                   navigate('Sala y cocina', 'sala-cocina', 'mdi:sofa-outline'),
                                   navigate('Familia y ubicación', 'familia', 'mdi:map-marker-outline'),
                                   navigate('Home Lab', 'homelab', 'mdi:server-outline')], columns=4, wide=True)]),
        'casa': ('Tu habitación.', 'Luz, ambiente y entretenimiento.', [
            group('Ambiente', controls[:2] + [tile('switch.smart_switch_dd5a', 'Cargador'), tile('light.dormitorio_luz_luz_de_fondo', 'Luz de fondo')], columns=2),
            group('Entretenimiento', [{'type': 'media-control', 'entity': 'media_player.dormitorio_fire_tv_dormitorio'},
                                      {'type': 'media-control', 'entity': 'media_player.echo_show_de_dayver'}])]),
        'sala-cocina': ('Sala y cocina.', 'Lo cotidiano, al alcance.', [
            group('Equipos', [tile('switch.smart_switch_d557', 'Nevera'), tile('switch.smart_switch_1a83', 'Air fryer')], columns=2),
            group('Seguridad', [tile('binary_sensor.blink_proxy_living_room_motion', 'Movimiento'),
                               tile('switch.blink_proxy_living_room_motion_detection', 'Detección de movimiento')]),
            group('Cámara', [{'type': 'picture-entity', 'entity': 'camera.blink_proxy_living_room', 'camera_view': 'auto', 'show_state': False},
                            {'type': 'custom:blink-live-button'}], wide=True, collapsed=True)]),
        'homelab': ('Home Lab.', 'Recursos y conexiones, sin perder la perspectiva.', [
            group('Datacenter', [tile('sensor.homelab_datacenter_cpu', 'CPU'), tile('sensor.homelab_datacenter_ram', 'Memoria'), tile('sensor.homelab_lxc_activos', 'LXC activos'), tile('sensor.homelab_docker_activos', 'Contenedores')], columns=2),
            group('Red', [tile('binary_sensor.homelab_unifi_controlador', 'UniFi'), tile('sensor.usw_flex_mini_estado', 'Switch'), tile('binary_sensor.docsis_estado_wan', 'Internet')])]),
        'diagnostico': ('Estado del sistema.', 'Lecturas y diagnóstico. Sin reparaciones automáticas.', [
            group('Conectividad', [tile('binary_sensor.docsis_estado_wan', 'Internet'), tile('binary_sensor.pc_principal_red', 'PC principal'), tile('binary_sensor.homelab_red', 'Home Lab')], columns=2),
            group('Avisos', [tile('sensor.icloud3_alerts', 'iCloud3'), tile('sensor.icloud3_event_log', 'Registro')])]),
        'familia': ('Cerca, a tu manera.', 'Ubicaciones compartidas. Una lectura antigua no confirma la posición actual.', [group('Tus dispositivos', [location], wide=True)]),
        'karen': ('Habla con Karen.', 'Consulta tu casa o continúa una conversación.', [group('Tu asistente local', [native], wide=True)]),
    }
    metrics = [dict(name='Internet', entity='binary_sensor.docsis_estado_wan', states={'on': 'Conectado', 'off': 'Sin conexión'}),
               dict(name='Puerta', entity='binary_sensor.bati_cueva_puerta', states={'on': 'Abierta', 'off': 'Cerrada'}),
               dict(name='Luz del cuarto', entity='switch.dormitorio_luz_interruptor_1'),
               dict(name='Abanico', entity='switch.smart_switch_6231')]
    for path, (title, subtitle, groups) in layouts.items():
        view = existing.get(path)
        if view is None:
            view = {'path': path, 'title': 'Karen' if path == 'karen' else 'Familia'}
            result['views'].append(view)
        else:
            groups.append(group('Todos los controles anteriores', original_cards(view), wide=True, collapsed=True))
        for key in ('sections', 'max_columns', 'subview', 'layout'):
            view.pop(key, None)
        view.update(type='panel', theme='Karen Calm', background='#111b20')
        view['subview'] = path != 'panorama'
        view['cards'] = [dict(type='custom:karen-house-card', title=title, subtitle=subtitle,
                              path=path, metrics=deepcopy(metrics) if path == 'panorama' else [], groups=groups)]
    return result
