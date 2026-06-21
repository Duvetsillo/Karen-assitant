# 🔴 Karen — Registro de Errores y Soluciones
**Proyecto:** [KAREN_Bitacora](KAREN_Bitacora.md)
**Fecha:** 2026-06-07
**Estado:** ✅ Resueltos (sesión actual)

> Este documento complementa la [KAREN_Bitacora](KAREN_Bitacora.md). Aquí se registran únicamente los errores encontrados durante la instalación, su causa raíz y la solución aplicada, para no repetirlos en futuras sesiones.
>
> 📝 Nota: en el momento de esta sesión el proyecto todavía se llamaba "Jarvis", por eso las rutas y nombres de variables usan ese nombre.

---

## 🖥️ Errores en Windows (Cliente)

---

### ❌ Error 1 — `pip` y `python` no reconocidos

**Mensaje:**
```
pip : El término 'pip' no se reconoce como nombre de un cmdlet...
python : El término 'python' no se reconoce...
```

**Causa:**
Al instalar Python, no se marcó la casilla **"Add Python to PATH"** en el instalador. Windows no sabe dónde está Python.

**Solución:**
Reinstalar Python desde python.org y en la primera pantalla del instalador marcar:
```
☑ Add Python 3.11 to PATH
```
O en "Advanced Options" marcar:
```
☑ Add Python to environment variables
```
Luego cerrar y reabrir PowerShell.

**Prevención futura:**
Siempre verificar con `python --version` y `pip --version` antes de continuar.

---

### ❌ Error 2 — `ffmpeg` no encontrado

**Mensaje:**
```
FileNotFoundError: [WinError 2] El sistema no puede encontrar el archivo especificado
```

**Causa:**
Whisper necesita `ffmpeg` para procesar audio. Se instaló con `winget install ffmpeg` pero quedó en una ruta con caracteres especiales que Windows no reconoce en el PATH.

**Intentos fallidos:**
- `winget install ffmpeg` → instalado pero no en PATH
- Agregar ruta manualmente con `SetEnvironmentVariable` → ruta con caracteres especiales causaba error
- `pip install imageio[ffmpeg]` + `import imageio_ffmpeg` → el módulo no funcionó correctamente en este contexto

**Solución final:**
Descargar `ffmpeg.exe` manualmente y copiarlo directo a `C:\jarvis\`:
```powershell
cd C:\jarvis
Invoke-WebRequest -Uri "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -OutFile "ffmpeg.zip"
Expand-Archive -Path "ffmpeg.zip" -DestinationPath "C:\jarvis\ffmpeg_temp"
Copy-Item "C:\jarvis\ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" "C:\jarvis\"
Copy-Item "C:\jarvis\ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe" "C:\jarvis\"
Remove-Item -Recurse "C:\jarvis\ffmpeg_temp"
Remove-Item "C:\jarvis\ffmpeg.zip"
```

Y en el código Python agregar al inicio:
```python
os.environ["PATH"] = r"C:\jarvis" + os.pathsep + os.environ["PATH"]
```

**Prevención futura:**
Siempre copiar `ffmpeg.exe` directo a `C:\jarvis\` al montar el cliente. No depender del PATH del sistema.

---

### ❌ Error 3 — `SyntaxError: expected 'except' or 'finally' block`

**Mensaje:**
```
SyntaxError: expected 'except' or 'finally' block
File "C:\jarvis\cliente.py", line 69
```

**Causa:**
Al copiar y pegar código Python en el Bloc de notas (Notepad), la indentación se rompe. Notepad no respeta los espacios/tabs del código, lo que genera errores de sintaxis en Python que es muy estricto con la indentación.

**Solución:**
Nunca usar Notepad para crear archivos Python. En su lugar, escribir el archivo directamente desde PowerShell con `Out-File`:
```powershell
@'
# código aquí
'@ | Out-File -FilePath "C:\jarvis\cliente.py" -Encoding utf8
```

**Prevención futura:**
Usar VS Code, Notepad++, o el método `Out-File` de PowerShell para crear scripts Python.

---

### ❌ Error 4 — `Connection aborted. RemoteDisconnected`

**Mensaje:**
```
Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Causa:**
El servidor Flask en el LXC se había caído o nunca se levantó. El cliente en Windows intentó conectarse pero no había nadie escuchando en el puerto 5000.

