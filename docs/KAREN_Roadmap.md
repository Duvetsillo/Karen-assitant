# 🚀 Karen — Roadmap: De Asistente de Voz a Control Total del PC
**Proyecto:** [KAREN_Bitacora](KAREN_Bitacora.md)
**Errores resueltos:** [KAREN_Errores](KAREN_Errores.md)
**Fecha:** 2026-06-07
**Meta:** Convertir a Karen en un agente que escucha, razona y controla Windows como administrador — sin pagar nada.

---

## 🧭 Visión Final

```
Tú hablas → Karen escucha → Karen entiende → Karen actúa
              (Whisper)         (Ollama LLM)      (Python en Windows)
                                                      │
                                          ┌───────────┴───────────┐
                                          │                       │
                                    Archivos/Apps           Sistema/Red
                                    abrir, crear,           apagar, reiniciar,
                                    mover, borrar           ping, ssh, procesos
```

**Estado actual:** Karen escucha y responde por voz ✅
**Meta:** Karen también ejecuta acciones en tu PC 🎯

---

## 📊 Estado General del Proyecto

| Fase | Descripción | Estado |
|---|---|---|
| Fase 1 | Base funcional (voz → LLM → voz) | ✅ Completada |
| Fase 2 | Mejor modelo y calidad de respuesta | ⏳ En progreso |
| Fase 3 | Activación por palabra clave | 🔲 Pendiente |
| Fase 4 | Control del sistema operativo | 🔲 Pendiente |
| Fase 5 | Control de aplicaciones | 🔲 Pendiente |
| Fase 6 | Memoria persistente | 🔲 Pendiente |
| Fase 7 | Interfaz gráfica | 🔲 Pendiente |

---

## ✅ FASE 1 — Base Funcional (COMPLETADA)

> Todo lo que ya funciona hoy.

- [x] Ollama instalado en LXC de Proxmox
- [x] Ollama expuesto a la red local (`OLLAMA_HOST=0.0.0.0:11434`)
- [x] Modelos descargados: `gemma3:1b` y `qwen2.5:7b`
- [x] Servidor Flask corriendo en el LXC (puerto 5000)
- [x] Python instalado en Windows con PATH correcto
- [x] Whisper STT funcionando (transcripción local, sin internet)
- [x] Edge-TTS funcionando (síntesis de voz en español)
- [x] ffmpeg en `C:\jarvis\` y referenciado desde el código
- [x] Cliente de voz funcional en Windows
- [x] Historial de conversación (últimos 20 turnos)
- [x] Comando "reset" para limpiar memoria
- [x] Comando "salir" para cerrar el cliente

---

## ⏳ FASE 2 — Mejor Modelo y Calidad (EN PROGRESO)

> El gemma3:1b funciona pero da respuestas básicas. Necesitamos un modelo más capaz.

### 2.1 Probar llama3.2:3b (recomendado para tu hardware)

- [x] Descargar modelo en el LXC:
  ```bash
  ollama pull llama3.2:3b
  ```
- [x] Cambiar modelo en `~/karen/server.py`:
  ```python
  MODEL = "llama3.2:3b"
  ```
- [x] Reiniciar servidor Flask (ahora vía `karen.service` systemd)
- [x] Probar conversación y evaluar calidad de respuestas
- [ ] Comparar velocidad con gemma3:1b

### 2.2 Diagnosticar qwen2.5:7b

- [x] Probado: confirmado que agota la RAM (60+ seg de respuesta) → descartado
- [x] Modelo descartado en favor de `llama3.2:3b`

### 2.3 Mejorar el System Prompt

- [x] Personalidad tipo VIERAS/Iron Man, se dirige a Dayver como "Jefe" o "Dayver"
- [ ] Reforzar que Karen recuerde que puede ejecutar comandos en Windows (para Fase 4)
- [ ] Diferenciar mejor entre preguntas y comandos de acción

---

## 🔲 FASE 3 — Activación por Palabra Clave

> En vez de presionar ENTER, Karen escucha siempre y actúa al oír "Karen".

### 3.1 Wake word con openwakeword

- [x] `openwakeword 0.6.0` instalado
- [x] Modelo pre-entrenado `hey_jarvis` confirmado funcionando con alta confianza
- [x] 25 muestras de audio personalizadas de "Karen" grabadas en `C:\karen\muestras_karen\`
- [ ] Entrenar modelo custom de "Karen" — falló en Windows por dependencias, **plan: entrenar en la LXC de Linux y generar `karen.onnx` portable**
- [ ] Copiar `karen.onnx` a `C:\karen\` y cargarlo con `inference_framework="onnx"`

### 3.2 Detección automática de silencio (VAD)

- [x] Función `hay_voz()` implementada con `np.max` (cambiado desde `np.mean`) para detección de picos
- [x] `UMBRAL_VOZ = 0.15` configurado — pendiente de validar a fondo
- [ ] Confirmar que el filtro RMS de energía pre-transcripción (`np.sqrt(np.mean(audio_np**2)) > umbral`) en `cliente.py` está implementado y funcionando — está diseñado para corregir alucinaciones de Whisper transcribiendo silencio/ruido ambiente como frases fantasma

---

## 🔲 FASE 4 — Control del Sistema Operativo (OBJETIVO PRINCIPAL)

> Aquí Karen pasa de chatbot a agente real. Puede ejecutar comandos como administrador en tu PC.

### 4.1 Arquitectura del agente

```
Tú: "Karen, abre el administrador de tareas"
      │
      ▼
