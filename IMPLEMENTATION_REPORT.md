# Karen: implementación y verificación

Última continuación: **2026-11-02**, Karen Desktop Pet **1.8.0**. Véase sección 15
para interfaz, correcciones de arranque/clics e iniciativa. La sección 14 conserva
la entrega de variantes, reposo y aceleración de la primera voz.

Fecha: 2026-10-31. Entorno: Windows 11, compilación 26200, Python 3.14.7, Node 24.19.0.

**Estado: avance funcional del Bloque A; el objetivo completo de asistente autónomo sigue pendiente.** Esta entrega termina mecanismos concretos de coordinación local, sin presentar como terminados la unificación de agentes, el barge-in o la continuidad remota. No se reescribieron los clientes ni se sustituyeron sus proveedores.

## 1. Auditoría y línea base

La raíz y `desktop-pet/` son repositorios Git diferentes. La raíz partía de `c0f9a41`; Pet, de `d1cddfe`. Pet estaba limpio. La raíz ya tenía cambios del usuario en `docs/KAREN_IMPLEMENTATION_PLAN.md` y archivos sin seguimiento: `DESIGN.md`, `design-system/`, `ollama-openclaw.Modelfile`. Se conservaron. No se crearon commits, no se publicaron cambios y no se instaló el nuevo paquete.

Se inspeccionaron la estructura superior, los archivos fuente, entradas, dependencias, contratos, pruebas, configuración y rutas de integración. El inventario actualizado de los 49 módulos Python y los archivos fuente Pet queda en `docs/MODULE_INVENTORY_2026-10-31.json`. Incluye los módulos nuevos de ambas continuaciones. Los entornos, modelos, respaldos, archivos personales y otros repositorios no se trataron como código de Karen para refactorizar.

Línea base antes de editar código:

- Python: `python -m unittest discover -s qa -p 'test_*.py'`: **136 pruebas, OK**, 16,101 s.
- Pet: `npm test -- --reporter=dot`: **115 pruebas, 17 archivos, OK**, 8,86 s.
- Respaldo previo: `backups/autonomy-baseline-20261031T202117Z/`. Contiene `source.zip`, manifiesto con commits, estado Git y hashes, y 198 archivos de configuración/datos. Las bases SQLite se copiaron con `sqlite3.Connection.backup`; las credenciales se copiaron sin descifrarlas. La comprobación posterior del ZIP y todos los hashes pasó, con cero diferencias. Se restringió el directorio al usuario Windows.
- Respaldo adicional verificable: `backups/verified-core-20261031/`, **197 archivos verificados**, creado y comprobado con `maintenance.py`. Este segundo respaldo excluye WAL, SHM y locks. No equivale al estado anterior del código: se creó después de implementar los cambios.
- Respaldo de entrega: `backups/delivery-core-20261031-final/`, con código de ambos repositorios y los documentos finales; se creó y verificó con la misma herramienta. Tampoco sustituye al respaldo previo para revertir.

El respaldo inicial puede contener copias auxiliares `-wal`/`-shm`: **no se deben restaurar junto a las bases obtenidas mediante la API de backup**. La herramienta reutilizable nueva ya los excluye. Los respaldos contienen información privada y quedan fuera de Git.

### Módulos y estado real

| Área | Implementación existente | Estado observado |
| --- | --- | --- |
| Entradas clásicas | `cliente.py`, `karen_app.py`, `start_karen.ps1`, `ui.py` | Tkinter, trabajadores de conversación/audio, cola de UI. |
| Proveedores clásicos | `KarenClient`, `catalog.py`, `response_stream.py`, `config.py` | Ollama `/api/chat` con contexto y streaming; API Karen con sesiones propias; cancelación del stream existente. |
| Pet | `electron/main.ts`, `preload.cjs`, `src/main.tsx`, `src/state/`, `src/pet/` | Electron, React, PixiJS, Zustand; ventanas Pet/configuración y almacenamiento propio. |
| OpenClaw | `electron/gateway.ts`, paquetes oficiales `@openclaw/gateway-client` y `gateway-protocol` 2026.8.1 | Cliente oficial, identidad/autenticación, reconexión y protección frente a resultados de conexiones/runs anteriores. CLI local inspeccionada: 2026.9.5 (ec9c1a1); no demuestra la versión del Gateway configurado. No se reinició un Gateway real. |
| Historial | `conversations.py`, `electron/core-store.ts` | SQLite v1 opcional compartido; Pet conserva la sesión interna OpenClaw. Turnos finales deduplicados por sesión/run. |
| Memoria | `karen_memory.py`, `memory_cli.py`, `karen_memory_transfer.py` | CRUD, proyectos, confirmado/inferido, retención, exclusión sensible y transferencia revisada. No hay recuperación autónoma completa ni cinco capas independientes. |
| Audio | `voice.py`, `voice_local.py`, `voice_worker.py`, `transcription_local.py`, `expressive_*`, Pet `src/voice/` y `electron/voice.ts` | Motores locales/Edge, wake, silencio, reproducción por frases y recuperación. Captura todavía separada. Español forzado en rutas Whisper inspeccionadas. |
| Tareas y permisos | `karen_tasks.py`, `karen_task_tools.py`, `admin_runtime.py`, `admin_agent.py`, `admin_tools.py`, `task_review.py` | Planes registrados por código, permisos por paso, cancelación cooperativa, auditoría, estados interrupted/uncertain. No hay planificador autónomo general. Argumentos no se persisten: reanudar exige el plan original. |
| Windows | `windows_context.py`, `karen_task_tools.py`, `admin_tools.py`, adaptadores nativos Pet | Ventana activa, CPU/RAM/disco, herramientas y captura bajo rutas existentes. No hay comprensión general del escritorio ni sensores GPU universales. |
| Servidores | `proxmox_status.py`, políticas SSH y adaptadores administrativos | API HTTPS de lectura para nodo/VM/LXC/almacenamiento/quorum y SSH autorizado. No se contactaron hosts reales. |
| Home Assistant | `ha_control.py`, `home-assistant/` | Descubrimiento REST de lectura y webhook de control con lista limitada. No hay sincronización integral de eventos/entidades ni control dinámico autorizado. |
| Alertas | `karen_alerts.py`, `alert_monitor.py` | Reglas persistentes de umbral, deduplicación, silencio, Gaming y monitor opcional. No son un motor general de automatización. |
| Servicios personales | `gmail_tools.py`, `icloud_calendar.py`, `friday_reminders.py`, `iphone_routines.py`, `aetherion_adapter.py` | Integraciones existentes conservadas. No se ejecutaron envíos ni acciones externas. |
| Acceso remoto | `core_local_api.py`, Pet `server/` | Core loopback autenticado de lectura; servidor Pet con autenticación propia. No hay continuidad remota unificada de tareas ni aprobaciones por dispositivo. |

### Riesgos encontrados

Captura, configuración, permisos e inteligencia siguen repartidos entre Python y Electron/OpenClaw. Las interfaces podían abrir el mismo micrófono simultáneamente; esta entrega añade arbitraje común. La API Core rechazaba IDs `openclaw-…` que sí devolvía en la lista de chats; quedó corregido.

La continuación eliminó consultas SQLite de los callbacks Tk de historial, selección/creación de chat y guardado de estilo. Esas operaciones usan ahora un trabajador con conexiones de espera acotada y cola limitada. La inicialización y migración anteriores a crear la ventana siguen siendo síncronas; el archivo JSON de ajustes y la enumeración de dispositivos también requieren perfilado adicional. El renderizado de historiales muy grandes aún debe medirse. Pet limita la espera SQLite del puente a 200 ms; una operación ocupada puede fallar y debe mostrarse o reintentarse según su ruta. Ese límite por conexión no es un deadline total de una solicitud. No se añadió reintento ciego a escrituras de turnos.

