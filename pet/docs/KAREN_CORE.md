# Karen Core SQLite v1: puente local inicial

Este puente es opcional y está limitado al mismo equipo. Karen clásica conserva su archivo `C:\karen\.private\conversations.sqlite3`; Desktop Pet puede escribir allí los turnos finales de su sesión OpenClaw. El adaptador usa `node:sqlite` del Electron incluido, sin proceso ni dependencia de pago adicional. El archivo debe existir antes de iniciar Pet.

## Activación local

Inicia Desktop Pet con la variable de entorno `KAREN_CORE_DB` apuntando a la ruta absoluta del archivo de conversaciones de Karen clásica. Para desarrollar desde este proyecto:

```powershell
$env:KAREN_CORE_DB = 'C:\karen\.private\conversations.sqlite3'
cd C:\karen\desktop-pet
npm run dev
```

Karen clásica usa esa ruta por defecto; también admite `KAREN_CORE_DB` para otra ruta absoluta. Pet en modo `--qa` no abre la base compartida. Un archivo ausente o incompatible deja el puente desactivado y registra un aviso. No se cambian los tokens de OpenClaw ni las confirmaciones administrativas.

## Contrato y límites

- `core_meta.schema_version = 1` identifica el formato. Una versión desconocida se rechaza.
- Una versión incompatible se comprueba antes de crear tablas del puente; abrirla no altera su esquema.
- Pet crea un chat `openclaw-<hash de sessionKey>` y guarda cada respuesta final junto a su petición. La clave `(session_key,run_id)` evita duplicados por reconexión o eventos repetidos.
- Los turnos parciales, cancelados o fallidos no se comparten. El historial clásico existente permanece en su archivo y las tablas nuevas son aditivas.
- Karen clásica puede abrir el chat Pet desde su selector al refrescar o reiniciar. Si usa ese chat con Ollama, el historial compartido puede entrar en el contexto del modelo seleccionado. Configura un modelo local si no quieres enviar ese contenido a un proveedor remoto.
- Pet puede consultar chats clásicos con `/historial listar` y `/historial ver ID`. La lectura es local, muestra los diez últimos turnos confirmados y no se envía a OpenClaw. No hay permisos por cliente ni sincronización entre equipos en este contrato inicial. No se marca completa la fase Core.

## Continuar un chat clásico desde Pet

`/historial preparar ID` muestra exactamente el texto propuesto para enviar a OpenClaw: los cinco últimos turnos confirmados como máximo, con hasta 700 caracteres de cada mensaje. No transmite nada. Para enviar esa vista previa al proveedor del modelo activo, escribe `/historial enviar ID` antes de cinco minutos. `/historial cancelar` descarta la preparación. Pet vuelve a leer esos turnos justo antes del envío; si cambió el texto mostrado, exige otra vista previa. La confirmación consume la preparación una sola vez; si falla el envío, vuelve a preparar y revisa el historial de OpenClaw antes de repetir. La transferencia no se copia de vuelta al archivo Core como un turno nuevo. Los mensajes posteriores de la misma sesión OpenClaw pueden usar ese contexto, pero esta función no fusiona ni migra sesiones. Si el proveedor activo es remoto, el texto aprobado sale del PC. Las autorizaciones de herramientas de OpenClaw siguen aplicándose por separado.

## Memoria local inicial

Karen clásica dispone de `/memoria guardar PROYECTO | TEXTO`, `/memoria listar PROYECTO`, `/memoria buscar PROYECTO | TEXTO`, `/memoria editar ID | TEXTO` y `/memoria borrar ID`. Estos comandos se procesan localmente y no se envían al modelo ni se añaden al historial. `python memory_cli.py --help` permite consultar, editar y exportar memorias, además de fijar retención y marcar inferencias. Los datos sensibles requieren `--allow-sensitive` explícito; el archivo SQLite no cifra su contenido, por lo que no se recomienda guardar secretos.

Pet ofrece solo `/memoria listar PROYECTO` y `/memoria buscar PROYECTO | TEXTO` cuando comparte la misma base. La consulta funciona sin conexión a OpenClaw, no se envía al Gateway y excluye memorias sensibles y caducadas. La respuesta se muestra en la sesión Pet sin síntesis de voz. No hay recuperación automática de memoria para respuestas del modelo ni escritura desde Pet. La memoria no equivale todavía a continuidad de conversaciones.

