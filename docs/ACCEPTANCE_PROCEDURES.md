# Procedimientos de aceptación

Estos procedimientos separan automatización, integración local y hardware real. **No son un registro de que las pruebas manuales hayan pasado.** Los resultados ejecutados están en `../IMPLEMENTATION_REPORT.md`.

## Preparación y evidencia

Ejecutar los comandos Python desde `C:\karen`, y los comandos npm desde `C:\karen\desktop-pet`. Usar un usuario de prueba o una sesión aislada de OpenClaw con herramientas administrativas deshabilitadas. No probar borrados, reinicios de servidores, envío de mensajes ni cambios domóticos para validar una conversación.

Para las pruebas de historial, crear una base temporal distinta de los datos personales:

```powershell
$acceptanceDirectory = Join-Path $env:TEMP ('karen-acceptance-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $acceptanceDirectory | Out-Null
$env:KAREN_CORE_DB = Join-Path $acceptanceDirectory 'core.sqlite3'
python -c "from conversations import Conversations; Conversations()"
$env:KAREN_CORE_DB
```

Copiar la ruta mostrada a la variable `KAREN_CORE_DB` de la consola que inicia la otra interfaz. No cambiar `KAREN_RESOURCE_DIR`: los clientes deben usar el mismo arbitraje local normal. Los smokes automáticos usan un directorio de locks temporal propio y no acceden al audio del usuario.

Para tareas compartidas, definir también `$env:KAREN_TASKS_DB = Join-Path $acceptanceDirectory 'tasks.sqlite3'` en ambas consolas, con el mismo directorio. El ejecutor clásico crea la base al usar una tarea; Pet no la crea al leer. No mezclar una base de pruebas con el registro productivo.

Guardar por escenario: fecha, versión de ambos repositorios/EXE, versión CLI/Gateway por separado, modelo/proveedor, tipo de prueba, pasos, resultado esperado, resultado observado y errores. No incluir tokens, mensajes personales, capturas del escritorio completo ni grabaciones sin autorización. Si una capacidad falta, registrar **pendiente/fallo conocido**, no aprobado.

## 1. Conversación Pet y clásica

Automático: `python qa/verify_core_interop.py`. Usa Python, Node y SQLite reales con texto sintético; no prueba al modelo.

Manual: iniciar ambas interfaces con el mismo Core temporal, configurar un agente OpenClaw de pruebas y un modelo local en clásica. Desde Pet enviar «El marcador de esta prueba es COBALTO-73». Esperar el turno final. En clásica, esperar el refresco de cinco segundos, seleccionar el chat Pet y preguntar por el marcador. Comprobar el historial y que el modelo responde desde el contexto. Volver de clásica a Pet requiere hoy `/historial preparar ID` y `/historial enviar ID`, con revisión del texto. No tratar esa transferencia explícita como sesión interna unificada.

## 2. Reinicio de OpenClaw

Automático: `npm test -- tests/gateway.test.ts`; utiliza servidor WebSocket de contrato y dobles de runs/conexiones.

Manual, solo con un Gateway de pruebas o una ventana de mantenimiento autorizada: conectar Pet, terminar una respuesta sintética, reiniciar el servicio y enviar otra consulta al recuperar la conexión. La CLI local inspeccionada es **2026.9.5** y su ayuda confirma `openclaw gateway restart` para un servicio instalado. No ejecutar ese comando contra el servicio productivo durante tareas activas. Si el Gateway está en otro host, utilizar su gestor instalado; la versión de la CLI local no demuestra la versión de ese proceso. Comprobar estado reconnecting, autenticación recuperada y ausencia de turnos duplicados o runs antiguos que alteren la respuesta nueva. Guardar solo logs sin payloads/secretos.

## 3. Barge-in

Automático actual: `python -m unittest discover -s qa -p test_conversations.py` y pruebas `audio.test.ts` de Pet verifican cancelación manual y reproducción con dobles.

Manual con micrófono explícitamente activado: pedir una respuesta larga y, mientras se reproduce, decir «Espera; cambia la consulta». Esperado final: cortar generación/audio y atender la nueva petición. **Capacidad pendiente**: los pipelines actuales cierran/pausan captura durante respuesta. Que funcione el botón de cancelar no aprueba barge-in. No registrar latencias de interrupción como si esta capacidad existiera.

## 4. Micrófono desconectado y competencia