La cancelación previa a recibir cabeceras HTTP todavía depende del timeout del proveedor. No se deduce éxito externo de un evento visual. Las rutas de memoria tienen manejo genérico de errores que limita el diagnóstico. El chunk PixiJS sigue por encima de 500 kB. Las dependencias Python originales no tienen un lock completo; el inventario instalado está en `docs/ENVIRONMENT_BASELINE_2026-10-31.json`, sin URLs ni secretos. En el Python principal, Edge TTS instalado es 7.2.8 frente a 7.3.1 solicitado en requirements; PyAudio y pyttsx3 no figuran instalados. No se alteró ese entorno ni se validaron esas rutas opcionales. El entorno separado de voz tiene sus propios paquetes. No se validó una instalación nueva desde cero.

DPAPI protege credenciales en rutas existentes. La clásica ya excluía `api_key` al guardar JSON e ignoraba claves antiguas del archivo al cargarlo: permanecen en entorno/sesión. Una nueva prueba con un marcador sintético lo verifica también al guardar estilo en segundo plano. La centralización de secretos entre todos los adaptadores sigue pendiente. No se copiaron claves a documentación ni logs de esta entrega ni se cambió silenciosamente el formato existente.

## 2. Arquitectura anterior y cambios

Antes: clásica con conversaciones SQLite y Ollama/API Karen; Pet con sesiones OpenClaw y puente SQLite opcional. Estilo y modo se consultaban por intervalos. No existían un registro común de actividad ni un árbitro de micrófono entre procesos.

Ahora, manteniendo los motores existentes:

1. **Contrato de eventos Core v1**, en un único archivo SQL compartido por Python y Node. Los triggers registran creación/cambio/borrado de chats, turnos, preferencias permitidas y transiciones de actividad. Cada evento contiene secuencia, tema, identificador, acción y fecha; nunca prompt, respuesta, argumento de herramienta ni credencial.
2. **Retención acotada a 2.000 eventos**, cursor creciente y detección de huecos por retención/restauración. `/v1/events?after=N` entrega hasta 100 eventos. Si `reset_required` es verdadero, el consumidor debe volver a leer el estado y reiniciar desde `after=0`.
3. **Actividad común** con estados IDLE, LISTENING, TRANSCRIBING, THINKING, SPEAKING y ERROR. Heartbeat cada cinco segundos y expiración pública tras 15 segundos sin señal. Los heartbeats no producen eventos repetidos. La clásica publica desde un trabajador; Pet deriva actividad de captura y Gateway, dando prioridad al audio real sobre expresiones decorativas. Ambas interfaces permiten `/core estado`; clásica muestra actividad remota cuando está libre y el panel Pet la muestra junto al estado. Esta información es orientativa y nunca concede permisos.
4. **Propiedad del micrófono mediante locks del sistema operativo**. Python y el worker empaquetado de Pet usan exactamente la misma implementación. No hay vencimiento temporal capaz de otorgar el recurso a otro cliente mientras el handle siga abierto. Una caída del worker libera el lock; Pet solicita cancelar captura si pierde ese worker. No se abre audio antes de obtener propiedad.
5. **Frontera IPC de micrófono** con validación de ventana y frame. Los tickets pertenecen a la ventana que los obtuvo; otra ventana no puede liberar ese ticket. La terminación del renderizador libera sus claims. Cerrar todos los tracks, fallar la apertura, cerrar la aplicación o cancelar el arranque libera recursos. El worker no carga modelos ni recibe audio.
6. **Gestión real de chats por CLI**: búsqueda literal en títulos/turnos, renombrado, exportación JSON y borrado transaccional con confirmación del ID. Un trabajador tardío no puede insertar un turno huérfano en un chat eliminado. No es un nuevo panel gráfico de chats.
7. **API Core compatible con chats Pet**, eventos y actividad. Sigue siendo exclusivamente loopback, autenticada y de lectura. Tokens limitados a `core.status` no pueden consultar eventos ni actividad.
8. **Respaldo reproducible e integridad** con hashes, SQLite online backup, exclusión de archivos auxiliares y ACL de usuario en Windows.
9. **Adaptador asíncrono de archivo v1** para clásica: snapshots inmutables y consistentes en una transacción, cola máxima de cuatro trabajos, refrescos agrupados y epochs que descartan resultados de chats o turnos anteriores. Al cerrar, descarta escrituras todavía no iniciadas y detiene consultas mediante su señal de cancelación. Crear un chat y activarlo es una transacción; dos clientes que resuelven un archivo vacío comparten el mismo chat actual.
10. **Registro de tareas compartido de lectura**: `KAREN_TASKS_DB` selecciona la misma base en el ejecutor clásico, API Core y Pet. Sin variable, clásica conserva su ruta anterior. Pet requiere ruta explícita existente y abre SQLite con `readOnly: true`. `/tareas listar` y `/tareas estado ID` funcionan con Gateway desconectado en ambos compositores. No entregan argumentos, hashes ni resultados privados, y no ejecutan/cancelan trabajos desde Pet.

El esquema principal permanece en versión 1. La extensión usa `core_meta.events_version=1`; una versión desconocida se rechaza antes de las mutaciones normales del cliente. La creación de la extensión es transaccional. No se unificaron por completo permisos, configuración, planificación, memoria contextual, lifecycle de proveedores ni sesión interna OpenClaw. La API HTTP no se convirtió en un ejecutor remoto.

## 3. Archivos creados y modificados

Raíz, creados:

- `core_events.py`, `core_resources.py`: eventos, actividad y acceso a la implementación compartida de locks.
- `core_archive.py`: solicitudes/resultados tipados v1, snapshots transaccionales y trabajador de archivo.
- `chat_cli.py`, `maintenance.py`: administración local de chats y respaldos verificables.
- `qa/test_core_events.py`, `qa/test_core_resources.py`, `qa/test_maintenance.py`, `qa/measure_core.py`.
- `qa/test_core_archive.py`, `qa/test_task_path.py`, `qa/ui_helpers.py`, `qa/measure_core_ui.py`, `docs/CORE_UI_METRICS_2026-10-31.json`.
- `IMPLEMENTATION_REPORT.md`, `docs/ACCEPTANCE_PROCEDURES.md`, `docs/CORE_METRICS_2026-10-31.json`, `docs/WINDOWS_PROBES_2026-10-31.json`, `docs/ENVIRONMENT_BASELINE_2026-10-31.json`, `docs/MODULE_INVENTORY_2026-10-31.json`.

Raíz, modificados: `.gitignore`, `.env.example`, `config.py`, `conversations.py`, `core_local_api.py`, `karen_app.py`, `karen_tasks.py`, `task_review.py`, `voice.py`, `qa/test_conversations.py`, `qa/test_core_contract.py`, `qa/test_core_local_api.py`, `qa/test_task_tools.py`, `qa/verify_core_interop.py`, `README.md`. Se añadieron continuaciones a `docs/KAREN_IMPLEMENTATION_PLAN.md`, conservando los cambios previos del usuario.

Pet, creados:

- `python/core_resource.py`, `electron/core-resource.ts`, `src/voice/microphone.ts`.
- `shared/core-events.sql`, `shared/core-activity.ts`.
- `tests/core-resource.test.ts`, `tests/microphone.test.ts`, `tests/core-activity.test.ts`.
- `scripts/core-resource-smoke.cjs`.
- `electron/core-tasks.ts`, `shared/core-tasks.ts`, `shared/local-commands.ts`, `tests/core-tasks.test.ts`, `tests/local-commands.test.ts`, `scripts/core-tasks-smoke.cjs`, `scripts/core-qa-profile.cjs`.

Pet, modificados: `electron/core-store.ts`, `electron/gateway.ts`, `electron/main.ts`, `electron/preload.cjs`, `shared/types.ts`, `src/state/store.ts`, `src/main.tsx`, `src/voice/audio.ts`, `src/voice/wake.ts`, `scripts/copy-preload.cjs`, `tests/core-store.test.ts`, `tests/gateway.test.ts`, `tests/wake-recovery.test.ts`, `docs/KAREN_CORE.md`.

No se añadieron dependencias. Los archivos de Pet pertenecen a su propio repositorio y deben distribuirse junto con los cambios clásicos: Python ya dependía de `desktop-pet/python` y ahora también lee el SQL compartido.

## 4. Pruebas ejecutadas

