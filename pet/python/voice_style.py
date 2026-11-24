"""Prosody presets for a fixed identity; Qwen Base has no emotion instruction API."""
import io
from pathlib import Path
import shutil
import subprocess

# tempo, semitones, high-frequency EQ. Never select another speaker or reference.
STYLES = {
    'neutral': (1.0, 0.0, 0.0),
    'serene': (0.94, -0.8, -1.5),
    'warm': (0.98, -0.3, -0.5),
    'serious': (0.97, -1.0, -1.0),
    'bright': (1.04, 0.3, 0.0),
    'wry': (0.96, -0.5, -0.5),
}


def validate_style(style):
    if style not in STYLES:
        raise ValueError('Estilo de voz desconocido')
    return style


def style_audio(audio, root, style='neutral'):
    validate_style(style)
    if style == 'neutral':
        return audio
    import soundfile as sf
    speed, semitones, treble = STYLES[style]
    executable = Path(root) / 'ffmpeg.exe'
    command = str(executable) if executable.is_file() else shutil.which('ffmpeg')
    if not command:
        raise RuntimeError('Instala FFmpeg para los estilos; el perfil original permanece intacto')
    pitch = 2 ** (semitones / 12)
    result = subprocess.run([
        command, '-hide_banner', '-loglevel', 'error', '-i', 'pipe:0',
        '-af', f'rubberband=tempo={speed}:pitch={pitch:.8f}:formant=preserved,equalizer=f=3200:t=q:w=0.8:g={treble}',
        '-f', 'wav', '-c:a', 'pcm_s16le', 'pipe:1',
    ], input=audio, capture_output=True, timeout=30,
       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), cwd=str(Path(root)))
    if result.returncode or not result.stdout.startswith(b'RIFF'):
        raise RuntimeError('No se pudo aplicar el estilo a la voz original')
    # Rewrite the streaming WAV header so every audio decoder sees a valid length.
    samples, rate = sf.read(io.BytesIO(result.stdout), dtype='float32')
    output = io.BytesIO()
    sf.write(output, samples, rate, format='WAV', subtype='PCM_16')
    return output.getvalue()