Automático: `python -m unittest discover -s qa -p test_voice_recovery.py`; Pet `npm test -- tests/wake-recovery.test.ts tests/core-resource.test.ts tests/microphone.test.ts`. El primer grupo simula audio; el arbitraje usa procesos y locks reales. `node scripts/core-resource-smoke.cjs` verifica IPC nativo sin abrir audio.

Manual: activar escucha en una interfaz. Intentar escuchar desde la otra: debe indicar ocupación y no capturar simultáneamente. Detener la primera y reactivar la segunda. Para recuperación física, desconectar y conectar el micrófono elegido, sin enviar datos privados. Observar error visible, liberación y recuperación del predeterminado; una selección explícita no debe cambiar silenciosamente a otro dispositivo. Probar wake y dictado por separado. Repetir después de cerrar una interfaz inesperadamente. No borrar el archivo de lock para forzar el resultado.

## 5. Conversación anterior y preferencia

Automático: `python -m unittest discover -s qa -p test_memory.py` y `python qa/verify_core_interop.py`.

Manual sobre Core temporal: crear el chat sintético del escenario 1. Guardar `python memory_cli.py add Prueba 'Prefiere respuestas breves en esta prueba'`, cerrar clientes, reabrir con la misma base, listar mediante `python memory_cli.py list Prueba` y recuperar el chat. Probar edición/exportación/borrado con `memory_cli.py --help` y `chat_cli.py --help`. Preparar transferencia con `/memoria preparar Prueba | breves`, revisar y autorizar `/memoria enviar` solo hacia el modelo de pruebas. El CRUD explícito no aprueba recuperación contextual autónoma.

## 6. Tarea de varios pasos

Automático: `python -m unittest discover -s qa -p test_tasks.py`. Comprueba plan, orden, permisos, resultados e idempotencia con handlers simulados. `test_task_tools.py` valida los adaptadores Windows con respuestas simuladas.

Real de lectura: `/tareas informe pc`; conservar el ID y consultar `/tareas estado ID`. Comparar CPU, RAM y disco con una lectura independiente cercana en el tiempo. Deben existir tres pasos terminados y ningún paso de escritura. Este plan fijo no valida planificación autónoma del LLM.

Interfaz compartida: con las dos rutas Core/tareas configuradas, usar el mismo `/tareas estado ID` en Pet; comparar ID, cursor y estados. `node scripts/core-tasks-smoke.cjs` verifica en Electron real pending/running/completed de una herramienta sintética ejecutada por Python. Sigue siendo una simulación de la herramienta, aunque los procesos, la UI y SQLite sean reales. La consulta funciona sin Gateway y no autoriza escrituras desde Pet.

## 7. Denegación privilegiada

Automático: `python -m unittest discover -s qa -p test_tasks.py` y `test_admin_runtime.py`, en particular casos de denegación y cancelación durante aprobación. Los handlers de prueba deben registrar **cero invocaciones**. No utilizar una acción destructiva real para demostrarlo. El smoke nativo también comprueba que otro renderer no puede liberar un ticket ajeno de micrófono.

## 8. Cancelación segura

Automático: suite `test_tasks.py`, con lectura cooperativa, escritura en curso y timeout. Verificar que no arranca el siguiente paso y que una escritura con efecto desconocido permanece uncertain.

Manual de lectura: iniciar `/tareas informe pc` y pulsar Cancelar tarea si aún está activo. Si termina antes, registrar «no se alcanzó la ventana de cancelación», no aprobado. No ralentizar ni bloquear servicios productivos para alargar la tarea.

## 9. Recuperación de tareas

Automático: suite `test_tasks.py`, especialmente procesos terminados y segundo ejecutor concurrente; usa bases temporales y herramientas simuladas. Consultar estados tras abrir otra instancia de `TaskEngine`. Una lectura abandonada debe quedar interrupted; escritura sin verificación, uncertain; ninguna se reejecuta automáticamente. La reanudación autónoma completa continúa pendiente porque los argumentos no se guardan.

## 10. Ventana o captura seleccionada

Automático: `python -m unittest discover -s qa -p test_windows_context.py`; Pet `npm test -- tests/perception.test.ts tests/pointing.test.ts`.

