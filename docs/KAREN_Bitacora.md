# 🤖 Karen — Asistente de Voz Local con Ollama
**Fecha:** 2026-06-07
**Duración:** ~3 horas
**Estado:** ✅ Funcional (con gemma3:1b)

> 📝 **Nota:** este proyecto se llamó originalmente "Jarvis". Esta bitácora documenta la sesión de instalación inicial y se conserva tal cual se escribió en su momento (por eso aparecen rutas y nombres `jarvis`). Las sesiones posteriores ya usan `karen` como nombre del proyecto.

---

## 🎯 Objetivo

Montar un asistente de voz local tipo Jarvis/Claude Code usando Ollama, sin costo, aprovechando un servidor Proxmox con i5 3ra generación y 12GB de RAM.

---

## 🏗️ Arquitectura Final

```
Windows (micrófono)
    │
    ▼
Whisper STT (transcripción local)
    │
    ▼ HTTP POST :5000
Flask Server (LXC en Proxmox)
    │
    ▼
Ollama API :11434
    │
    ▼
Modelo LLM (gemma3:1b / qwen2.5:7b)
    │
    ▼ respuesta texto
Edge-TTS (síntesis de voz)
    │
    ▼
Windows (altavoz)
```

---

## 🖥️ Infraestructura

| Componente | Detalle |
|---|---|
| Servidor | Proxmox VE 9.2.3 |
| Contenedor Ollama | LXC (Linux) |
| IP LXC | 192.168.100.66 |
| Cliente | Windows (PC separada) |
| Modelos disponibles | qwen2.5:7b (4.7GB), gemma3:1b (815MB) |
| Modelo en uso | gemma3:1b |

---

## 📋 Proceso de Instalación

### PARTE 1 — Servidor en el LXC

#### 1.1 Exponer Ollama a la red

Por defecto Ollama solo escucha en `127.0.0.1`. Para abrirlo a la red local:

```bash
systemctl edit ollama
```

Se agregó al archivo `/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
systemctl daemon-reload
systemctl restart ollama
```

**Verificación:**
```bash
curl http://localhost:11434
# Respuesta: Ollama is running
```

#### 1.2 Instalar dependencias Python

```bash
apt update && apt install -y python3 python3-pip python3-venv
python3 -m venv ~/jarvis-server
source ~/jarvis-server/bin/activate
pip install flask requests
```

#### 1.3 Descargar modelos

```bash
ollama pull qwen2.5:7b   # 4.7GB
ollama pull gemma3:1b    # 815MB
ollama list              # verificar
```

#### 1.4 Servidor Flask (`~/jarvis/server.py`)

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma3:1b"  # cambiado de qwen2.5:7b por problemas de respuesta

SYSTEM_PROMPT = """Eres Jarvis, un asistente personal inteligente que responde siempre en español.
Sé conciso y directo. Tus respuestas serán convertidas a voz, así que:
- No uses markdown, asteriscos, ni listas con guiones
- Responde en oraciones naturales y cortas
- Máximo 3 oraciones salvo que te pidan algo largo
- Nunca escribas emojis"""

historial = []

@app.route('/chat', methods=['POST'])
def chat():
    global historial
    data = request.json
    texto = data.get('mensaje', '')
    if data.get('reset'):
        historial = []
        return jsonify({'respuesta': 'Historial limpiado.'})
    historial.append({"role": "user", "content": texto})
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + historial,
        "stream": False
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        respuesta = r.json()['message']['content']
        historial.append({"role": "assistant", "content": respuesta})
        if len(historial) > 40:
            historial = historial[-40:]
        return jsonify({'respuesta': respuesta})
    except Exception as e:
        return jsonify({'respuesta': f'Error: {str(e)}'}), 500

