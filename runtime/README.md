# Karen

Karen clásica es un cliente Windows en Python/Tkinter. `desktop-pet/` es un cliente Electron para OpenClaw. Comparten opcionalmente el archivo Core v1 de turnos finales, eventos y actividad; ahora coordinan el micrófono con un bloqueo del sistema operativo. Sus motores de conversación y permisos todavía requieren unificación. El [informe de implementación](IMPLEMENTATION_REPORT.md) contiene cambios, pruebas Windows, instalador local, instrucciones y pendientes.

La clásica carga, refresca y cambia chats con un trabajador SQLite, sin consultar la base desde los callbacks de Tk. También comparte el estilo guardado en segundo plano. Pet puede consultar el mismo registro de tareas mediante `/tareas listar` y `/tareas estado ID`, incluso sin conexión a OpenClaw. Configura `KAREN_TASKS_DB` con la misma ruta absoluta en ambos procesos; sin esa variable la clásica conserva su ruta anterior y Pet no habilita la consulta de tareas. El puente Pet es de lectura: no ejecuta ni cancela tareas y no muestra argumentos ni resultados privados.

## Ejecutar Karen clásica

La [actualización personal local](docs/PERSONAL_AI_UPGRADE.md) documenta identidad persistente, documentos revisados, perfiles de recursos y continuidad tras cancelación manual. El [registro de progreso](KAREN_PROGRESS.md) distingue lo integrado de full-duplex y otras capacidades pendientes.

Requiere Python y las dependencias de `requirements.txt`; funciones de voz y calendario usan además `requirements-voice.txt` y `requirements-calendar.txt`. Revisa `settings.json` y usa tus propios endpoints y credenciales. Los datos privados van en `.private/`.

```powershell
python -m pip install -r requirements.txt
./start_karen.ps1
```

`start_karen.ps1` puede iniciar Ollama local si está configurado y disponible. Lee [PRODUCT.md](PRODUCT.md), [ADMINISTRATION.md](ADMINISTRATION.md) y [VOZ_Y_ACTIVACION.md](VOZ_Y_ACTIVACION.md) antes de activar herramientas o voz.

Karen clásica solicita respuestas Ollama en streaming también cuando TTS está desactivado. Muestra fragmentos completos en una vista previa temporal y conserva la respuesta final como un solo turno en el historial. La vista previa desaparece al terminar o fallar la petición.

Durante la generación aparece **Cancelar generación**. Detiene el stream y la voz asociada; una respuesta cancelada no se añade al historial. Si la conexión aún no ha entregado una respuesta HTTP, el botón registra la cancelación y Karen espera a que termine o agote el timeout de esa petición. **Detener voz** conserva su función independiente: silencia el audio sin cancelar el texto.

En Windows, `/ventana activa` consulta explícitamente el título, PID y nombre del proceso de la ventana en primer plano. Muestra el resultado solo en la interfaz local: no se envía al modelo, no se pronuncia mediante TTS y no se guarda en el historial. No captura la pantalla ni inspecciona el contenido de la ventana. Si escribes el comando en Karen, esa ventana suele ser la activa; para consultar otra aplicación, usa la voz mientras esa aplicación tenga el foco.

## Ejecutar Desktop Pet desde código