Manual: abrir una ventana con un error sintético, sin datos personales. Para metadatos clásicos, usar `/ventana activa` por voz conservando el foco en la ventana objetivo y confirmar título/proceso. No afirmar OCR o comprensión visual a partir del título. Para Pet, seleccionar explícitamente una ventana de prueba en Percepción y revisar la captura antes de enviarla a un modelo visual autorizado. Registrar proveedor, consentimiento y resultado. No capturar permanentemente el escritorio ni incluir campos privados.

## 11. Sensores y servicios

Automático: suites Python `test_task_tools.py`, `test_proxmox_status.py`, `test_ha_control.py`, con respuestas simuladas.

Real: escenario 6 para Windows; `/proxmox nodo NOMBRE` o `/casa entidades` solo en una instalación de pruebas con credenciales propias y permisos de lectura. Comparar con API/panel real y registrar la hora. Un error o campo ausente debe mostrarse como desconocido/fallido. CPU/RAM/disco no aprueban temperatura CPU, potencia GPU ni servicios de todo el laboratorio.

## 12. Regla de alerta

Automático: `python -m unittest discover -s qa -p test_alerts.py` y `test_alert_monitor.py`. Verifica umbral, muestra fresca, deduplicación, desactivación y reinicio con datos simulados.

Manual: en un almacén de pruebas, configurar una regla de lectura del monitor y ejecutar una muestra real. Comprobar regla, valor, fecha e historial, y que repetir la misma condición no duplica la alerta. No llenar discos ni detener Jellyfin para dispararla. El monitor actual no ejecuta cadenas generales de acciones; esa aceptación sigue pendiente.

## 13. Autenticación remota

Automático: `python -m unittest discover -s qa -p test_core_local_api.py` y Pet `npm test -- tests/server.test.ts`. Se comprueban HTTP local real, token incorrecto, revocación y scope limitado. No son pruebas de Tailscale.

Manual remota: pendiente hasta disponer de transporte seguro, cuentas/dispositivos y política de acceso. No cambiar Core a `0.0.0.0`, abrir puertos del router o incrustar tokens para completar este escenario. Un teléfono que solo muestra una página no demuestra continuidad de tareas o aprobaciones seguras.

## 14. Proveedor desconectado

Automático: suites `test_conversations.py` y `gateway.test.ts`, con fallos controlados y servidores de contrato.

Manual: utilizar un proveedor local de pruebas; terminar/cancelar la consulta anterior, detener ese proveedor, consultar, comprobar error visible y ausencia de respuesta ficticia; reiniciar el proveedor y repetir. Verificar que el historial no contiene un éxito inventado ni turnos duplicados. No detener un proveedor o Gateway compartido con otros usuarios sin mantenimiento autorizado.

## 15. Migración y reversión

Automático: suites `test_core_contract.py`, `test_core_events.py`, `test_maintenance.py` y Pet `core-store.test.ts`. Comprueban datos previos, esquema incompatible, WAL activo, hash de respaldo y rechazo de corrupción.

Manual: copiar mediante `maintenance.py` con clientes detenidos, verificar, abrir una **copia** del SQLite de pruebas con el nuevo código y comparar chats/preferencias/recuerdos. Probar regreso al código previo conservando el esquema v1 adicional. Seguir el manual de reversión del informe. No usar los datos personales como primera prueba de una migración.

## 16. Recursos y estabilidad Windows

Automático medible: `python qa/measure_core.py --runs 100 --output 'tmp\core-medidas.json'`, con `tmp` existente. Registrar Windows, intérprete y carga concurrente. No llamar a estos resultados latencia STT/LLM/TTS.

Para el bloqueo de historial: `python qa/measure_core_ui.py --output 'tmp\core-ui-medidas.json'`. Abre una ventana Tk con datos temporales, la oculta, bloquea SQLite de forma real y mide temporizadores, entrega del error y recuperación. No consulta proveedores ni graba audio. Las pruebas `test_core_archive.py` verifican además cola limitada, cierre, snapshots antiguos, creación atómica y ausencia de consultas de archivo desde el hilo Tk.

Manual: mantener cada interfaz en reposo y ambas juntas, luego realizar una conversación sintética y una tarea de lectura. Medir CPU/RAM de sus procesos y consumo de GPU con herramientas del equipo, en intervalos comparables. Repetir con voz desactivada, voz local y equipo sin GPU; guardar duración y condiciones. Ejecutar sesiones prolongadas, suspensión/reanudación y reconexión. Falta completar este ensayo y añadir medición separada de detección, transcripción, primer token y primer audio. Registrar fallos y límites, incluso con suites automatizadas verdes.