Para añadir contexto de memoria a una sesión OpenClaw, usa `/memoria preparar PROYECTO | CONSULTA`. Pet muestra el texto exacto de hasta tres recuerdos **confirmados y no sensibles**, limitados a 400 caracteres cada uno, sin enviarlo. `/memoria enviar` vuelve a consultar Core y solo transmite la vista previa una vez si el texto sigue idéntico. Un recuerdo editado, eliminado o que deje de estar confirmado exige preparar de nuevo. La autorización dura cinco minutos; `/memoria cancelar` la descarta. Cambiar de agente, desconectar o preparar otra búsqueda invalida la vista previa anterior. La transferencia no crea otro turno en Core. Si el proveedor es remoto, los recuerdos aprobados salen del equipo. El modelo debe tratar recuerdos como datos; los permisos de herramientas siguen bajo los controles de OpenClaw. Este flujo no recupera memorias de forma automática.

Karen clásica también dispone de una preparación explícita con los mismos comandos. Allí `/memoria enviar` autoriza el contexto solo para la siguiente consulta al modelo, sin copiar los recuerdos al historial; no transfiere automáticamente ese contexto a la sesión OpenClaw de Pet. Cada interfaz conserva su propia autorización temporal.

## Preferencia compartida inicial

Con `KAREN_CORE_DB` activo en ambas aplicaciones, el estilo de voz (`neutral`, `serene`, `warm`, `serious`, `bright` o `wry`) se guarda en la tabla `preferences` bajo `core.voice_style`. La base compartida tiene prioridad al iniciar cada aplicación; un cambio desde Ajustes de Pet o al guardar la configuración clásica actualiza esa clave. Ambas aplicaciones consultan el valor cada cinco segundos y lo aplican a respuestas futuras. La clásica conserva una selección de estilo que el usuario aún no ha guardado. `KAREN_VOICE_STYLE` tiene prioridad en la clásica y desactiva esa lectura periódica. No se comparten dispositivos, motores de voz, credenciales ni ajustes de privacidad. El registro de Pet o la pantalla clásica avisan si falla la escritura compartida. La actualización en vivo todavía requiere una prueba manual con las dos ventanas abiertas.

Pet guarda el modo manual `normal`, `gaming` o `do_not_disturb` bajo `core.mode` en el mismo archivo. Al iniciar toma el valor compartido si existe; después consulta cambios cada cinco segundos. El monitor opcional de alertas de Karen clásica lee esa preferencia si también recibe `KAREN_CORE_DB`: Gaming y No molestar aplazan alertas no críticas, mientras las críticas siguen visibles. El ajuste local `alert_monitor.py gaming on` también puede aplazarlas. Si Core no está disponible, cada interfaz conserva su modo local. La lectura cruzada usa SQLite local y no envía el modo a OpenClaw. Aún falta validar ambas ventanas y el monitor juntos durante una sesión real.

Karen clásica puede escribir el mismo valor con `/modo normal`, `/modo gaming` o `/modo no molestar`; `/modo` consulta el valor. Pet lo aplica en su siguiente ciclo de cinco segundos. La prueba de interoperabilidad comprueba ambas direcciones con SQLite temporal y procesos Python/Node.

Escribe `/core estado` en Pet para consultar si el puente está activo. Muestra versión, número de chats, recuerdos no sensibles vigentes y estilo compartido. Funciona sin OpenClaw y no envía esos datos al Gateway.

## Verificación

`python qa/verify_core_interop.py` desde `C:\karen` crea una base temporal, escribe un chat clásico y memorias, añade un turno Pet con Node y confirma lectura cruzada de chats y recuerdos, además de exclusión de memorias sensibles y del filtro Gaming/crítica. `npm test` cubre deduplicación, versión, consultas locales y emisión solo de respuestas finales. Estas pruebas no conectan a OpenClaw real ni migran datos privados.
# Coordinación añadida el 2026-10-31

El contrato v1 incorpora el SQL compartido `shared/core-events.sql`: registro acotado a 2.000 eventos sin contenido de conversaciones, y actividad con heartbeat de cinco segundos y expiración de 15 segundos. El panel muestra actividad de otras interfaces; `/core estado` también la consulta. No unifica la sesión interna OpenClaw ni sus permisos con Karen clásica.

## Metadatos de automatización y desarrollo — 2026-11-26

Con automation_policy_version=1, el lector incluye event_topic y Pet identifica
el evento y la próxima fecha de aceptación. Se mantiene compatibilidad con bases
anteriores sin esa extensión; una versión desconocida se rechaza. No ejecuta triggers.

`/automatizaciones listar` consulta hasta 50 schedules de KAREN_TASKS_DB;
`/desarrollo listar` consulta hasta 50 handoffs de KAREN_CORE_DB. Requieren las
versiones automation_version=1 y handoff_version=1 creadas por el runtime clásico.
Sin tablas compatibles se informa indisponibilidad y no se crean ni migran esas tablas.