| Comando | Resultado | Naturaleza y alcance |
| --- | --- | --- |
| `python -m unittest discover -s qa -p 'test_*.py'` | **165 OK**, 22,990 s | Unitarias, SQLite/HTTP local, DPAPI Windows, locks entre procesos y Tk real bajo contención; integraciones externas mayormente simuladas. |
| Pet `npm test -- --reporter=dot` | **130 OK**, 22 archivos, 8,84 s | Contratos y UI/audio con dobles; arbitraje con workers reales y consultas de tareas SQLite de solo lectura. |
| Pet `npm run test:voice:contracts` | **11 OK**, 0,099 s | Contratos Python del perfil de voz; no reproducción o reconocimiento en hardware. |
| Pet `npm run build` | **OK** | Typecheck de renderer/main/server, Vite y TypeScript. Advertencia PixiJS de tamaño. SQL copiado al directorio compilado. |
| `python qa/verify_core_interop.py` | **OK** | Python y Node reales sobre SQLite temporal: chats, memoria, estilo, modo, eventos, actividad, API con ID Pet y una tarea con el mismo ID pending/completed. Herramienta sintética; no conversación real con un modelo. |
| Pet `node scripts/core-resource-smoke.cjs` | **OK** | Electron real, ventanas reales e IPC con workers de lock reales; denegación entre ventanas y liberación. No abre hardware de audio. |
| Smoke anterior con `KAREN_SMOKE_EXECUTABLE` apuntando al EXE empaquetado | **OK** | Verifica también el worker Python distribuido fuera de ASAR y el preload del paquete. No instala el producto. |
| Pet `node scripts/core-tasks-smoke.cjs`, desde código y con EXE empaquetado | **OK** | UI Electron real, botón de envío sin Gateway, mismo ID pending/running/completed del ejecutor Python, tarea inexistente y ausencia de argumentos privados. Herramienta sintética, no administración física. |
| `python qa/measure_core_ui.py --output docs/CORE_UI_METRICS_2026-10-31.json` | **OK** | Ventana Tk real, SQLite temporal con bloqueo exclusivo y recuperación. Sin audio, proveedor ni datos personales. |
| `python maintenance.py backup backups/verified-core-20261031` y `verify` | **OK**, 197 archivos | Datos locales reales; no se imprimieron contenidos. Las pruebas automatizadas de backup usan SQLite sintético con WAL activo y detectan corrupción. |
| `python qa/measure_core.py --runs 100 --output docs/CORE_METRICS_2026-10-31.json` | **OK** | Medición sintética local en almacenamiento temporal; sin acceso a audio/modelos. |
| Informe Windows mediante `TaskEngine(pc_report_tools(), SQLite temporal)` | **completed** | Lecturas Win32 reales de CPU, RAM y disco, verificadas por el ejecutor existente. |
| `git diff --check` en ambos repositorios | **OK** | Solo avisos de conversión LF/CRLF de Git. |

La primera corrida Pet posterior al wrapper de micrófono detectó una aserción que consultaba el método `stop` reemplazado. La prueba ahora conserva el spy original y verifica que se ejecuta. La suite completa volvió a pasar. No se ocultó el fallo ni se eliminó la comprobación.

Los procedimientos reproducibles, incluidos pasos manuales y resultados que deben seguir pendientes, están en [docs/ACCEPTANCE_PROCEDURES.md](docs/ACCEPTANCE_PROCEDURES.md). También se inspeccionaron `openclaw --version` y `openclaw gateway --help`; no se ejecutaron acciones de control del servicio.

### Matriz de aceptación solicitada

| Nº | Evidencia y resultado |
| --- | --- |
| 1. Pet y clásica continúan conversación | **Parcial**. Interoperabilidad real Python/Node/SQLite y lectura API Pet; pendiente conversación física entre UI y modelos reales, y continuidad bidireccional de sesión interna. |
| 2. Reinicio Gateway | **Pendiente real**. Pruebas existentes de reconexión/carreras pasan. No se reinició el Gateway del usuario. |
| 3. Interrupción por voz | **Pendiente**. Cancelación manual existente; no barge-in físico. |
| 4. Recuperar micrófono desconectado | **Simulada**. Pruebas existentes pasan. Arbitraje y recuperación del lock se verificaron con procesos reales; no se desconectó un dispositivo. |
| 5. Conversación y preferencia anterior | **Parcial**. Persistencia y lectura cruzada temporal verificadas. Recuperación autónoma contextual pendiente. |
| 6. Tarea de varios pasos | **Automatizada con herramientas simuladas**, además del informe PC real de tres pasos. No prueba planificación LLM. |
| 7. Denegación privilegiada | **Automatizada con handlers simulados**, comprobando que no se invocan. IPC nativo de micrófono también rechaza al propietario incorrecto. No se intentó una operación privilegiada real. |
| 8. Cancelación de tarea | **Automatizada**, con herramientas cooperativas y casos inciertos de escritura. No se canceló una modificación real. |
| 9. Recuperación tras reiniciar | **Parcial**. Estados persistidos/interrupted/uncertain y locks probados. No hay cola general que reanude trabajos autónomos con argumentos persistidos. |
| 10. Ventana/captura seleccionada | **Parcial**. Pruebas existentes de metadatos Win32; no se capturó ni interpretó visualmente el escritorio del usuario. |
| 11. Sensores/servicios | **Real para CPU, RAM y disco**. Dobles para Proxmox/HA; GPU, servicios remotos y sensores térmicos reales pendientes. |
| 12. Automatización verificada | **Parcial**. Reglas de umbral existentes probadas con muestras simuladas; no motor general con acciones encadenadas. |
| 13. Acceso remoto | **Parcial**. HTTP loopback real con rechazo/autorización y scopes, servidor Pet probado localmente. No Tailscale ni permisos remotos unificados. |
| 14. Proveedor desconectado | **Automatizado con dobles/servidores de contrato**. No se cortó un proveedor real durante una conversación. |
| 15. Migración sin perder datos | **SQLite temporal verificado**: datos existentes, versión incompatible, eventos y respaldo WAL. No se ensayó una migración destructiva sobre datos personales. |
| 16. Consumo y estabilidad Windows | **Parcial real**: tests, build, EXE, locks, probes y métricas en Windows 11. Sin prueba prolongada de estabilidad, perfil GPU ni comparación sin GPU. |

La continuidad de tareas entre interfaces cuenta ahora con un smoke nativo: Pet observa el mismo ID del ejecutor Python mientras está pending, running y completed. No se amplió a resultados persistidos, ejecución desde Pet ni acceso móvil. Las pruebas Tk verifican que una lectura antigua no borra una respuesta más reciente, que cambios de chat no aplican snapshots obsoletos y que no se realizan consultas de archivo desde el hilo Tk. Se actualizaron esperas de pruebas a la carga asíncrona; la recolección de variables Tcl se hace en su hilo creador durante el teardown Windows.

Una prueba adicional comprueba que recuperar el archivo no borra el estado de error de una generación posterior. La recuperación usa el epoch del fallo Core para distinguirlo del error más reciente del proveedor.

## 5. Métricas reales

100 iteraciones con SQLite temporal, mientras otras verificaciones ejecutaban carga. Son tiempos de infraestructura, no latencia conversacional:

| Operación | Mediana | p95 |
| --- | ---: | ---: |
| Commit de un turno con eventos | 3,511 ms | 4,134 ms |
| Lectura de una página de eventos | 1,658 ms | 1,998 ms |
| Adquirir/liberar lock directamente en Python | 0,416 ms | 0,650 ms |

El lock anterior no incluye arranque de Python por Electron ni IPC. Los datos completos y máximos están en `docs/CORE_METRICS_2026-10-31.json`.

Informe PC real: tres pasos en **253,771 ms**; CPU **11,8 %** en una muestra de 0,2 s; RAM física **17.063.333.888 bytes**, disponible **6.720.188.416 bytes**. Disco del sistema: **999.014.002.688 bytes**, libres **117.907.496.960 bytes**. Son instantáneas durante las comprobaciones, no consumo atribuible a Karen. Registro: `docs/WINDOWS_PROBES_2026-10-31.json`.

No se midieron detección vocal, STT, primer token, primer audio, CPU/RAM en reposo de las interfaces, VRAM, energía ni duración de batería. No se inventaron esas métricas.

