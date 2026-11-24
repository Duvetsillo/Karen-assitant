"""Bounded public evidence and Windows-user encrypted private plan payloads."""
import base64
import hashlib
import json
import re

SECRET = re.compile(r'(?i)(password|passwd|contrase[nñ]a|api[_ -]?key|access[_ -]?token|secret|authorization|cookie|credential)')
ASSIGNMENT = re.compile(r'(?i)\b(password|passwd|api[_ -]?key|token|secret|authorization)\s*[:=]\s*\S+')


def public(value, depth=0):
    if depth > 8:
        return '[límite de profundidad]'
    if isinstance(value, dict):
        return {str(k)[:80]: '[redactado]' if SECRET.search(str(k)) else public(v, depth + 1)
                for k, v in list(value.items())[:100]}
    if isinstance(value, (list, tuple)):
        return [public(item, depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return ASSIGNMENT.sub(r'\1=[redactado]', value[:12000])
    if value is None or type(value) in (bool, int, float):
        return value
    return type(value).__name__


def fingerprint(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


def seal(value):
    from icloud_calendar import crypt
    return base64.b64encode(crypt(json.dumps(value, ensure_ascii=False, allow_nan=False).encode())).decode('ascii')


def unseal(value):
    from icloud_calendar import crypt
    return json.loads(crypt(base64.b64decode(value), decrypt=True).decode())
