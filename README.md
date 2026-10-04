# 🌸 KAREN Assistant: The Genesis of Local AI

## 📜 Visión General
KAREN no fue solo un asistente; fue la primera piedra angular de mi ecosistema de IA local. Representó el salto desde la computación reactiva hacia la asistencia proactiva, implementando la primera capa de procesamiento de lenguaje natural (NLP) ejecutada íntegramente en hardware propio.

KAREN nació de la necesidad de interactuar con mi entorno digital de una manera orgánica, eliminando la fricción entre la intención humana y la ejecución del sistema.

## 🏗️ Arquitectura del Sistema
El sistema se basó en una arquitectura de tres capas:
1. **Capa de Interfaz (Frontend):** Un puente de comunicación simple pero efectivo para la entrada de comandos y salida de respuestas.
2. **Núcleo de Procesamiento (The Brain):** Implementación de un LLM ligero optimizado para tareas de clasificación de intención.
3. **Capa de Ejecución (Actuators):** Un conjunto de scripts de Python diseñados para interactuar con el Sistema Operativo y automatizar rutinas básicas.

## 🚀 Capacidades Implementadas
- **NLP Primario:** Capacidad de entender lenguaje natural y convertirlo en comandos ejecutables.
- **Automatización de Rutinas:** Ejecución de secuencias de comandos predefinidas para optimizar el flujo de trabajo diario.
- **Gestión de Contexto Inicial:** Implementación de una memoria a corto plazo para mantener el hilo de la conversación.

## 💎 El Legado de KAREN
KAREN fue la fase de experimentación pura. A través de ella, identifiqué las limitaciones de la "asistencia amable" y la necesidad de una "autoridad sistémica", lo que dio lugar al desarrollo de **ULTRON**. Sin la base de KAREN, la precisión operativa de **F.R.I.D.A.Y.** no sería posible.

## 🛠️ Stack Tecnológico
- **Lenguaje:** Python 3.x
- **Modelos:** Implementaciones tempranas de LLMs locales.
- **OS:** Linux / Windows (Híbrido).
- **Integraciones:** Scripts de shell y APIs de automatización básica.

## ⚙️ Configuración portable

El cliente ya no depende de una IP privada escrita en el código. Por defecto
busca el servidor en `http://127.0.0.1:5000`, pero puedes conectarlo a tu
servidor local o de tu red sin editar `cliente.py`.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
$env:KAREN_SERVER = "http://192.168.1.20:5000"
py cliente.py
```

También puedes pasar el servidor directamente:

```powershell
py cliente.py --server http://192.168.1.20:5000 --whisper-model base
```

Consulta `.env.example` para todas las variables disponibles. El archivo no
se carga automáticamente y no contiene secretos; sirve como plantilla para
tu entorno local.

## 🧪 Tests

Los tests no requieren micrófono, GPU, Whisper ni un servidor KAREN activo:

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest -q
```

La configuración por defecto es segura para una instalación nueva: apunta a
localhost y no expone ningún endpoint de red por sí sola.