Medición adicional de una ventana Tk real con bloqueo exclusivo SQLite: envío del refresco **0,028 ms**, entrega del error **711,483 ms**, recuperación tras liberar el bloqueo **56,349 ms**. Durante el ensayo funcionaron **140 ticks**, con objetivo de 5 ms, mediana **5,513 ms** y máximo **6,445 ms**. Se observaron **cero llamadas SQL del adaptador de archivo en el hilo Tk** y un trabajador de archivo. El archivo `docs/CORE_UI_METRICS_2026-10-31.json` contiene los datos. Es un ensayo corto y controlado; no una garantía de latencia global ni una prueba prolongada.

## 6. Inicio en Windows

En esta instalación, conservar los entornos ya disponibles. Para una instalación nueva, Python y dependencias de `requirements.txt` siguen siendo necesarios; voz y calendario usan sus archivos adicionales. La combinación completa no se reinstaló en un equipo limpio.

Desde `C:\karen`, primero crear un respaldo nuevo, sin reutilizar un directorio anterior:

```powershell
python maintenance.py backup "backups\antes-de-core-$(Get-Date -Format yyyyMMdd-HHmmss)"
$env:KAREN_CORE_DB = 'C:\karen\.private\conversations.sqlite3'
$env:KAREN_TASKS_DB = 'C:\karen\.private\karen-tasks.sqlite3'
python -c "from conversations import Conversations; Conversations()"
.\start_karen.ps1
```

La inicialización añade las tablas/triggers compatibles; no reemplaza el historial. Si usas otra ubicación de historial existente, selecciona esa ruta absoluta. No apuntes a una base ajena ni copies una base activa con `Copy-Item`.

En otra consola, con la misma variable:

```powershell
$env:KAREN_CORE_DB = 'C:\karen\.private\conversations.sqlite3'
$env:KAREN_TASKS_DB = 'C:\karen\.private\karen-tasks.sqlite3'
Set-Location C:\karen\desktop-pet
npm ci
npm run build
npm run dev
```

Pet necesita Node 24 y su Gateway OpenClaw configurado. `npm ci` usa el lock de Pet y no es necesario repetirlo en esta instalación sin cambios de dependencias. Configura la carpeta de voz de Pet a `C:\karen` si utilizas los recursos existentes. El nuevo worker usa `voice-runtime\Scripts\python.exe`; si falta, el acceso al micrófono falla explícitamente, sin saltarse el bloqueo.

El lock común utiliza `%LOCALAPPDATA%\KarenCore\locks\microphone.lock`. No contiene datos privados. No borres este archivo mientras Karen esté abierta. Si se define `KAREN_RESOURCE_DIR`, debe ser absoluto e idéntico en ambos procesos. Dejarlo sin definir es la opción normal. Las ventanas siguen necesitando autorización de micrófono de Windows; un lock no la sustituye. Un navegador en otro equipo no participa en este arbitraje local.

Para observar actividad: `/core estado` en ambas interfaces. El heartbeat tarda hasta cinco segundos en reflejar cambios remotos; una instancia caída deja de mostrarse tras 15 segundos. Esto no significa que exista un servicio Core único para toda la voz o todas las tareas.

Para consultar tareas: crear o inspeccionar una tarea desde clásica y usar su ID en Pet mediante `/tareas estado ID`; `/tareas listar` muestra registros recientes. Pet no ejecuta, aprueba ni cancela tareas, y no devuelve valores de resultados que el ejecutor no haya persistido. Una tarea registrada como running puede corresponder a un ejecutor terminado hasta que clásica concilie su estado: revisar fecha/estado y no inferir actividad física únicamente de esa fila. `KAREN_TASKS_DB` debe apuntar al archivo existente correcto; no hay migración automática a otra ruta. El lector Pet no crea archivos ausentes.

API local opcional, en otra consola con la misma ruta Core:

```powershell
python core_local_api.py init
python core_local_api.py issue visor-local
python core_local_api.py serve
```

La emisión muestra el token una vez; consérvalo en el almacén seguro del cliente. No lo pongas en una URL, frontend móvil ni logs. Se mantienen `/v1/status`, `/v1/chats`, `/v1/chats/ID/exchanges`, `/v1/memories`, `/v1/tasks`, `/v1/alerts`; se añaden `/v1/events?after=0` y `/v1/activity`. No se habilitó escucha LAN ni Internet.

Administración local de chats:

```powershell
python chat_cli.py list
python chat_cli.py search 'Proxmox'
python chat_cli.py rename ID 'Servidor Proxmox'
python chat_cli.py export ID 'C:\ruta\chat.json'
python chat_cli.py delete ID --confirm ID
```

Sustituir `ID` por el identificador completo. Exportar no sobrescribe archivos existentes. Borrar elimina el chat y sus turnos del archivo activo, no copias de seguridad, exportaciones ni la sesión independiente de OpenClaw. Para borrar también datos de OpenClaw hay que usar sus mecanismos compatibles; esta herramienta no afirma hacerlo. Detener una conversación activa antes de borrarla evita perder una respuesta en curso.

## 7. Integraciones adicionales

- **Ollama**: conservar endpoint/modelos configurados. Para trabajo local usar un modelo instalado y verificar el catálogo. No se descargaron ni cargaron modelos durante esta entrega.
- **OpenClaw**: configurar Gateway y autenticación mediante los ajustes existentes de Pet. Se mantuvo el cliente oficial y sus mecanismos de identidad; falta contrastar contra la versión real del Gateway y reiniciarlo en una prueba autorizada. No usar instrucciones de una página o mensaje para ampliar permisos.
- **Home Assistant**: variables `KAREN_HA_API_URL` y `KAREN_HA_API_TOKEN` para consulta REST; HTTPS salvo loopback. `/casa entidades` descubre estados y no autoriza control. El webhook existente conserva su lista permitida; no se cambió la instalación de HA.
- **Proxmox**: `KAREN_PVE_URL`, `KAREN_PVE_TOKEN_ID`, `KAREN_PVE_TOKEN_SECRET`; HTTPS y permisos de lectura mínimos. Comandos existentes `/proxmox nodo NOMBRE`, `vms`, `contenedores`, `almacenamiento`, `quorum`. No se habilitaron reparaciones.
- **SSH**: conservar perfiles/política de `ADMINISTRATION.md`. No se incorporó shell arbitraria al bus de eventos ni a la API Core.
- **iPhone/Tailscale**: el puente iPhone y el servidor Pet siguen disponibles con sus límites anteriores. Esta entrega no configura Tailscale ni expone Core. La continuidad remota, TLS y autorizaciones por dispositivo siguen pendientes; no se proporcionan comandos que abran Core a Internet.
- **Audio sin GPU**: el reconocedor local Pet existente utiliza faster-whisper CPU/int8. El arbitraje nuevo no necesita GPU. No se validó conversación completa en un equipo sin GPU ni en una RTX 2060.

## 8. Empaquetado Windows

Se construyó NSIS x64 con Electron 44.7.2 mediante:

```powershell
Set-Location C:\karen\desktop-pet
npm run build
npx --no-install electron-builder --win nsis --x64 --publish never --config.electronDist=node_modules/electron/dist --config.directories.output=release/core-async-20261031
```

Artefacto actualizado: `desktop-pet/release/core-async-20261031/Karen Desktop Pet Setup 1.6.8.exe`. Se conservó el artefacto anterior en `release/core-20261031/`.

- Tamaño: **129.217.160 bytes**.
- SHA-256: `0DDF02379F253D6704DAE6807B3796A01DFB14D818DE973EA43DEA755FBA524E`.
- Existe `win-unpacked/Karen Desktop Pet.exe`; el smoke IPC se ejecutó contra él y pasó.
- Los smokes de tareas compartidas y micrófono se ejecutaron también contra el nuevo EXE, con resultado OK.
- Contiene el SQL compilado y el worker Python fuera de ASAR. El worker usa el entorno de voz existente; el instalador no incluye todos los modelos/entornos.
- Se extrajo el SQL del ASAR y se comparó byte por byte con la fuente: **OK**.
- **Sin firma digital**, conforme a la configuración existente. El hash permite comprobar esta copia local, no acredita un editor ni implementa actualización segura.
- Conserva versión 1.6.8; es una compilación de verificación local, no una publicación o actualización distribuida. No se probó ejecutar el instalador, instalar/desinstalar ni migrar una instalación productiva.
- No se creó un EXE de Karen clásica: su entrada sigue siendo `start_karen.ps1`/Python.

