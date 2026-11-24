"""Only final answers may enter the conversation and speech pipeline."""
import re


def final_answer(value):
    text = value.strip()
    while True:
        opening = re.match(r'^<(think|analysis|reasoning)>', text, re.I)
        if not opening:
            break
        closing = re.search(r'</' + opening.group(1) + r'>', text[opening.end():], re.I)
        if not closing:
            raise ValueError('El modelo devolvió razonamiento sin respuesta final. Revisa su plantilla o cambia de modelo.')
        text = text[opening.end() + closing.end():].strip()
    if not text:
        raise ValueError('El modelo no devolvió una respuesta final')
    return text