**Solución:**
Levantar el servidor en el LXC:
```bash
source ~/jarvis-server/bin/activate
python ~/jarvis/server.py
```

**Prevención futura:**
Antes de correr el cliente, siempre verificar que el servidor responde:
```powershell
curl http://192.168.100.66:5000/salud
# Debe devolver: {"estado": "ok"}
```

---

## 🐧 Errores en el LXC (Servidor)

---

### ❌ Error 5 — Ollama no accesible desde la red

**Síntoma:**
- Open WebUI mostraba "Ollama: Server disconnected"
- Desde el navegador en Windows `http://192.168.100.66:11434` daba error de conexión
- El cliente Python recibía `Connection aborted`

**Causa:**
Por defecto Ollama solo escucha en `127.0.0.1` (localhost). Cualquier petición desde otra máquina es rechazada.

**Solución:**
```bash
systemctl edit ollama
```

Agregar entre los comentarios indicados:
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
# Ollama is running
```

**Prevención futura:**
Esta configuración persiste entre reinicios. Solo hay que hacerla una vez. Si se reinstala Ollama, repetir este paso.

---

### ❌ Error 6 — `Address already in use: Port 5000`

**Mensaje:**
```
Address already in use. Port 5000 is in use by another program.
```

**Causa:**
Se intentó levantar el servidor Flask cuando ya estaba corriendo en segundo plano de una sesión anterior.

**Solución:**
No es necesario levantarlo de nuevo. Si se quiere reiniciar limpio:
```bash
pkill -f "python.*server.py"
source ~/jarvis-server/bin/activate
python ~/jarvis/server.py
```

**Prevención futura:**
Siempre verificar si el servidor ya está activo antes de intentar levantarlo:
```bash
curl http://localhost:5000/salud
```

---

### ❌ Error 7 — qwen2.5:7b no da respuestas útiles

**Síntoma:**
El modelo qwen2.5:7b no respondía correctamente o daba respuestas vacías/erróneas a través del servidor Flask.

**Causa probable:**
Con un i5 3ra gen y 12GB de RAM, el modelo de 4.7GB consume casi toda la memoria disponible. Las respuestas pueden fallar por timeout o por memoria insuficiente para el contexto.

**Solución temporal:**
Cambiar a `gemma3:1b` en `~/jarvis/server.py`:
```python
MODEL = "gemma3:1b"
```

**Solución definitiva pendiente:**
Probar `llama3.2:3b` que ofrece mejor calidad que gemma 1b con menor consumo que qwen 7b:
```bash
ollama pull llama3.2:3b
```
Y cambiar en server.py:
```python
MODEL = "llama3.2:3b"
```

---

## 📋 Pendientes Sin Resolver

| # | Problema | Estado | Próximo paso |
|---|---|---|---|
| 1 | qwen2.5:7b no funciona bien | ⏳ Pendiente | Probar con `ollama run qwen2.5:7b "hola"` para diagnosticar |
| 2 | Servidor Flask no arranca automáticamente | ⏳ Pendiente | Configurar como servicio systemd |
| 3 | Jarvis requiere presionar ENTER para escuchar | ⏳ Pendiente | Implementar activación por palabra clave |

---

## 💡 Lecciones Aprendidas

- **Python en Windows:** Siempre marcar "Add to PATH" al instalar. Verificar con `python --version` antes de continuar.
- **ffmpeg en Windows:** La forma más confiable es copiar el `.exe` directo al directorio del proyecto y agregarlo al PATH desde el código Python.
- **Archivos Python:** Nunca usar Notepad. Usar `Out-File` desde PowerShell o un editor como VS Code.
- **Ollama en red local:** Siempre configurar `OLLAMA_HOST=0.0.0.0:11434` desde el inicio si se va a usar desde otra máquina.
- **Modelos y RAM:** Con 12GB de RAM, el límite práctico es un modelo de ~4-5GB. Dejar margen para el sistema operativo y Flask.