@app.route('/salud', methods=['GET'])
def salud():
    return jsonify({'estado': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

#### 1.5 Iniciar servidor

```bash
source ~/jarvis-server/bin/activate
python ~/jarvis/server.py
# Running on http://0.0.0.0:5000
# Running on http://192.168.100.66:5000
```

---

### PARTE 2 — Cliente en Windows

#### 2.1 Instalar Python

- Descargado `python-3.11.0-amd64.exe` desde python.org
- **Error inicial:** No se marcó "Add Python to PATH" en la primera pantalla
- **Solución:** Reinstalar y en "Advanced Options" marcar ✅ "Add Python to environment variables"

#### 2.2 Instalar dependencias

```powershell
pip install requests
pip install edge-tts
pip install sounddevice
pip install soundfile
pip install numpy
pip install openai-whisper   # descarga PyTorch, tarda varios minutos
pip install imageio[ffmpeg]  # intento fallido de instalar ffmpeg
```

#### 2.3 Instalar ffmpeg (problemático)

**Intento 1 — winget:**
```powershell
winget install ffmpeg
# Se instaló pero no quedó en PATH
```

**Intento 2 — Agregar al PATH manualmente:**
```powershell
[System.Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\Dayver\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_...\bin", "Machine")
# No funcionó, ruta con caracteres especiales
```

**Intento 3 — imageio_ffmpeg:**
```python
import imageio_ffmpeg
os.environ["PATH"] = imageio_ffmpeg.get_ffmpeg_exe().rsplit(os.sep, 1)[0] + ...
# Error: módulo no reconocido en el contexto
```

**Solución final — Descarga manual:**
```powershell
cd C:\jarvis
Invoke-WebRequest -Uri "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -OutFile "ffmpeg.zip"
Expand-Archive -Path "ffmpeg.zip" -DestinationPath "C:\jarvis\ffmpeg_temp"
Copy-Item "C:\jarvis\ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" "C:\jarvis\"
Copy-Item "C:\jarvis\ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe" "C:\jarvis\"
Remove-Item -Recurse "C:\jarvis\ffmpeg_temp"
Remove-Item "C:\jarvis\ffmpeg.zip"
```

ffmpeg.exe copiado directamente en `C:\jarvis\` y referenciado desde el código:
```python
os.environ["PATH"] = r"C:\jarvis" + os.pathsep + os.environ["PATH"]
```

#### 2.4 Cliente (`C:\jarvis\cliente.py`)

```python
import sounddevice as sd
import soundfile as sf
import numpy as np
import whisper
import requests
import edge_tts
import asyncio
import tempfile
import os
import sys

os.environ["PATH"] = r"C:\jarvis" + os.pathsep + os.environ["PATH"]

SERVIDOR = "http://192.168.100.66:5000"
SAMPLE_RATE = 16000
VOZ = "es-ES-AlvaroNeural"

print("Cargando Whisper...")
modelo_whisper = whisper.load_model("base")
print("Whisper listo\n")

def grabar_voz(segundos=5):
    print(f"Grabando {segundos} segundos... habla ahora")
    audio = sd.rec(int(segundos * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()

def transcribir(audio_np):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        ruta = f.name
    sf.write(ruta, audio_np, SAMPLE_RATE)
    resultado = modelo_whisper.transcribe(ruta, language="es", fp16=False)
    os.unlink(ruta)
    return resultado["text"].strip()

def preguntar_jarvis(texto):
    try:
        r = requests.post(f"{SERVIDOR}/chat", json={"mensaje": texto}, timeout=90)
        return r.json()["respuesta"]
    except Exception as e:
        return f"Error: {e}"

async def hablar_async(texto):
    communicate = edge_tts.Communicate(texto, VOZ)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        ruta = f.name
    await communicate.save(ruta)
    data, fs = sf.read(ruta)
    sd.play(data, fs)
    sd.wait()
    os.unlink(ruta)

def hablar(texto):
    asyncio.run(hablar_async(texto))

def main():
    print("JARVIS listo. Di salir para terminar.\n")
    while True:
        try:
            entrada = input("ENTER para hablar (o escribe los segundos): ").strip()
            segundos = int(entrada) if entrada.isdigit() else 5
            audio = grabar_voz(segundos)
            texto = transcribir(audio)
            if not texto:
                print("No entendi, intenta de nuevo.\n")
                continue
            print(f"Tu: {texto}\n")
            if "salir" in texto.lower():
                hablar("Hasta luego.")
                break
            if "reset" in texto.lower():
                requests.post(f"{SERVIDOR}/chat", json={"reset": True})
                print("Memoria limpiada\n")
                continue
            print("Jarvis pensando...")
            respuesta = preguntar_jarvis(texto)
            print(f"Jarvis: {respuesta}\n")
            hablar(respuesta)
        except KeyboardInterrupt:
            sys.exit()

if __name__ == "__main__":
    main()
```

---

## 🐛 Errores y Soluciones

| Error | Causa | Solución |
|---|---|---|
| `pip no reconocido` | Python no instalado aún | Instalar python-3.11.0-amd64.exe |
| `python no reconocido` | "Add to PATH" no marcado | Reinstalar marcando "Add Python to environment variables" |
| `FileNotFoundError ffmpeg` | ffmpeg no en PATH | Copiar ffmpeg.exe a `C:\jarvis\` y agregar al PATH desde código |
| `SyntaxError: expected except or finally` | Indentación rota al pegar en Notepad | Recrear archivo con `Out-File` desde PowerShell |
| `Connection aborted` | Servidor Flask caído | Levantarlo de nuevo con `python ~/jarvis/server.py` |
| `Address already in use :5000` | Flask ya corriendo en background | No hace falta levantarlo de nuevo, ya está activo |
| `Ollama: Server disconnected` en WebUI | Ollama no escuchaba en red | Agregar `OLLAMA_HOST=0.0.0.0:11434` via `systemctl edit ollama` |
| qwen2.5:7b no responde bien | Posible problema con el modelo o RAM | Cambiar a gemma3:1b en server.py |

---

## ▶️ Cómo Usar

### Iniciar servidor (LXC)
```bash
source ~/jarvis-server/bin/activate
python ~/jarvis/server.py
```

### Iniciar cliente (Windows)
```powershell
cd C:\jarvis
python cliente.py
```

### Comandos de voz
| Dices | Acción |
|---|---|
| Cualquier pregunta | Responde por voz |
| "reset" / "limpiar" | Borra el historial de conversación |
| "salir" | Cierra el cliente |

---

## 🔧 Archivos del Proyecto

```
LXC Proxmox:
~/jarvis/server.py
~/jarvis-server/          (virtualenv)

Windows:
C:\jarvis\cliente.py
C:\jarvis\ffmpeg.exe
C:\jarvis\ffprobe.exe
```

---

## 🚀 Mejoras Pendientes

- [ ] Cambiar gemma3:1b por llama3.2:3b (mejor calidad, aún liviano)
- [ ] Activación por palabra clave ("Jarvis") sin presionar ENTER
- [ ] Detección automática de silencio (sin segundos fijos)
- [ ] Ejecutar servidor Flask como servicio systemd (arranque automático)
- [ ] Interfaz gráfica con botón push-to-talk
- [ ] Probar qwen2.5:7b con `ollama run qwen2.5:7b` para diagnosticar

---

## 📦 Dependencias Completas

### LXC (Python)
- flask
- requests

### Windows (Python)
- openai-whisper
- sounddevice
- soundfile
- numpy
- requests
- edge-tts
- imageio[ffmpeg]

### Binarios Windows
- ffmpeg.exe (en C:\jarvis\)
- ffprobe.exe (en C:\jarvis\)

---

📎 Ver también: [KAREN_Errores](KAREN_Errores.md) · [KAREN_Roadmap](KAREN_Roadmap.md)
