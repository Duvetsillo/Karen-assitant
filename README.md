# 🌸 KAREN Assistant: The Genesis of Local AI

## Código actual de Karen

**La interfaz principal es Desktop Pet.** Iníciala con `start_pet.ps1` cuando
su código, dependencias y base compartida estén preparados. La
[guía de memoria personal del Pet](docs/PET_PERSONAL_MEMORY.md) explica cómo
incorporar información sin abrir el cliente verde y qué sigue pendiente.

La evolución Windows validada está en [`runtime/`](runtime/), integrada el 24 de
noviembre de 2026 desde la instalación de trabajo `C:\karen`. Incluye identidad
persistente, memoria SQLite, documentos revisados, conversación en streaming,
cancelación y perfiles de recursos. El cliente histórico de esta carpeta raíz
se conserva para documentar el origen del proyecto.

Consulta la [guía operativa](runtime/docs/PERSONAL_AI_UPGRADE.md) y el
[estado de esta integración](KAREN_PROGRESS.md). Full-duplex, AEC y STT
incremental siguen pendientes; esta publicación no los presenta como terminados.

Para ejecutar el código actual, con sus dependencias y modelos locales preparados:

```powershell
cd runtime
.\start_karen.ps1
```

Los modelos, referencias de voz, credenciales y datos personales permanecen en
la instalación local. La guía explica los requisitos de `desktop-pet/python` y
los entornos de voz; el repositorio contiene el código, no esos datos.

La CI portable de la raíz comprueba el cliente histórico en `tests/`. La suite
Windows del runtime se ejecuta desde `runtime/` con
`python -m unittest discover -s qa -p 'test_*.py'` y sus dependencias preparadas.

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