Whisper transcribe
      │
      ▼
Ollama interpreta la intención → devuelve JSON con acción
      │
      ▼
Python ejecuta el comando en Windows
      │
      ▼
Edge-TTS confirma: "Abriendo el administrador de tareas"
```

### 4.2 Modificar el servidor para devolver acciones

- [ ] Cambiar el System Prompt para que Ollama devuelva JSON cuando detecte un comando:
  ```python
  SYSTEM_PROMPT = """Eres Karen, un asistente que controla Windows.
  Cuando el usuario pida ejecutar algo, responde SOLO con JSON así:
  {"accion": "ejecutar", "comando": "taskmgr.exe", "confirmacion": "Abriendo el administrador de tareas"}
  Para preguntas normales responde en texto natural en español."""
  ```
- [ ] Modificar `server.py` para detectar si la respuesta es JSON o texto
- [ ] Enviar al cliente tanto la respuesta como la acción a ejecutar

### 4.3 Motor de ejecución en Windows (`C:\karen\ejecutor.py`)

- [ ] Crear el archivo ejecutor con estos comandos básicos:
  ```python
  import subprocess
  import os
  import psutil

  def ejecutar_accion(accion, comando):
      if accion == "ejecutar":
          subprocess.Popen(comando, shell=True)
      elif accion == "cerrar_proceso":
          for proc in psutil.process_iter():
              if comando.lower() in proc.name().lower():
                  proc.kill()
      elif accion == "abrir_url":
          os.startfile(comando)
      elif accion == "volumen_subir":
          # usando pycaw
          pass
      elif accion == "apagar":
          subprocess.run("shutdown /s /t 0", shell=True)
      elif accion == "reiniciar":
          subprocess.run("shutdown /r /t 0", shell=True)
  ```
- [ ] Instalar dependencias:
  ```powershell
  pip install psutil
  pip install pycaw        # control de volumen
  pip install pyautogui    # control del mouse y teclado
  pip install pygetwindow  # control de ventanas
  ```

### 4.4 Comandos de sistema a implementar

- [ ] **Gestión de procesos:**
  - [ ] Abrir aplicación por nombre ("abre el bloc de notas")
  - [ ] Cerrar aplicación ("cierra Chrome")
  - [ ] Listar procesos activos ("qué está corriendo")
  - [ ] Matar proceso por nombre

- [ ] **Control del sistema:**
  - [ ] Apagar el PC ("apaga el equipo en 5 minutos")
  - [ ] Reiniciar ("reinicia Windows")
  - [ ] Bloquear pantalla ("bloquea la pantalla")
  - [ ] Modo ahorro de energía

- [ ] **Control de audio:**
  - [ ] Subir/bajar volumen ("sube el volumen")
  - [ ] Silenciar/activar micrófono
  - [ ] Silenciar el sistema

- [ ] **Archivos y carpetas:**
  - [ ] Abrir carpeta ("abre mis documentos")
  - [ ] Crear archivo/carpeta ("crea una carpeta llamada proyectos")
  - [ ] Mover/copiar archivos
  - [ ] Buscar archivos por nombre

- [ ] **Información del sistema:**
  - [ ] CPU y RAM en uso ("cuánta RAM estoy usando")
  - [ ] Temperatura del sistema
  - [ ] Espacio en disco
  - [ ] Procesos que más consumen

---

## 🔲 FASE 5 — Control de Aplicaciones

> Karen interactúa con programas específicos.

### 5.1 Control del navegador

- [ ] Instalar:
  ```powershell
  pip install selenium
  ```
- [ ] Descargar ChromeDriver o EdgeDriver
- [ ] Implementar comandos:
  - [ ] "Abre YouTube y busca música relajante"
  - [ ] "Busca en Google el precio del dólar hoy"
  - [ ] "Abre una nueva pestaña"
  - [ ] "Cierra la pestaña actual"

### 5.2 Control del escritorio

- [ ] Implementar con pyautogui:
  - [ ] Mover el mouse a una posición
  - [ ] Hacer click en un elemento
  - [ ] Escribir texto en el campo activo
  - [ ] Tomar screenshot ("toma una captura de pantalla")
  - [ ] Scroll arriba/abajo

### 5.3 Integración con Spotify/reproductor de música

- [ ] Detectar si Spotify está abierto
- [ ] Controlar reproducción:
  - [ ] "Pausa la música"
  - [ ] "Siguiente canción"
  - [ ] "Reproduce algo de reggaeton"

### 5.4 Notificaciones de Windows

- [ ] Instalar:
  ```powershell
  pip install win10toast
  ```
- [ ] Karen puede enviar notificaciones al escritorio
- [ ] Útil para confirmaciones de acciones ("Archivo copiado correctamente")

---

## 🔲 FASE 6 — Memoria Persistente

> Actualmente Karen olvida todo al reiniciar. Esta fase le da memoria real.

### 6.1 Base de datos local con SQLite

- [ ] Crear base de datos en `C:\karen\memoria.db`
- [ ] Guardar cada conversación con timestamp
- [ ] Recuperar contexto relevante en cada nueva sesión
- [ ] Implementar en el servidor Flask

### 6.2 Memoria de preferencias

- [ ] Guardar preferencias del usuario:
  - [ ] Nombre ("Llámame Dayver")
  - [ ] Aplicaciones favoritas
  - [ ] Horarios habituales
- [ ] Karen personaliza respuestas basándose en el historial

### 6.3 Memoria de tareas pendientes

- [ ] Sistema de recordatorios:
  - [ ] "Karen, recuérdame tomar agua cada hora"
  - [ ] "Recuérdame el meeting a las 3pm"
- [ ] Implementar scheduler en segundo plano:
  ```powershell
  pip install schedule
  ```

---

## 🔲 FASE 7 — Interfaz Gráfica (Opcional)

> Una ventana flotante en el escritorio para interactuar con Karen.

### 7.1 Ventana minimalista con Tkinter

- [ ] Botón push-to-talk (mantener presionado para hablar)
- [ ] Indicador visual cuando está escuchando (barra de audio)
- [ ] Log de la conversación en pantalla
- [ ] Botón para silenciar/activar

### 7.2 Ícono en la bandeja del sistema

- [ ] Instalar:
  ```powershell
  pip install pystray
  pip install Pillow
  ```
- [ ] Karen como ícono en el system tray
- [ ] Click derecho → menú con opciones
- [ ] Doble click → abrir ventana principal

### 7.3 Overlay en pantalla (avanzado)

- [ ] Ventana transparente que muestra lo que Karen está haciendo
- [ ] Similar al HUD de Iron Man
- [ ] Muestra transcripción en tiempo real

---

## 🔲 BONUS — Hacer Karen Autónoma al Iniciar Windows

> Karen arranca sola con Windows, sin necesidad de abrir PowerShell.

### B.1 Script de inicio automático

- [ ] Crear `C:\karen\iniciar_karen.bat`:
  ```batch
  @echo off
  cd C:\karen
  python cliente.py
  ```
- [ ] Agregar al inicio de Windows:
  - Presionar `Win + R` → escribir `shell:startup`
  - Copiar el `.bat` en esa carpeta

### B.2 Servidor Flask como servicio

- [x] Configurado como `karen.service` vía systemd en la LXC — activo, habilitado y con auto-arranque
- [ ] (Opcional) Alternativa en Windows con NSSM si se migra el server al lado Windows

---

## 📐 Arquitectura Final Objetivo

```
Windows (inicio automático)
    │
    ├── cliente.py (en background)
    │       │
    │       ├── Escucha wake word "Karen" (openwakeword + karen.onnx)
    │       ├── Graba hasta silencio (filtro RMS + np.max sobre umbral)
    │       ├── Transcribe con Whisper (local)
    │       ├── Envía a Flask en LXC
    │       └── Recibe acción + texto
    │               │
    │               ├── Si texto → Edge-TTS habla
    │               └── Si acción → ejecutor.py actúa
    │
    └── ejecutor.py
            │
            ├── subprocess (comandos de sistema)
            ├── pyautogui (mouse/teclado)
            ├── psutil (procesos)
            ├── pycaw (audio)
            └── selenium (navegador)

LXC Proxmox
    │
    ├── server.py (Flask, servicio systemd: karen.service)
    │       │
    │       └── Ollama API :11434
    │               │
    │               └── llama3.2:3b
    │
    └── memoria.db (SQLite, historial persistente — Fase 6)
```

---

## 🔗 Referencias y Recursos

- [Ollama modelos disponibles](https://ollama.com/library)
- [openWakeWord](https://github.com/dscripka/openWakeWord)
- [pyautogui documentación](https://pyautogui.readthedocs.io)
- [edge-tts voces disponibles](https://github.com/rany2/edge-tts)
- [Whisper modelos](https://github.com/openai/whisper#available-models-and-languages)

---

*Actualizar este documento cada vez que se complete una fase. Marcar casillas con `- [x]` en Obsidian.*
