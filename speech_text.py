"""Prepare final answers for conversational speech without altering their meaning."""
import re
from answers import final_answer


def spoken_text(value):
    text = final_answer(value)
    text = re.sub(r'\[([^\]]+)\]\(https?://[^)]+\)', r'\1', text)
    text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*(?:[-*+] |\d+[.)] )', '', text, flags=re.MULTILINE)
    text = re.sub(r'```[^\n]*\n?', '', text)
    text = text.replace('`', '').replace('**', '').replace('__', '')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # A list or paragraph break is a speech boundary. Preserve punctuation so
    # questions and exclamations retain their natural intonation.
    return ' '.join(line if line[-1] in '.!?…:;,¿¡' else line + '.' for line in lines)
