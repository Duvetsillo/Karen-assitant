# Consultas compartidas de automatización y desarrollo

Core API añade GET `/v1/schedules` y `/v1/handoffs`, con alcance core.read.
Core.status recibe 403; POST no está permitido. Cada consulta abre SQLite en
modo ro, exige versión compatible y limita la salida a 50 filas. Si falta la base,
responde indisponible y no la crea. No descifra payloads ni ejecuta tareas.

Schedules devuelve ID, nombre acotado, vencimiento, intervalo, reintentos,
habilitación y estado. Handoffs devuelve ID, proyecto, estado, prioridad y fecha.
Se excluyen recetas, argumentos, contexto, criterios, resultados y hashes de payload.
Las etiquetas de acceso reconocibles se redactan.
Con automation_policy_version=1 se añade event_topic; next_run indica la fecha de
aceptación del próximo evento para tareas de trigger. Pet lo distingue de una fecha fija.

Móvil expone `/api/core2/schedules`, `/api/core2/handoffs`, `/api/v1/schedules` y
`/api/v1/handoffs`, conservando cookie, host y origen autorizados. Usa el archivo
de tareas de su runtime y evita consultar otro archivo predeterminado del equipo.
Son rutas API de lectura; no se añadieron controles visuales de escritura.

Pet admite `/automatizaciones listar` y `/desarrollo listar` sin Gateway.
Reutiliza KAREN_CORE_DB y KAREN_TASKS_DB con archivos absolutos existentes.
No envía las respuestas a OpenClaw, no las pronuncia ni permite ejecutar o
modificar tareas. El lector de tareas abre readOnly; CoreStore conserva su
escritura anterior de historial. No se ampliaron permisos documentales del vault.

Para usar este Pet desde el checkout: `cd ../pet` y `npm run dev`.
No se reemplazó el ejecutable Pet 1.8.1 instalado desde otro repositorio.

Verificación: HTTP loopback autenticado real y SQLite real desde Vitest.
`python qa/verify_metadata_interop.py` crea SQLite con Python y lo consulta desde
los adaptadores Node compilados; verifica payloads ausentes, archivo de tareas
intacto y cero planes ejecutados. Requiere `npm run build` en ../pet.