Funcionan sin Gateway y muestran solo IDs, nombres/proyectos, fechas y estados.
No incluyen recetas, contexto, criterios, resultados ni hashes privados. Los
comandos no se transfieren a OpenClaw, no usan TTS y no permiten ejecutar ni
aprobar tareas. El lector de schedules abre SQLite en readOnly; el CoreStore
conserva su circuito anterior de historial. No se cambiaron los permisos del vault.

Verificación: 166 pruebas Vitest, typecheck y build correctos. La prueba cruzada
`python qa/verify_metadata_interop.py` del checkout clásico crea SQLite con Python
y lo consulta con estos adaptadores compilados; confirma archivo de tareas intacto,
payloads privados ausentes y cero planes ejecutados. No usa Gateway ni datos reales.
El ejecutable instalado del usuario no fue reemplazado por esta modificación.

Micrófono: `electron/core-resource.ts` obtiene un lock OS mediante `python/core_resource.py` antes de abrir hardware. Se usan tickets ligados al renderer autorizado, se liberan al cerrar los tracks y se limpian al cerrar el renderer/aplicación. La clásica importa esa misma implementación. La ubicación predeterminada es `%LOCALAPPDATA%/KarenCore/locks/microphone.lock`; `KAREN_RESOURCE_DIR`, si se define, debe ser absoluto e idéntico en los clientes. No borrar el lock con clientes activos. El navegador remoto no participa en este lock local.

Se necesita la carpeta de voz configurada con `voice-runtime/Scripts/python.exe`. Fallar el worker impide abrir el micrófono; no se salta el arbitraje. El worker se distribuye fuera de ASAR y no recibe audio ni carga modelos. Esto evita competencia entre capturas cooperantes; no implementa barge-in ni sustituye permisos de micrófono de Windows.

Pruebas nuevas: `npm test`, `npm run build`, `node scripts/core-resource-smoke.cjs`. El último comando usa el perfil QA y locks temporales, sin abrir audio. Puede apuntarse al EXE con `KAREN_SMOKE_EXECUTABLE`. Los smokes desde código y EXE empaquetado pasaron en Windows 11. El [informe principal del repositorio clásico](../../IMPLEMENTATION_REPORT.md) contiene límites, métricas y reversión.

## Continuación: tareas compartidas y comandos sin Gateway

Configurar, en ambos procesos, `KAREN_CORE_DB` y `KAREN_TASKS_DB` con rutas absolutas a sus archivos existentes. Para la instalación clásica habitual, las rutas son `C:\karen\.private\conversations.sqlite3` y `C:\karen\.private\karen-tasks.sqlite3`. La clásica conserva la ruta anterior si no se define la segunda variable; Pet requiere autorización explícita mediante esa variable para leer tareas. Un archivo inexistente no se crea al consultarlo desde Pet.

`/tareas listar` muestra hasta diez de las últimas cincuenta tareas; `/tareas estado ID` muestra estado registrado, cursor, fecha y hasta 32 pasos. Las consultas usan SQLite de solo lectura y conservan el mismo ID del ejecutor clásico. No reanudan, recuperan, ejecutan, aprueban ni cancelan trabajos. No incluyen argumentos, hashes ni valores de resultados. Las filas pueden sobrevivir a un proceso terminado: consultar su fecha y permitir que el ejecutor clásico concilie estados interrupted/uncertain antes de inferir actividad real.

Ambos compositores permiten comandos Core locales con Gateway desconectado. Las transferencias `/memoria enviar` y `/historial enviar ID` siguen exigiendo conexión y revisión previa. Las respuestas de tareas no se envían al modelo ni a TTS.

`node scripts/core-tasks-smoke.cjs` crea bases temporales y una herramienta sintética. Comprueba en Electron real el mismo ID pending/running/completed, una tarea inexistente, el botón habilitado sin Gateway y la exclusión de argumentos privados. Usar `KAREN_SMOKE_EXECUTABLE` permite repetirlo contra el paquete. `--qa --qa-core` habilita el Core temporal del smoke y mantiene desactivada la conexión automática del Gateway. La prueba no administra servicios ni valida herramientas físicas.

Los dos smokes Core usan perfiles nuevos bajo el directorio temporal, con reconocimiento, wake y reproducción desactivados desde el arranque. `KAREN_QA_PROFILE` selecciona ese perfil únicamente con `--qa`; no cambia el perfil normal. Su limpieza comprueba el límite del directorio resuelto antes de borrarlo. No reutilizan credenciales ni preferencias del perfil QA persistente.