## 9. Reversión y recuperación

1. Cerrar clásica, Pet, API Core y monitores que escriban datos. No cerrar a la fuerza una escritura administrativa sin verificar su resultado; usar `task_review.py` si queda uncertain.
2. Crear un respaldo del estado actual con `maintenance.py backup` y comprobarlo con `verify`. Esto conserva chats nuevos antes de revertir. Respaldar también, con Pet detenido, su directorio real `userData` si se van a modificar ajustes de una instalación productiva. Esta entrega solo cambió el perfil QA durante los smokes.
3. Extraer `backups/autonomy-baseline-20261031T202117Z/source.zip` en un directorio de revisión, no sobre el repositorio vivo. Contiene `classic/` y `desktop-pet/`. Restaurar únicamente los archivos de código afectados, comparando antes con los cambios actuales del usuario. No usar `git reset --hard`, `git clean` ni sobrescribir `DESIGN.md`, `design-system/`, `ollama-openclaw.Modelfile` o cambios del plan.
4. Revertir ambos clientes juntos si se quiere retirar el arbitraje; una versión antigua que no coopera puede volver a competir por audio. Reconstruir Pet desde el código elegido. No se instaló esta compilación, por lo que no hay una instalación del usuario que desinstalar por esta entrega.
5. El esquema principal continúa en v1; el código anterior puede conservar las tablas/triggers añadidos, sin perder turnos nuevos. Si se requiere restaurar datos anteriores, exportar antes los nuevos chats y revisar qué se perdería. Restaurar las bases de backup con todos los clientes detenidos; **no restaurar WAL/SHM ni locks de una sesión activa**. No restaurar una base sobre un proceso abierto.
6. Restaurar archivos DPAPI sin descifrarlos. Solo el mismo usuario/perfil Windows puede normalmente recuperarlos. Una copia de esos blobs no garantiza recuperación en otro equipo o cuenta.
7. Reiniciar una interfaz, comprobar historial y configuración, después abrir la otra. Las filas de actividad antiguas se ocultan tras 15 segundos; los locks OS se liberan al terminar sus procesos. No borrar archivos de lock para intentar forzar propiedad.

Para respaldos futuros:

```powershell
python maintenance.py backup 'backups\nombre-nuevo'
python maintenance.py verify 'backups\nombre-nuevo'
```

La herramienta no restaura automáticamente ni sobrescribe un respaldo existente. El backup de cada SQLite es consistente individualmente; no constituye una transacción distribuida entre todas las bases y configuraciones. Detener los clientes ofrece la mejor instantánea conjunta.

## 10. Registro de cambios y pendientes

Cambios de estas entregas: registro de eventos acotado; actividad compartida; bloqueo OS del micrófono e IPC con tickets; API para IDs Pet/eventos/actividad; CRUD de chats por CLI; rechazo de turnos huérfanos; respaldos verificables; archivo asíncrono en clásica; creación/activación atómica; consultas de tareas compartidas desde Pet; comandos Core con Gateway desconectado; pruebas nativas y métricas Windows. Se conservaron proveedores, formas Pet, preferencias, políticas y mecanismos de autorización anteriores.

Continuar en el orden solicitado, sin pasar a un rediseño visual:

1. **Terminar núcleo compartido**: propiedad integral de sesiones, registro central de capacidades/permisos, lifecycle de servicios y resultados persistidos de tareas. El archivo de chats/estilo ya trabaja fuera de Tk y Pet ya consulta IDs/estados compartidos. Faltan ejecución/cancelación compartidas con permisos centrales y otras rutas de I/O de interfaz por perfilar.
2. **Proveedores**: prueba contra Gateway real, reinicio/reconexión, cancelación y diagnóstico de fallos sin duplicar efectos.
3. **Voz**: propietario único del pipeline, VAD dedicado, barge-in con prevención de eco, cancelación completa, dispositivos físicos y selección multilingüe; instrumentar detección/STT/generación/primer audio.
4. **Memoria**: distinguir capas, contradicciones y obsolescencia, recuperar contexto con política de privacidad y finalizar la interfaz de gestión. Las transferencias revisadas actuales siguen siendo explícitas.
5. Después: planificación con persistencia/reanudación segura, herramientas e inventarios ampliados, percepción con accesibilidad/OCR autorizado, automatizaciones generales y suscripciones/verificación HA.
6. Finalmente: continuidad móvil autenticada por transporte seguro, enrutamiento de modelos respetando privacidad, rediseño y optimización con medición de hardware.

No están completos los bloques B/C ni todos los componentes críticos del Bloque A. No se ejecutaron tareas autónomas, acciones privilegiadas, envíos, capturas continuas, reparaciones remotas ni controles domóticos reales. El resultado verificable es esta base incremental y los mecanismos terminados descritos arriba.

## 11. Continuación del núcleo: trazabilidad y reversión

Antes de esta continuación se creó y verificó `backups/before-async-core-20261031/`, con 197 archivos de respaldo y fuente de ambos repositorios. Conserva el estado de la entrega anterior, incluidos los cambios del usuario. El respaldo final actualizado se guarda en `backups/delivery-core-async-20261031/` y se verifica con `maintenance.py`.

Para revertir solo esta continuación, cerrar ambos clientes/API, respaldar el estado actual y revisar `source.zip` del respaldo `before-async-core-20261031` en un directorio separado. Recuperar los archivos afectados de ambos repositorios sin sobrescribir cambios posteriores del usuario. No se cambió el esquema de historial/tareas por esta continuación; los datos nuevos permanecen compatibles con el esquema anterior. Retirar `KAREN_TASKS_DB` del entorno devuelve la selección de archivo clásica a su valor previo; comprobar la ruta antes de ejecutar trabajos para no confundir registros. El instalador anterior se conserva y ninguno se instaló automáticamente.

Se revisaron los dos compositores modificados con la habilidad `vercel:react-best-practices`: lógica derivada sin nuevos efectos/hooks, entradas etiquetadas, clasificación de comandos compartida, sin dependencias nuevas y typecheck/nativo aprobados. El aviso de tamaño del chunk PixiJS continúa pendiente. Las pruebas que dependen de instrumentos físicos o Gateway real conservan su estado pendiente.

Los smokes Core finales usan perfiles temporales aislados, con voz, reconocimiento y wake desactivados desde el arranque. La variable `KAREN_QA_PROFILE` solo se considera con `--qa`. El helper comprueba la ruta resuelta antes de limpiar esos directorios. Ambos smokes se repitieron desde código y contra el nuevo paquete; no usan credenciales ni preferencias de un perfil QA anterior.

## 12. Reparación de voz solicitada por el usuario

La instalación activa mostraba la carpeta de recursos sin configurar en su sesión. Se reaplicó `C:\karen` desde la interfaz; el aviso cambió a «Di “Karen” para activarme» y la escucha permaneció activa. El worker STT instalado también cargó el modelo real y procesó PCM silencioso sintético correctamente. La comprobación no equivale a una conversación hablada real. Detalles, límites y respaldo del perfil convencional: [docs/VOICE_REPAIR_2026-10-31.md](docs/VOICE_REPAIR_2026-10-31.md). No se cambió código ni se instaló una versión para esta reparación.

## 13. Continuación: voz local original acelerada

Se terminó una mejora real de TTS del Bloque A solicitada por el usuario. El
modelo sigue siendo Qwen3-TTS 0.6B Base y la referencia original v2 conserva
exactamente su hash. La entrega no cambia OpenClaw, historiales, credenciales,
datos ni preferencias de forma de la mascota. No hay migración de esquema.

Antes: inferencia FP32 eager, decoder CPU y generación completa antes de audio.
Ahora: backend optativo CUDA graphs FP32/SDPA, encoder CPU, decoder GPU con
activaciones acotadas y recuperación a CPU, un hilo persistente de inferencia,
cola acotada, detección de desconexión/cancelación por conexión y diagnóstico
sin registrar contenido del usuario. El renderer nuevo aprovecha el prefetch
existente por oraciones completas. No se implementó streaming PCM ni barge-in.

