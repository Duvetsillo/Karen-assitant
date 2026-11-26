# Automatizaciones locales

`Automations` utiliza Plans y su SQLite existente. No crea servicios del sistema,
procesos de agentes, acceso a shell ni modelos adicionales. El runner automático
está apagado por defecto. `KAREN_AUTOMATION_ENABLED=true` activa un hilo dentro
del runtime, que comprueba vencimientos cada 30 segundos mientras Karen está abierta.
La respuesta al crear una tarea indica `runner_active`.

Ejecuta `python -m karen_core2 automation list` para consultar el estado guardado;
`history` muestra hasta 100 ocurrencias y su plan, intento y resultado.
`tick` ejecuta hasta 10 ocurrencias vencidas. `tick --args '{"dry_run":true}'`
muestra las acciones previstas sin consumir la ocurrencia ni ejecutarla.
Clásica acepta los mismos comandos con `/automation`.

`create --args JSON` admite name, recipe, due_at y opcionalmente interval_seconds
y retries. due_at debe incluir zona horaria. Intervalo: 60 a 31.536.000 segundos;
reintentos: 0 a 2. Una receta tiene el mismo esquema goal/steps del planificador:

```json
{
  "name": "Consultar RAM",
  "due_at": "2026-12-01T10:00:00-04:00",
  "recipe": {
    "goal": "Medir RAM local",
    "steps": [
      {"id": "ram", "label": "Leer RAM", "tool": "memory_sample", "args": {}, "depends": []}
    ]
  }
}
```

Solo se programan herramientas que el registro de código clasifica READ. Antes de
ejecutar se vuelven a comprobar permisos y esquemas; cambios de permisos bloquean
la tarea. `simulate --args '{"recipe":...}'` también valida propuestas de escritura
sin ejecutarlas ni programarlas. Las escrituras conservan aprobación interactiva
por paso del motor de planes. No hay autorización global persistida para ellas.

`enable --args '{"id":"ID","enabled":false}'` pausa una tarea y solicita cancelar
su plan activo en esta instancia. El cierre cancela el trabajo propio; un cierre
inesperado conserva la ocurrencia y permite recuperar lecturas interrumpidas.
Una cancelación explícita de una tarea de una sola ejecución la deja detenida.

El payload está cifrado con DPAPI. Un lock del SO evita dos runners sobre la misma
base. La clave schedule/fecha/intento evita crear planes duplicados al reiniciar.
Los intervalos atrasados se agrupan en una sola ejecución y después avanzan al futuro.
Hasta 100 tareas guardadas y 1.000 ocurrencias retenidas. El scheduler ofrece hasta
tres intentos; cada plan conserva sus dos intentos máximos por lectura fallida.

## Condiciones y horas de silencio

Create admite `conditions`: weekdays (0 lunes a 6 domingo), allowed_modes
(normal/do_not_disturb), window (start/end y offset_minutes opcional),
min_ram_available_mib, min_vram_available_mib y max_cpu_percent.
Todos los predicados se combinan con AND; no hay expresiones ni código evaluable.
Un sensor ausente, inválido o un presupuesto insuficiente aplaza la ocurrencia.
Los sensores se consultan solo cuando se necesitan; las muestras del batch se
renuevan tras un segundo. Gaming siempre aplaza el trabajo.

`quiet --args '{"start":"22:00","end":"07:00","offset_minutes":-240}'`
guarda horas de silencio, incluso cruzando medianoche. `quiet` sin parámetros
las elimina. Sin offset se usa la zona local de Windows; un offset explícito
es fijo y no aplica DST. Inicio y fin iguales se rechazan. La misma lógica de
horarios del monitor de alertas se reutiliza sin cambiar sus ajustes independientes.

Quiet hours y modo se comprueban entre planes. No se cancela retroactivamente
una lectura que empezó antes del silencio. Se examinan hasta 100 tareas, con un
máximo de diez intentos de plan por tick; tareas aplazadas no bloquean a las siguientes.
Finalizar un plan conserva una deshabilitación concurrente del usuario.

## Triggers de eventos

Create puede sustituir due_at por `event`:

```json
{
  "topic": "obsidian.index.updated",
  "cooldown_seconds": 60
}
```

También admite code/entity_id opcionales como filtros exactos. Puede usar due_at
como fecha mínima de aceptación; event e interval_seconds no se combinan.
Lista permitida: memory.conflict, obsidian.note.changed, obsidian.index.updated,
resource.pressure y gaming.ended. Las escrituras directas y los cambios de índice
de Obsidian ya tienen productores; no se presume un detector automático de juegos
ni otro productor de recursos solo porque el tópico esté registrado.

El runner escucha el EventBus de su proceso al iniciarse; se eliminan suscripciones
al cerrar y no se duplican al iniciar dos veces. El registro de eventos no es una
cola retroactiva: solo se capturan mientras existe un listener autorizado activo.
No se leen eventos de otros procesos o de un log para ejecutar instrucciones.

Se conserva una ocurrencia pendiente por tarea; eventos nuevos se agrupan. Hay
cooldown de 60 a 86.400 segundos y deduplicación persistente de hasta 1.000 pares
tarea/evento. Los pendientes sobreviven al reinicio y esperan a salir de quiet
hours o a cumplir condiciones. Para tareas de evento, next_run expresa la próxima
fecha de aceptación, no una ejecución incondicional. Policy devuelve configuración
y estado pendiente para revisión local.

Los eventos recibidos durante ejecuciones programadas se omiten, incluidos los de
otros runners de la misma base, para impedir bucles y cadenas entre herramientas.
Este límite también puede omitir un evento externo coincidente; no hay promesa de
entrega exactamente una vez de todos los eventos del sistema.

La migración aditiva automation_policy_version=1 conserva tablas y contratos de
metadatos anteriores. Reinicia los runtimes antiguos antes de utilizar políticas
nuevas; un proceso que conserve código anterior en memoria no interpreta esas reglas.
Runner apagado y cero tareas creadas en la base privada real durante las pruebas.

Pruebas: `python -m unittest qa.test_automation`. Incluyen SQLite y locks reales,
caída real de un proceso hijo de prueba, recuperación sin duplicación, cambio de
permisos, aplazamiento gaming y una medición real de RAM de Windows.
