"""Fast, explicit Home Assistant commands for Karen.

The private webhook ID lives in .private/ha_bridge.json, never in settings.json.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse

import requests


CONFIG_PATH = Path(__file__).resolve().parent / ".private" / "ha_bridge.json"
DEVICES = {
    "luz": ("switch.dormitorio_luz_interruptor_1", ("luz", "lampara", "bombillo")),
    "abanico": ("switch.smart_switch_6231", ("abanico", "ventilador")),
    "cargador": ("switch.smart_switch_dd5a", ("cargador", "escritorio")),
    "nevera": ("switch.smart_switch_d557", ("nevera", "refrigerador", "frigorifico")),
    "air fryer": ("switch.smart_switch_1a83", ("air fryer", "airfryer", "freidora", "horno")),
}
ROOM = ("luz", "abanico", "cargador")
ON = {"enciende", "encender", "prende", "prender", "activa", "activar", "conecta", "conectar"}
OFF = {"apaga", "apagar", "desactiva", "desactivar", "desconecta", "desconectar"}
STATUS = {"estado", "como", "esta", "estan", "encendido", "encendida", "apagado", "apagada"}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def parse_command(prompt: str):
    text = _normalize(prompt)
    sequence = text.split()
    words = set(sequence)
    if text.startswith(("por que ", "porque ", "cuando ")):
        return None
    if any(word == "no" and any(next_word in ON | OFF for next_word in sequence[index + 1:index + 4])
           for index, word in enumerate(sequence)):
        return None
    actions = ({"on"} if words & ON else set()) | ({"off"} if words & OFF else set())
    if len(actions) > 1:
        return ("ambiguous", ())
    action = next(iter(actions), "status" if words & STATUS or text.startswith("que tal") else None)
    if action is None:
        return None
    matches = [name for name, (_, aliases) in DEVICES.items()
               if any(re.search(r"\b" + re.escape(alias) + r"\b", text) for alias in aliases)]
    if not matches and re.search(r"\b(cuarto|habitacion|dormitorio)\b", text):
        matches = list(ROOM)
    if not matches:
        if action in {"on", "off"} and "todo" in words:
            return ("ambiguous_target", ())
        return None
    return action, tuple(dict.fromkeys(matches))


class HomeAssistantControl:
    def __init__(self, path: Path = CONFIG_PATH, session=None):
        self.path = path
        self.session = session or requests.Session()

    def execute(self, prompt: str) -> str | None:
        parsed = parse_command(prompt)
        if parsed is None:
            return None
        action, names = parsed
        if action == "ambiguous":
            return "Dime si quieres encender o apagar."
        if action == "ambiguous_target":
            return "Dime qué dispositivo o pide encender o apagar el cuarto."
        if not self.path.exists():
            return "Control de casa sin configurar."
        try:
            config = json.loads(self.path.read_text(encoding="utf-8"))
            if (not isinstance(config, dict) or
                    any(not isinstance(config.get(key), str) or not config[key].strip()
                        for key in ('url', 'webhook_id'))):
                raise ValueError('Configuración de Home Assistant incompatible.')
            url = config["url"].rstrip("/") + "/api/webhook/" + config["webhook_id"]
            response = self.session.post(url, json={"action": action,
                                                     "entities": [DEVICES[name][0] for name in names]},
                                         timeout=(1.0, 5.0))
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError('Respuesta de Home Assistant incompatible.')
            if not result.get("ok"):
                return "HA rechazó la orden: " + str(result.get("error", "sin detalle"))
            states = result.get("states", {})
            if not isinstance(states, dict):
                raise ValueError('Estados de Home Assistant incompatibles.')
            accepted = result.get("accepted") is True
            labels = {"on": "encendido", "off": "apagado", "unavailable": "sin conexión", "unknown": "sin datos"}
            chunks = []
            for name in names:
                state = states.get(DEVICES[name][0], "unknown")
                if not isinstance(state, str):
                    state = 'unknown'
                if action != "status" and accepted and state != action:
                    chunks.append(f"{name.capitalize()}: orden enviada; HA aún muestra {labels.get(state, state)}")
                else:
                    chunks.append(f"{name.capitalize()}: {labels.get(state, state)}")
            return ". ".join(chunks) + "."
        except (OSError, requests.RequestException, ValueError, KeyError, TypeError):
            return "No pude conectar con Home Assistant. La orden no está confirmada."


class HomeAssistantDiscovery:
    """Read-only Home Assistant REST discovery; never authorizes control."""

    def __init__(self, url=None, token=None, session=None):
        self.url = url if url is not None else os.getenv('KAREN_HA_API_URL', '')
        self.token = token if token is not None else os.getenv('KAREN_HA_API_TOKEN', '')
        if url is None and token is None and not self.url and not self.token:
            from karen_core2.home import HomeAssistant
            config = HomeAssistant().config
            if config:
                self.url, self.token = config['url'], config['token']
        self.session = session or requests.Session()

    def list_entities(self, domain=None, limit=50):
        if not self.url or not self.token:
            raise ValueError('Configura KAREN_HA_API_URL y KAREN_HA_API_TOKEN.')
        parsed = urlparse(self.url)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or
                parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('URL de Home Assistant inválida.')
        if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('La API remota de Home Assistant requiere HTTPS.')
        if domain is not None and not re.fullmatch(r'[a-z_]{2,32}', domain):
            raise ValueError('Dominio de entidad inválido.')
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Límite inválido.')
        response = self.session.get(self.url.rstrip('/') + '/api/states',
                                    headers={'Authorization': 'Bearer ' + self.token},
                                    timeout=(2.0, 8.0))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError('Respuesta de entidades incompatible.')
        entities = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            entity_id, state = item.get('entity_id'), item.get('state')
            if not isinstance(entity_id, str) or not re.fullmatch(r'[a-z_]{2,32}\.[a-z0-9_]{1,128}', entity_id):
                continue
            if domain and entity_id.partition('.')[0] != domain:
                continue
            if not isinstance(state, str):
                continue
            attributes = item.get('attributes')
            name = attributes.get('friendly_name') if isinstance(attributes, dict) else None
            if not isinstance(name, str) or not name.strip():
                name = entity_id
            entities.append({'entity_id': entity_id, 'name': name[:100], 'state': state[:100]})
            if len(entities) >= limit:
                break
        return entities


def main() -> None:
    parser = argparse.ArgumentParser(description="Control explícito de Home Assistant")
    parser.add_argument("action", choices=("status", "on", "off"))
    parser.add_argument("device", choices=(*DEVICES, "cuarto"))
    args = parser.parse_args()
    verb = {"status": "estado de", "on": "enciende", "off": "apaga"}[args.action]
    result = HomeAssistantControl().execute(f"{verb} {args.device}")
    print(result or "Orden no reconocida.")


if __name__ == "__main__":
    main()