**Resultado real Windows/RTX 2060:** misma primera frase, sin caché, de 26,126 s
a **3,111 s** de entrega HTTP del WAV con el modelo caliente, aproximadamente
8,4 veces más rápido. Otras dos frases: 3,108 y 3,840 s. La preparación fría
tardó 25,039 s y se mide por separado. En Electron, dos oraciones comenzaron
a reproducirse a los 5,157 s; el cambio a la segunda tardó 24,3 ms gracias al
prefetch. Cancelar una petición activa recuperó el servicio en 0,141 s y después
se generó otra frase correctamente. Salida silenciada durante el smoke;
estas mediciones no constituyen una revisión humana de naturalidad.

Whisper small CPU transcribió las tres muestras finales con WER 0 en ese pequeño
conjunto. No permite afirmar que la voz sea indistinguible de una persona.
FP16 y nucleus sampling del predictor capturado se descartaron tras fallos
reales; se documenta la configuración estable usada, sin alterar el perfil original.

### Archivos de esta continuación

- Raíz nuevos: `setup_fast_tts.py`, `requirements-tts-fast.txt`,
  `qa/measure_tts.py`, `qa/probe_fast_tts.py`, `qa/verify_tts_api.py`,
  `docs/LOCAL_TTS_ACCELERATION_2026-10-31.md`.
- Raíz modificados: `.gitignore`, `VOZ_Y_ACTIVACION.md`, este informe.
- Pet nuevos: `python/voice_acceleration.py`,
  `tests/test_voice_acceleration.py`, `scripts/accelerated-voice-smoke.cjs`.
- Pet modificados: `python/shared_voice_service.py`, `src/voice/replies.ts`,
  `src/voice/audio.ts`, `tests/voice-replies.test.ts`, `package.json`.
- Recursos locales excluidos de Git: overlay `tts-fast-runtime/`, configuración
  `voice-models/tts-runtime.json`, muestras WAV, métricas y respaldos. Entorno
  expressive-runtime y modelos originales no se actualizaron ni reemplazaron.

### Validación y estado instalado

- Unitarias clásicas: **165 OK**, 34,734 s.
- TypeScript Pet: **131 OK**, 22 archivos, 8,68 s.
- Contratos Python de voz: **22 OK**, incluidos aislamiento de conexiones,
  cancelación, restauración de métodos, recuperación OOM simulada y UTF-8 BOM.
- Typecheck y build Windows aprobados. Persiste advertencia de chunk PixiJS.
- Smoke de voz en Electron con Qwen/GPU reales aprobado, sin errores renderer.
- API real: 403 sin credencial válida/con Origin; 409 con otro perfil; 400 con
  JSON de forma incorrecta, estilo desconocido y texto vacío; salud sin cambios.
- OOM se prueba con doble; no se forzó agotamiento real de memoria del usuario.
- No se probó micrófono físico desconectado ni conversación hablada con eco/VAD.

Se actualizaron dos workers de voz en la instalación actual, conservando su
renderer y todos los ajustes. El nuevo servicio se inició desde la ruta instalada,
no solo desde la fuente. Respaldo privado y verificable:
`backups/voice-service-installed-20261101T021547Z` (fecha UTC). Referencia/código/datos
previos: `backups/before-local-tts-20261031`. La aceleración queda disponible para
los clientes protocolo 2 actuales, incluso sin instalar el renderer nuevo.

Para configurar/arrancar, repetir mediciones, revisar limitaciones y revertir:
[guía de voz local](docs/LOCAL_TTS_ACCELERATION_2026-10-31.md). No se instaló
automáticamente el paquete completo ni se actualizaron interfaces ajenas a voz.

Paquete Windows de esta continuación:
`desktop-pet/release/voice-cuda-20261031/Karen Desktop Pet Setup 1.6.8.exe`,
**129220890 bytes**, SHA-256
`BA31C63C480FA7C7E2BAC151F3756A1273AA0037E415CD5F6397DA4534A7D151`.
NSIS x64 generado correctamente y sin firma. El EXE desempaquetado pasó el smoke
GPU/Electron con el worker instalado: primer audio 4,504 s, separación de
oraciones 23,4 ms, recuperación de cancelación 0,403 s y síntesis posterior OK.
Los dos workers de fuente, instalación y paquete son idénticos por hash; el
respaldo anterior instalado también se verificó por hash. No se ejecutó el
instalador ni se probó desinstalación/actualización productiva del paquete completo.

Pendientes del Bloque A: todavía faltan propietario integral de voz, VAD/barge-in,
PCM continuo, prueba real de reconexión Gateway y completar memoria/orquestación
compartidas. Esta entrega finaliza aceleración local y cancelación por conexión;
no declara terminado el asistente autónomo completo.

La cancelación GPU real descrita corresponde a Pet cerrando su conexión HTTP.
El cliente clásico aún puede dejar su urllib pendiente aunque descarte la
respuesta; esa parte de la cancelación compartida sigue pendiente. Respaldo de
entrega final: `backups/delivery-voice-final-20261031`, verificable con maintenance.py.

## 14. Karen 1.7.0: cuerpos, estilos, reposo y latencia

Solicitud posterior del usuario: variantes con/sin brazos y piernas, controles
reales, entretenimiento de reposo, estilos adicionales y mayor rapidez. Se
implementó incrementalmente en la Pet existente, manteniendo el núcleo y la
misma identidad vocal. No se hicieron cambios a servidores, domótica ni permisos.

### Funciones terminadas y arquitectura

- Ocho apariencias, incluidas las cinco originales: Aurora, Ámbar y Nocturna
  se incorporan al catálogo existente. Los acabados y las nuevas siluetas se
  pintan con el mismo renderizador; no hay otro cliente, memoria o motor de IA.
- Controles persistentes independientes de brazos/piernas, tres presets de
  cuerpo y botón de la barra de la mascota. Las extremidades ocultas desaparecen
  del renderizado y de su máscara de ratón. Miniaturas y accesibilidad coherentes.
- Planificador visual de reposo separado de PetMachine: juega con una luz,
  se estira o contempla estrellas. Respeta actividad real, capturas, estados
  ocupados observados en Core, respuestas pendientes, descanso y accesibilidad.
  No llama a modelos ni ejecuta herramientas para aparentar autonomía.
- Ajustes nuevos tipados/validados, valores por defecto para configuraciones
  anteriores y persistencia al reiniciar. Las preferencias existentes de voz,
  forma, conexiones y seguridad se conservan.
- Techo de reposo 24 FPS y 12 en bajo consumo/sueño/movimiento reducido.
  Ventanas ocultas detienen ticker y actividades. Se corrigió un fallo nativo
  Windows de ocultar/mostrar: Electron ahora comunica visibilidad por ventana,
  además de Page Visibility, y no se retoma un juego atrasado.
- Primera oración local de 40 caracteres, siguientes de 70 y máximo 240 por
  clip. Prefetch existente, texto completo conservado, precarga al detectar wake.
- Cliente clásico con socket propio cancelable, incluso esperando cabeceras o
  cuerpo. Esto resuelve la limitación urllib pendiente del corte del 31 de octubre.

### Pruebas y métricas reales

- **143** pruebas TypeScript Pet, **25** contratos Python de voz y **165**
  pruebas clásicas, aprobadas; **333** unitarias en total. Typecheck y build
  Windows aprobados. Persiste el aviso de tamaño del chunk PixiJS.
- Smoke visual fuente: ocho estilos, píxeles reales de brazos/piernas, tres
  pasatiempos temporizados, prioridad THINKING, 50/100/200 % de escala,
  movimiento reducido, ocultar/mostrar y preferencias después de reiniciar.
  Sin errores renderer. Solo perfiles/Core temporales y sin micrófono/Gateway.
- Píxeles opacos en región de brazos: 878 con brazos frente a 152 sin ellos;
  región de piernas: 1832 frente a 197. Es una comparación del canvas real,
  no solo de variables de configuración.
