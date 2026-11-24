"""Shared style and activation rules for the original Karen application."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'desktop-pet/python'))
from dialogue_style import personality
from wake_word import wake_command
from voice_style import validate_style

STYLE_LABELS = {
    'serene': 'Serena: madura y pausada', 'warm': 'Cercana: calida',
    'serious': 'Seria: sobria', 'bright': 'Alegre: ligera',
    'wry': 'Ironia suave', 'neutral': 'Original: sin ajustar',
}
