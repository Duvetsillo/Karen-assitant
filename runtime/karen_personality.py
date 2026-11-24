"""Shared style and activation rules for the original Karen application."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'desktop-pet/python'))
from dialogue_style import personality as base_personality
from wake_word import wake_command
from voice_style import validate_style

STYLE_LABELS = {
    'serene': 'Serena: madura y pausada', 'warm': 'Cercana: calida',
    'serious': 'Seria: sobria', 'bright': 'Alegre: ligera',
    'wry': 'Ironia suave', 'neutral': 'Original: sin ajustar',
}


def personality(style=None, suggestions=True, sarcasm=True):
    """Apply the persisted identity to every provider without changing model weights."""
    from personal_profile import load, instructions
    profile = load()
    # Explicit legacy toggles remain stricter than a proactive saved preference.
    if not suggestions:
        profile['initiative'] = 'passive'
    return base_personality(style or profile['tone'],
                            suggestions and profile['initiative'] != 'passive',
                            sarcasm and profile['humor'] != 'none') + ' ' + instructions(profile)