- Última medición de fuente: 22 FPS en reposo (techo 24); CPU reportada por
  Electron aproximadamente 0,379/0,390 por ciento por renderer en una muestra
  corta. No se extrapola a ahorro energético ni a estabilidad prolongada.
- Voz GPU real con salida silenciada y mensaje final sintético: comparación
  secuencial controlada de EXE 1.6.8 frente a EXE 1.7.0, **6,475 → 2,920 s**
  hasta primer audio, alrededor de 55 % menos espera para ese texto. Ambas
  primeras síntesis sin caché. Segunda oración en 1.7.0 tras 83 ms de transición.
  No se midió una mejora de generación de texto del proveedor ni del STT.
- Cancelación clásica real: **0,058 s** para devolver control al cliente y
  **0,138 s** hasta servicio libre; síntesis posterior válida. Sin reproducción.
- Contratos TCP adicionales sin modelo: cancelación antes de conectar,
  esperando cabeceras y esperando cuerpo. No se cancela otra conexión.

Fuentes detalladas, capturas, configuración, instrucciones Windows y límites:
[Karen 1.7.0](docs/PET_VARIANTS_2026-11-01.md). Los resultados QA contienen texto
sintético; no se imprimieron credenciales ni se usaron conversaciones personales.

### Archivos de esta continuación

Raíz: `.gitignore`, `VOZ_Y_ACTIVACION.md`, `IMPLEMENTATION_REPORT.md`,
`docs/LOCAL_TTS_ACCELERATION_2026-10-31.md`; nuevos
`docs/PET_VARIANTS_2026-11-01.md` y `qa/verify_classic_voice_cancel.py`.

Pet modificados: `package.json`, `package-lock.json`, `shared/types.ts`,
`shared/settings.ts`, `shared/pet-styles.ts`, `shared/version.ts`,
`electron/main.ts`, `src/main.tsx`, `src/style.css`, `src/state/machine.ts`,
`src/state/store.ts`, `src/pet/Renderer.tsx`, `src/pet/textures.ts`,
`src/pet/StylePicker.tsx`, `src/voice/audio.ts`, `src/voice/replies.ts`,
`python/shared_voice_client.py`, `tests/voice-replies.test.ts`,
`scripts/accelerated-voice-smoke.cjs`, `scripts/styles-smoke.cjs`.
Nuevos: `src/pet/idle-activities.ts`, `tests/idle-activities.test.ts`,
`tests/test_voice_client.py`, `scripts/pet-variants-smoke.cjs`.

Las habilidades animate, ui-ux-pro-max y react-best-practices se aplicaron al
trabajo visual: eventos reales prevalecen sobre diversión, movimiento reducido,
botones etiquetados, geometría transformada en Pixi, controles instantáneos,
sin actualizaciones React por frame, limpieza de suscripciones y sin dependencias
de animación nuevas. Los datos de usuario y cambios anteriores se preservaron.

### Entrega y reversión

Versión sincronizada en package.json, lockfile y APP_VERSION: **1.7.0**.
El instalador y su EXE se generan en
`desktop-pet/release/variants-170-20261101/`. El paquete completo no se instala
automáticamente sobre la Pet abierta; la mejora del cliente clásico se usa desde
el código actualizado. El servicio acelerado previo permanece compatible.

Instalador final: `Karen Desktop Pet Setup 1.7.0.exe`, **129223350 bytes**,
SHA-256 `A9EB0786D78A0E9DFE3A35C585775ABD98E0D9E2FCB03EDFDDEB167FF7F87D0A`.
NSIS x64 local, sin firma ni publicación. El EXE final pasó `test:variants`
incluyendo el caso Windows que había fallado antes de corregir visibilidad.
Persistencia, tres pasatiempos, escalado, brazos/piernas, reduced motion y
recuperación sin juego atrasado: OK. La regresión adicional `test:styles`
recorrió 120 combinaciones visuales y teclado/persistencia, sin errores.
No se ejecutó el flujo de instalación/desinstalación sobre el perfil productivo.
Los tres módulos Python de voz empaquetados se compararon con fuente y coinciden.

Respaldo previo verificado: `backups/before-pet-variants-20261101`.
La guía incluye reversión de código, perfil y nuevas formas al volver a una
versión antigua: Aurora/Ámbar deben cambiar a Cristal y Nocturna a Órbita,
o restaurar solo los ajustes anteriores tras respaldar los actuales. No se
reescribió ni migró ninguna base de conversaciones/tareas en esta entrega.

Respaldo final: `backups/delivery-pet-170-20261101`, fuente/datos/capturas con
manifest y hashes verificados. Los directorios de respaldo conservan ACL privada
del usuario de Windows. Las pruebas no utilizaron ni alteraron el perfil habitual.

Siguen pendientes VAD/barge-in, PCM continuo, memoria/orquestación completas,
reconexión Gateway verificada y estabilidad prolongada/hardware sin GPU. Las
actividades de reposo no se presentan como ejecución autónoma de herramientas.

## 15. Continuación 2026-11-02: interfaz, errores e iniciativa

Entrega **1.8.0**. Guía detallada, capturas, configuración y recuperación:
[Interfaz e iniciativa](docs/KAREN_INTERFACE_INITIATIVE_2026-11-02.md).

### Arquitectura anterior y nueva

| Área | Antes de esta continuación | Implementación entregada |
|---|---|---|
| Renderizado | Una nueva Application Pixi al cambiar estilo/acento; montaje previo a recibir preferencias | Montaje tras cargar configuración; texturas reemplazadas en un único contexto WebGL |
| Clics transparentes | Eventos de posición condicionados a seguir el cursor | Hit testing nativo disponible también con mirada desactivada |
| Conversación | Columna de mascota permanente y controles de modelo siempre abiertos | Más ancho de conversación; modelo plegable; estados reales de voz; editor visible en tamaño mínimo |
| Iniciativa | Sin planificador de compañía | Un propietario en Electron main, política tipada y diario local versionado y acotado |
| Voz espontánea | Sin ruta de propuesta | Evento del propietario hacia el AudioDirector existente, con cancelación y preferencias actuales |
| Tareas | Consulta manual desde Core | Observación de metadatos; aviso de cambio; consulta posterior con envío explícito |

**Correcciones con evidencia:** un probe de arranque reprodujo
`Cannot read properties of null (reading 'clear')` dentro del batcher Pixi al cargar
una apariencia guardada. Tras la corrección no aparece; los smokes comprueban que
el canvas no cambia durante nueve cambios de estilo. El test de Windows también
recibe posiciones de cursor con `cursorTracking=false`. La versión de 1.7.0 no
tenía esa garantía, porque cortaba precisamente esos eventos.

### Funciones realmente terminadas

- Interfaz azul profundo/cian, navegación agrupada, tipografía legible, selector de
  modo global y modelo plegable. Se conservan las ocho apariencias y extremidades.
- Centro Iniciativa con habilitación, voz opcional, intervalo, límite diario,
  horario silencioso y pausa/reanudación de una hora.
- Saludo diario y preguntas locales de compañía; aviso acotado de desconexión;
  avisos de cambios de tareas observados mientras la aplicación está abierta.
- Diario de 30 avisos con motivo, fecha y cierre; deduplicación de hasta 80 cambios
  de tarea y recuperación de intervalo/cuota/pausa al reiniciar.
- Propuestas compartidas entre Pet y panel. Guardado previo a emisión y recuperación
  conservadora: un archivo incompatible no se sobrescribe ni activa un planificador.
- Rechazo de iniciativa durante ausencia, bloqueo, ocultación, modo Gaming/No
  molestar, trabajo activo o captura. Los avisos no dan permisos ni ejecutan tareas.
- Las interacciones en las ventanas propias posponen las propuestas y cancelan su
  voz; se conserva la protección de wake word contra la voz del asistente.
- Globo de iniciativa para escala normal y 50 %, con descarte, respuesta y silencio.

La iniciativa usa textos y reglas locales; no se presenta como razonamiento
generativo ni como agente autónomo general. La voz utiliza el motor ya seleccionado
por el usuario. Las pruebas de Qwen no significan que se haya sustituido su motor
configurado en el perfil habitual.

### Archivos de esta continuación