Requiere Node 24. Desktop Pet necesita un Gateway OpenClaw propio. Es un repositorio separado; clónalo en `desktop-pet/` junto a este README. La [guía de Desktop Pet](https://github.com/Duvetsillo/karen-desktop-pet/blob/fix/wake-stop-controls/README.md) cubre configuración Windows, servidor y seguridad. Karen clásica también usa los módulos Python de ese repositorio para estilo y activación; deben estar presentes antes de iniciarla.

```powershell
git clone --branch fix/wake-stop-controls https://github.com/Duvetsillo/karen-desktop-pet.git desktop-pet
cd desktop-pet
npm ci
npm run build
npm run dev
```

## Pruebas locales

```powershell
python -m unittest discover -s qa -p 'test_*.py'
python qa/verify_conversation_live.py --model gemma3:1b
cd desktop-pet
npm test
npm run typecheck
```

La prueba de continuidad usa un chat y una palabra sintéticos en SQLite temporal. Exige un Ollama local y rechaza el modelo cloud configurado por defecto; `--allow-remote` habilita de forma explícita una prueba remota. Usa un modelo local que tengas instalado.

Estas pruebas no validan micrófonos, proveedores, Home Assistant ni servidores físicos. El registro de validaciones y los siguientes pasos están en [docs/KAREN_IMPLEMENTATION_PLAN.md](docs/KAREN_IMPLEMENTATION_PLAN.md).

Para medir Ollama local con un prompt sintético fijo: `python qa/measure_ollama_latency.py --runs 3`. Informa tiempo hasta el primer token y tiempo total; si `psutil` está instalado, añade instantáneas RSS de procesos Ollama. No mide VRAM ni latencia de audio, y no lee chats ni memorias.

## Tareas locales

`/tareas informe pc` ejecuta tres lecturas reales de Windows: CPU durante 0,2 s, RAM física y espacio de la unidad del sistema. Devuelve un ID. `/tareas estado ID` consulta su estado; `/tareas cancelar ID` pide cancelación. Durante un informe aparece el botón **Cancelar tarea**; la interfaz puede cancelar el paso activo sin esperar a otra orden. Las tareas se registran en `.private/karen-tasks.sqlite3`: persisten estados, nombres y hashes de argumentos, pero no datos medidos. El motor acepta únicamente herramientas registradas por código, limita pasos y tiempo, y exige aprobación por cada paso de escritura. El informe actual es solo de lectura. No hay planificación autónoma de tareas ni control administrativo conectado a este motor.

Tras un cierre inesperado, el motor marca un paso de lectura abandonado como `interrupted` y uno de escritura en curso como `uncertain`. No reejecuta ninguno automáticamente. Un bloqueo local por tarea evita clasificar como abandonada una ejecución activa de otra instancia. Los archivos `.lock` en `.private/karen-tasks.sqlite3.locks/` solo sirven para coordinar procesos y no contienen argumentos ni resultados.

Si una escritura queda `uncertain`, comprueba su efecto en el sistema de destino. `python task_review.py list` muestra los ID pendientes. `python task_review.py review ID applied` o `review ID not_applied` registra el resultado que comprobaste; exige volver a escribir el ID. El estado queda `reviewed_applied` o `reviewed_not_applied` con un evento de auditoría; el paso conserva su estado incierto original. Esta revisión no ejecuta herramientas ni prueba por sí misma el efecto externo. Si no puedes comprobarlo, deja la tarea como `uncertain`.

## Alertas locales opcionales

`alert_monitor.py` funciona como proceso de consola independiente de las ventanas. Solo lee el espacio libre real de la unidad del sistema; no envía datos a modelos ni instala un servicio. Configura una regla antes de iniciarlo:

```powershell
python alert_monitor.py add-disk-rule '<' 10 --priority high
python alert_monitor.py check
python alert_monitor.py watch --interval 60
```

`watch` imprime alertas nuevas y continúa hasta Ctrl+C. `python alert_monitor.py history` consulta el registro; `rules` muestra reglas, `ack ID` confirma una alerta, `quiet 22:00 07:00` fija horas locales de silencio y `gaming on` aplaza alertas no críticas. `quiet` sin horas y `gaming off` restauran el comportamiento normal. Los estados persisten en `.private/karen-alerts.sqlite3`; lecturas obsoletas no generan avisos. El monitor no inicia con Windows y no muestra notificaciones del sistema todavía. Solo produce alertas cuando existe una regla y una medición real cruza su umbral.

También puede vigilar CPU y RAM disponible con las mismas reglas persistentes. Las muestras usan `GetSystemTimes` y `GlobalMemoryStatusEx` de Windows; CPU se mide durante 0,2 s. Un fallo de un sensor no impide procesar los otros. La consulta y vigilancia completa son opcionales:

```powershell
python alert_monitor.py add-cpu-rule '>' 85 --priority normal
python alert_monitor.py add-memory-rule '<' 12 --priority high
python alert_monitor.py check-pc
python alert_monitor.py watch-pc --interval 60
```

`python alert_monitor.py rules` muestra los ID. `python alert_monitor.py rule ID off` desactiva una regla; `rule ID on` la reactiva. `python alert_monitor.py source pc off` pausa todas las reglas del PC; `source pc on` las restaura. Desactivar resuelve alertas activas, pero conserva el historial.

En Karen clásica, `/alertas disco` realiza una lectura real inmediata y evalúa las reglas guardadas. `/alertas historial` muestra cinco avisos recientes y `/alertas confirmar ID` confirma uno. Estas respuestas son locales y solo usan TTS local; no entran al modelo ni al historial de chat.

Si Pet y el monitor reciben `KAREN_CORE_DB` con la misma ruta absoluta, el modo manual de Pet se comparte mediante `core.mode`: Gaming y No molestar aplazan avisos no críticos; los críticos siguen visibles. El monitor conserva su propio ajuste `gaming on|off`; cualquiera de los dos puede aplazar avisos no críticos. Sin Core disponible, continúa con el ajuste local. La sincronización física de ambas ventanas y el monitor sigue pendiente.

Karen clásica permite `/modo` para consultar el modo compartido y `/modo normal`, `/modo gaming` o `/modo no molestar` para cambiarlo. Pet lee ese cambio cada cinco segundos cuando apunta al mismo archivo Core. El comando se procesa localmente; no va al modelo ni al historial. Los modos Estudio, Servidor y Casa aún no están integrados.

Si el catálogo del modelo está desconectado, pulsa Enter para enviar `/modo`, `/memoria`, `/alertas`, `/tareas`, `/proxmox`, `/casa entidades` o `/ventana activa`; estas rutas locales ya no exigen un modelo listo. Una conversación normal sigue esperando la selección de un modelo disponible. Las integraciones locales pueden requerir sus propias credenciales o conexiones.

`/alertas pc` consulta disco, CPU y RAM en el momento; informa qué sensores fallaron y cuántas alertas nuevas generó. No inicia la vigilancia continua.

Para una comprobación breve del dispositivo de entrada configurado, sin guardar ni transcribir audio: `python diagnose_mic.py --seconds 0.16`. El diagnóstico muestra niveles y desbordamientos; no verifica reconocimiento de voz.

## Puente iPhone existente

La nueva [app de Karen para iPhone](docs/KAREN_IPHONE.md) permite conversar,
retomar historial y consultar tareas, alertas y recuerdos desde Safari o un
icono en la pantalla de inicio. Arranca con `./start_karen_mobile.ps1`; usa
`python mobile_server.py code` para ver el código privado de conexión. Es un
servidor independiente en loopback (`18793`) con acceso HTTPS mediante Tailscale
Serve; el PC debe permanecer encendido. No habilita controles administrativos.

`iphone_routines.py` conserva la rutina de llegada con aprobación previa. Una instalación nueva guarda su token en `.private/iphone-routines.dpapi`, cifrado para el usuario Windows. Si ya existe `.private/iphone-routines.json`, lo lee sin modificarlo para no romper el Atajo actual. `python iphone_routines.py --migrate-config` crea una copia DPAPI con el mismo token y puerto; no borra ni altera el JSON anterior. Comprueba el Atajo con el puente antes de retirar manualmente ese JSON. El puente sigue limitado a loopback y no habilita acceso remoto al Core. La prueba automatizada verifica el cifrado DPAPI y la migración con archivos temporales; no se probó el iPhone físico.

## Karen Core local

La API Core v1 opcional permite a un cliente **local** leer estado, lista de hasta 50 chats, los últimos 20 turnos de un chat, el estado de hasta 50 tareas, hasta 50 recuerdos no sensibles por proyecto y las últimas 50 alertas. Usa el SQLite de `KAREN_CORE_DB` cuando está definido, o el historial clásico predeterminado. Para tareas y alertas lee sus SQLite locales por separado y devuelve 503 si aún no existen. El servidor no arranca con Karen ni abre la red. Escucha únicamente en `127.0.0.1:18792`, exige `Authorization: Bearer TOKEN` y no permite escrituras. El token principal se guarda cifrado con DPAPI para el usuario Windows. Inicialización y arranque manual:

```powershell
python core_local_api.py init
python core_local_api.py token
python core_local_api.py serve
```

`token` muestra el secreto principal en la consola; no lo compartas ni lo pongas en una URL. `rotate` genera otro token principal; reinicia `serve` para revocar el anterior. Para cada cliente local, usa `python core_local_api.py issue NOMBRE`: entrega un ID y un token individual **una sola vez**. `--scope status` limita ese cliente a `/v1/status`; el alcance predeterminado `read` permite todas las lecturas. `python core_local_api.py clients` lista IDs y permisos sin secretos; `python core_local_api.py revoke ID` revoca el token del cliente de inmediato, incluso con el servidor abierto. El registro guarda solo hashes de los tokens individuales. Ejemplo de lectura desde otra consola, con el token principal en una variable local sin escribirlo en el historial de comandos: `$token = python core_local_api.py token; Invoke-RestMethod http://127.0.0.1:18792/v1/status -Headers @{Authorization = "Bearer $token"}`. Para tareas usa `/v1/tasks` y `/v1/tasks/ID`; el detalle incluye estados y nombres de herramientas, sin argumentos ni hashes. Para memorias usa `/v1/memories?project=Karen`; se omiten recuerdos sensibles y caducados, y se conserva la marca `confirmed` o `inferred`. `/v1/alerts` muestra alertas ya registradas, sin medir sensores ni crear avisos. Los turnos se limitan a 4.000 caracteres por campo; esta API aún no transfiere el estado interno de OpenClaw ni permite editar memorias. No está preparada para exposición por Tailscale, LAN o Internet: faltan TLS, autenticación de transporte y revisión de permisos por dispositivo. El servidor responde 503 cuando Core no se puede leer y no crea ni migra la base.

El [puente SQLite v1](https://github.com/Duvetsillo/karen-desktop-pet/blob/fix/wake-stop-controls/docs/KAREN_CORE.md) permite compartir turnos finales de Desktop Pet con Karen clásica cuando `KAREN_CORE_DB` apunta explícitamente al mismo archivo. Pet puede consultar chats clásicos con `/historial`; para llevar hasta cinco turnos a la sesión OpenClaw activa exige `/historial preparar ID` y después `/historial enviar ID`. Revisa la vista previa: el envío puede sacar ese contenido del PC si el modelo elegido es remoto. Es una integración parcial; consulta sus límites antes de activarla.

Karen clásica también tiene memoria local por proyecto mediante `/memoria` y `memory_cli.py`; Pet puede consultar memorias no sensibles con el puente activo. Consulta los comandos, el tratamiento de datos sensibles y las limitaciones en la guía del puente. Las respuestas de gestión de `/memoria` no se inyectan en el modelo ni en el historial. Solo usan TTS cuando hay un motor local configurado; con Edge TTS se muestran como texto.

En clásica, `/memoria preparar PROYECTO | CONSULTA` muestra hasta tres recuerdos confirmados y no sensibles, 400 caracteres cada uno, sin enviarlos. `/memoria enviar` autoriza usarlos **solo en la siguiente consulta al modelo** dentro de cinco minutos; `/memoria cancelar` descarta la preparación. La preparación se invalida al cambiar chat, sesión, servidor o modelo, y si un recuerdo cambia o caduca. La vista previa no se pronuncia. El contenido aprobado puede salir del PC si el proveedor es remoto. El historial guarda la pregunta normal y la respuesta, pero no copia allí los recuerdos; la tabla `core_memory_usage` registra solo IDs, chat, backend y fecha del intento de transferencia. Si el envío falla, el modelo puede haber recibido el contenido: revisa antes de repetir.

Pet también permite transferir hasta tres recuerdos públicos confirmados a OpenClaw: `/memoria preparar PROYECTO | CONSULTA` muestra el contenido exacto; `/memoria enviar` lo entrega tras revisión explícita, y `/memoria cancelar` descarta la preparación. La sesión debe seguir siendo la misma y la preparación vence a los cinco minutos. Un modelo remoto puede recibir ese contenido tras `/memoria enviar`.

Con el puente activo, ambas interfaces comparten el estilo de voz al guardar ajustes. Cada aplicación consulta el cambio cada cinco segundos y lo aplica a las respuestas siguientes; los cambios aún sin guardar en la clásica no se pisan. `KAREN_VOICE_STYLE` anula la sincronización en clásica. Pet también comparte su modo manual con las alertas locales; las demás preferencias siguen siendo locales. Si la base compartida no está disponible o usa una versión incompatible al iniciar, Karen clásica abre el historial local y muestra un aviso. Revisa `KAREN_CORE_DB` antes de seguir: los nuevos turnos no se compartirán mientras dure ese fallo.

Karen clásica también consulta cada cinco segundos los chats de Core. Los nuevos chats creados por Pet aparecen en el selector sin cambiar la conversación abierta; si Pet añade un turno al chat visible, la clásica recarga su contenido al quedar libre. Se puede seleccionar un chat Pet y continuar con Ollama desde clásica. Esto comparte turnos finales, no el estado interno de OpenClaw ni sus permisos. El refresco espera a que termine una respuesta local.

## Home Assistant: consulta de entidades

Las consultas directas funcionan con ambos motores (`karen` y `ollama`), aunque el catálogo de modelos esté desconectado:

- `/servidor estado friday-home` y `/servidor estado friday-datacenter` consultan por SSH el estado real de los servidores autorizados en `admin_policy.json`. Requieren los alias y claves ya configurados en `~/.ssh/config`.
- `/casa estado` consulta los dispositivos del cuarto mediante el webhook privado existente. `/casa estado luz`, `/casa estado abanico`, `/casa estado cargador`, `/casa estado nevera` y `/casa estado air fryer` consultan un dispositivo.

Estas rutas solo consultan: no ejecutan cambios ni envían los resultados al modelo o al historial. La voz de estos resultados usa el canal local privado. No necesitan un token REST de HA; usan `.private/ha_bridge.json`. La administración libre mediante herramientas sigue requiriendo modo Ollama y un modelo compatible.

En Karen clásica, `/casa entidades` lista hasta 50 entidades; `/casa entidades switch` filtra por dominio. Configura `KAREN_HA_API_URL` y `KAREN_HA_API_TOKEN` en el entorno de la sesión. La URL necesita HTTPS salvo en loopback. El comando usa solo `GET /api/states`, no llama servicios ni envía la respuesta al modelo, a TTS remoto o al historial. El control existente por webhook conserva su lista de cinco switches y sus permisos; descubrir una entidad no la autoriza para control.

## Proxmox: consultas de solo lectura

En Karen clásica, `/proxmox nodo NOMBRE` consulta el estado del nodo. `/proxmox vms NOMBRE` lista VM y `/proxmox contenedores NOMBRE` lista LXC. `/proxmox almacenamiento NOMBRE` muestra capacidad disponible, usada y total en GiB cuando la API entrega esos datos. `/proxmox quorum` consulta el estado del clúster; si la API no informa `quorate`, Karen no infiere el resultado. Configura `KAREN_PVE_URL` (HTTPS), `KAREN_PVE_TOKEN_ID` y `KAREN_PVE_TOKEN_SECRET` en el entorno de la sesión. El token necesita permisos de lectura para el nodo, los invitados, el almacenamiento y el clúster según la consulta. Las respuestas locales muestran solo campos filtrados, no se envían al modelo ni a TTS remoto y no se guardan en el historial. El certificado TLS se verifica; no se ejecutan reparaciones ni cambios administrativos. Inventarios limitados a 100 entradas por consulta.

## Karen Core 2 y Jarvis

La evolución incremental y local está documentada en [auditoría](docs/KAREN_CORE_2_AUDIT.md), [arquitectura](docs/KAREN_CORE_2.md), [uso y recuperación](docs/KAREN_CORE_2_OPERATIONS.md) y [aceptación y pendientes](docs/KAREN_CORE_2_ACCEPTANCE.md). La interfaz alternativa está en `http://127.0.0.1:18793/jarvis`; conserva el acceso privado del iPhone. Visión queda preparada y pausada, con su ampliación pendiente.

La [interfaz Jarvis holográfica](docs/KAREN_JARVIS_INTERFACE.md) incorpora un núcleo animado cian/ámbar junto al chat. Abre **Karen Jarvis** en el escritorio o ejecuta `launch_jarvis.ps1`. Para reinstalar el acceso directo, ejecuta `install_jarvis_shortcut.ps1`.

El diseño Jarvis actual sigue los [vídeos de referencia del usuario](docs/KAREN_JARVIS_PARTICLES.md): presencia de partículas orgánica o esférica, conversación flotante y herramientas desplegables.

Jarvis incluye [lectura con la voz local femenina y serena de Karen](docs/KAREN_JARVIS_VOICE.md), controles para probar/detener y coordinación de memoria entre chat y voz.

La [burbuja reactiva y el router de recursos](docs/KAREN_REACTIVE_ROUTING.md) sincronizan el efecto con el audio real: tareas ligeras en CPU, uso acotado de GPU para trabajo complejo y descarga de pesos al terminar.
