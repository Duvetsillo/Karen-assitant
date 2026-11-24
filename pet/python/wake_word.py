"""Local addressed-name matching shared with Karen's desktop client."""
import re
import unicodedata

PATTERN = re.compile(r'^(?:(?:oye|hola|hey|ok|okay)[,\s]+)?(?:karen|caren)\b[\s,;:.!?¿¡-]*', re.I)


def wake_command(text):
    clean = text.strip().lstrip('¿¡ ')
    normalized = ''.join(c for c in unicodedata.normalize('NFD', clean) if not unicodedata.combining(c))
    match = PATTERN.match(normalized)
    return clean[match.end():].strip() if match else None