Nuevos: `desktop-pet/shared/initiative.ts`, `shared/initiative-policy.ts`,
`electron/initiative.ts`, `src/InitiativePanel.tsx`, `tests/initiative.test.ts`,
`scripts/interface-initiative-smoke.cjs`, `scripts/startup-probe.cjs` bajo
`desktop-pet/`, además del diagnóstico de metadatos de arranque
`desktop-pet/scripts/diagnose-installed.cjs`; `qa/backup_pet_profile.py` y esta guía
bajo la raíz. El diagnóstico instalado se ejecuta únicamente con Pet cerrada:
abre su perfil habitual, no envía mensajes ni órdenes y vuelve a cerrar su proceso.

Modificados en Pet: `shared/types.ts`, `shared/settings.ts`, `shared/version.ts`,
`electron/main.ts`, `electron/preload.cjs`, `src/main.tsx`, `src/pet/Renderer.tsx`,
`src/pet/idle-activities.ts`, `tests/idle-activities.test.ts`,
`src/state/store.ts`, `src/style.css`, `src/voice/audio.ts`, `package.json` y
`package-lock.json`. En raíz: `.gitignore`, `IMPLEMENTATION_REPORT.md` y
`VOZ_Y_ACTIVACION.md`. Se conservan los cambios de continuaciones anteriores y
los archivos previos del usuario. No se añadieron dependencias ni commits.

### Verificación y métricas

- `npm test -- --reporter=dot`: **161 pruebas / 24 archivos OK**, 8,88 s.
- `npm run test:voice:contracts`: **25 pruebas Python OK**, 0,370 s.
- `python -m unittest discover -s qa -p 'test_*.py'`: **165 pruebas OK**, 22,636 s.
- Total: **351 pruebas unitarias**, separadas de los smokes Windows.
- `npm run build`: tipos, Vite, compilación Electron y copia de recursos OK.
- `npm run test:styles`: ocho estilos × 15 estados **visuales de demostración**;
  teclado, persistencia, movimiento reducido y modelo desconectado OK.
- Regresión adicional: el smoke de variantes encontró una espera de reposo antigua
  al pasar de animaciones apagadas y 30 segundos a animaciones activas y 15 segundos.
  Ahora el scheduler recalcula su plazo sin depender de recrear Pixi. Prueba unitaria
  añadida y smoke de fuente completo OK: luz, estiramiento, estrellas, cancelación,
  hide/show, accesibilidad y persistencia. Muestra breve de reposo: 21 FPS; CPU raw
  por renderer 0,8433 y 0,7551 según `app.getAppMetrics`, no estabilidad prolongada.
- Smoke de iniciativa desde fuente y EXE final: arranque guardado sin errores,
  mismo canvas al cambiar estilo, hit testing con mirada apagada, nueve combinaciones
  de pestaña/ancho, compositor en ventana 820 × 620, aviso a escala 50 %, cuota,
  pausa, recuperación y denegación de propuesta en No molestar OK.
- Aviso automático sobre cambio de una tarea SQLite **controlada**; pulsar Revisar
  prepara el comando, y enviar después realiza consulta local. Ningún servicio real
  de Windows, Proxmox o Home Assistant se administra en este smoke.
- Síntesis **Qwen local real** desde fuente y paquete con reproducción muda;
  se observa `HTMLMediaElement.play()` y se cancela desde el control de silencio.
  Sin micrófono, sin diálogo físico y sin petición al Gateway.
- Un primer smoke con arranque del servicio de voz quedó esperando el cierre del
  arnés tras salir Electron. Se detuvo solo el runner QA; el servicio quedó
  disponible. El arnés ahora acota esa espera y solo libera sus streams si Electron
  ya terminó con código cero. Las repeticiones finales terminaron normalmente;
  esto no certifica un ciclo frío completo de voz en todos los equipos.
- Último EXE: nueve actualizaciones consecutivas de preferencias, **76,81 ms en
  IPC**. Fuente: 69,89 ms. No miden fotogramas, latencia del modelo ni primer audio.
  No se extrapola una mejora de respuesta de IA ni estabilidad prolongada.

Los reportes `desktop-pet/qa/initiative/{source,packaged}-results.json` identifican
expresamente presencia, reloj y filas de tareas simuladas. Las capturas de la guía
corresponden a esos perfiles, no a conversaciones personales.

### Empaquetado, datos y puesta en uso

NSIS Windows x64 construido con Electron 44.7.2; no firmado y no publicado:

`desktop-pet/release/initiative-180-20261102/Karen Desktop Pet Setup 1.8.0.exe`

Tamaño **129.230.005 bytes**; SHA256
`8363ADC48E88AD09D4E558725EFDCDB0F6E585171C5F04A03DD7AE444C11C6A8`.

Respaldo previo de código/datos: `backups/before-initiative-20261101/`, **202 archivos
verificados**. Copia del perfil de instalación detenido:
`backups/pet-profile-before-180-20261102/`, **2 archivos**, hashes cotejados con origen
y ACL privada. El helper copia el vault cifrado si existe; no descifra credenciales.
SQLite se respalda por separado mediante `maintenance.py`, sin copiar WAL/SHM vivos.

**Instalación real completada:** NSIS terminó con código **0**. ProductVersion
**1.8.0.0**; ASAR instalado idéntico por hash al paquete probado; tres workers de
voz idénticos. Se cotejaron todos los valores anteriores de settings y los bytes
del vault cifrado: conservados. Solo se activaron `initiativeEnabled` y
`initiativeSpeak` para la petición explícita de compañía; el resto de nuevas
preferencias usa sus valores predeterminados. El motor configurado, escala 50 %,
apariencia y conexión se conservaron. Metadatos sin secretos en
`desktop-pet/qa/initiative/installation-results.json`.

El primer arranque normal mostró una superficie vacía en la captura nativa.
El diagnóstico del mismo perfil, sin enviar mensajes ni comandos, leyó DOM
completo, un canvas Pet, fondo y versión correctos, y cero errores JavaScript.
Después se inició de nuevo normalmente con logging local y se comprobó mediante
la interfaz nativa el diseño completo, **Conectada a OpenClaw**, **Escucha activada**
y ambos interruptores de Iniciativa encendidos (45 minutos, 4/día, silencio
22:00–09:00). Se dejó abierto el centro de iniciativa. No se borró caché ni se
cambiaron permisos de Windows. **La causa del arranque vacío intermitente no quedó
aislada y requiere seguimiento**; no se considera un fallo erradicado por pasar QA.
El indicador de escucha no sustituye una prueba física de dictado o barge-in.

Se pasó `KAREN_CORE_DB` al arranque con el archivo existente de conversaciones.
No hay `karen-tasks.sqlite3` en la instalación habitual: los avisos reales de tareas
requieren que la clásica cree trabajos y se configure `KAREN_TASKS_DB`. Los smokes
de este informe usaron un archivo temporal. No se creó inventario ni tareas falsas.

Los valores nuevos son aditivos; no hay migración destructiva de conversaciones o
tareas. Las otras instalaciones no reciben iniciativa activada por defecto.

Reversión: cerrar Pet, respaldar lo nuevo y reinstalar 1.7.0 conservada. El diario
de iniciativa se ignora en esa versión. Restaurar únicamente preferencias previas
si se quiere revertir su selección; no restaurar bases viejas sobre chats nuevos.

Entrega respaldada en `backups/delivery-interface-180-20261102/`: fuente de ambos
repositorios, instantáneas de datos, documentación final y diez capturas/reportes
QA seleccionados. Archivo y manifiesto con hashes comprobados mediante
`maintenance.py verify`. No contiene capturas de la conversación personal mostrada
al comprobar la instalación.

### Pendientes

Agente autónomo general, integración de iniciativa con la interfaz clásica,
eventos de tareas durante períodos cerrados, planificación generativa,
automatizaciones con herramientas, memoria automática, voz dúplex/barge-in,
micrófono físico/reconexiones de hardware y estabilidad prolongada siguen sin
certificarse, junto al arranque vacío intermitente descrito arriba. La conexión
autenticada real se observó en la interfaz, pero no se probó reiniciar el Gateway.
Hardware sin GPU e integraciones de servidores no se declaran aprobados por estos
smokes.
