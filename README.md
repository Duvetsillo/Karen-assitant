# 🤖 Karen — Asistente de Voz Local y Autohospedado

Karen es un asistente de voz personal, gratuito y 100% local, inspirado en Jarvis (Iron Man). Corre sobre un home server con Proxmox (sin GPU, hardware modesto) y un cliente de voz en Windows, sin depender de APIs de pago ni de internet para el razonamiento.

> 📌 Proyecto en desarrollo activo. Este repo documenta el proceso completo: decisiones, errores, soluciones y el roadmap hacia un agente que no solo conversa, sino que controla el sistema operativo.

---

## ✨ Qué hace hoy

- Escucha por voz, transcribe con **Whisper** (local, sin internet)
- Razona con un **LLM local vía Ollama** (`llama3.2:3b`)
- Responde por voz con **Edge-TTS** en español
- Corre como servicio systemd en una LXC de Proxmox (arranque automático)
- Tiene preparada la integración de activación por palabra clave con `openWakeWord`; falta validar y desplegar el modelo personalizado `karen.onnx`
- Personalidad propia (tipo VIERAS/Iron Man), se dirige al usuario como "Jefe" o por su nombre

## 🎯 Hacia dónde va

Karen está evolucionando de un chatbot de voz a un agente que puede:
- Abrir/cerrar aplicaciones, controlar el sistema (apagar, bloquear, volumen)
- Controlar el navegador (Selenium) y el escritorio (pyautogui)
- Tener memoria persistente (SQLite) entre sesiones
- Funcionar con una interfaz gráfica simple

Ver el detalle completo en [`docs/KAREN_Roadmap.md`](docs/KAREN_Roadmap.md).

---

## 🏗️ Arquitectura

```
Windows (micrófono)
    │
    ▼
openwakeword ("Karen") + filtro de voz/silencio
    │
    ▼
Whisper STT (transcripción local)
    │
    ▼ HTTP POST :5000
Flask Server (LXC en Proxmox, systemd)
    │
    ▼
Ollama API :11434
    │
    ▼
llama3.2:3b
    │
    ▼ respuesta texto
Edge-TTS (es-ES-ElviraNeural)
    │
    ▼
Windows (altavoz)
```

## 🧰 Stack

| Capa | Tecnología |
|---|---|
| LLM | Ollama + `llama3.2:3b` |
| STT | OpenAI Whisper (`base`) |
| TTS | Edge-TTS (`es-ES-ElviraNeural`) |
| Wake word | openWakeWord 0.6.0 (ONNX) |
| Backend | Flask (Python) |
| Infraestructura | Proxmox VE + LXC, systemd |
| Cliente | Python 3.11 en Windows |

## 🖥️ Hardware

Corre sobre un servidor casero modesto, sin GPU:
- Intel i5-3500T (3ra gen)
- ~12 GB RAM
- 4 GB de swap

Esto es una restricción de diseño constante: cualquier modelo por encima de ~3B parámetros arriesga agotar la RAM disponible.

---

## 📂 Estructura del repo

```
karen-assistant/
└── docs/
    ├── KAREN_Bitacora.md   # Log técnico de la instalación inicial
    ├── KAREN_Errores.md    # Errores encontrados y sus soluciones
    └── KAREN_Roadmap.md    # Roadmap por fases
```

> El código operativo vive actualmente en el cliente Windows y en la LXC. Aún falta sincronizar y versionar aquí `cliente.py`, `server.py` y `requirements.txt`.

---

## 🚀 Cómo correrlo

### 1. Servidor (LXC / Linux)

> Referencia de despliegue: el servicio de producción corre como `karen.service`. Los archivos de código todavía no están incluidos en este repositorio.
```bash
sudo systemctl status karen.service
curl http://localhost:5000/salud
```

### 2. Cliente (Windows)
```powershell
cd C:\karen
pip install -r requirements.txt
python cliente.py
```

> Nota: requiere `ffmpeg.exe` accesible (ver [`docs/KAREN_Errores.md`](docs/KAREN_Errores.md) para el setup en Windows).

---

## 📖 Documentación

- [Bitácora técnica](docs/KAREN_Bitacora.md) — cómo se montó todo, paso a paso
- [Registro de errores](docs/KAREN_Errores.md) — problemas reales y cómo se resolvieron
- [Roadmap](docs/KAREN_Roadmap.md) — fases del proyecto, de chatbot a agente de control del PC

## 📌 Estado al 29 de agosto de 2026

- Fases 1 y 2 completadas: flujo voz → LLM → voz, `llama3.2:3b`, personalidad de Karen y servicio systemd.
- Fase 3 en progreso: se generaron muestras sintéticas para entrenar la wake word; está pendiente confirmar el entrenamiento y obtener `karen.onnx`.
- El siguiente hito es desplegar el modelo ONNX en el cliente Windows y activar `WAKE_WORD_ACTIVO`.

---

## 👤 Autor

Proyecto personal de Dayver — un asistente de voz local como alternativa gratuita a los asistentes de pago, construido fase por fase sobre hardware casero.
