# Checkpoint de desarrollo — 2026-11-26

## Experience Update 1.9.0 — entrega 2026-11-26

Pet siempre flotante sin extremidades, Presencia y centro de control, treinta
estados, saludos configurables, cápsula musical, router que reutiliza LocalModels
y contexto Windows optativo con permisos separados. Commits fed51db, ab3bdaf,
9643dbb, dc7d9ca y 5ce2a22 publicados. Paquete 1.9.0 instalado, acceso directo
verificado y proceso normal abierto con qwen3:4b local/manual. No se habilitó voz,
observación, herramientas ni scheduler. 425 runtime, 236 Pet, 26 voz, cuatro legacy,
tres interoperabilidades y aceptación Core temporal correctos. Ver
../../pet/docs/EXPERIENCE_UPDATE.md y JSON de aceptación para medidas y límites;
no declarar voz física, topmost o pantalla completa certificados.

## Destino canónico e interfaz — 2026-11-26

Trabajar y publicar en `C:/Users/Dayve/Documents/GitHub/Karen-assitant`, rama main.
Core está en runtime/ y Pet en pet/. Integraciones `65f9c28` y `8dfa530` publicadas;
se conservaron voz/presets propios de Pet y personal_learning.py del runtime.
425 pruebas Python y tres interoperabilidades reales con datos temporales correctas.
Interfaz: navegación/búsqueda, conversación completa y opciones de inicio/música
organizadas; 210 pruebas Pet, build y QA de diez secciones en dos tamaños correctos.
Ver ../../KAREN_PROGRESS.md y ../../pet/docs/INTERFACE_ACCEPTANCE_2026-11-26.json.
C:/karen y su Pet separado son fuentes históricas, no destinos de nuevas entregas.
La instalación y los datos privados permanecen intactos. Audición/HiDPI físico pendiente.

## Introducciones y chat — 2026-11-26

Pet: nitidez adaptada a pantalla/DPI, ojos de Awakening a 8× en 1080p,
regreso con fotograma de escritorio preparado y saludo sincronizado al reloj de
audio/dispositivo de salida. Despedida nativa de 780 ms con fallback de 1200 ms,
reducción de movimiento y omisión en sesión bloqueada/mascota oculta. Tres formas
de respuesta (Globo/Panel/Cinta), editor multilínea con borrador conservado,
barra reducida y Más opciones; lectura de historial sin desplazamiento forzado.
Se conservan las ocho apariencias y los permisos existentes.

Verificado: 197 pruebas Pet, typecheck, Vite y compilación Electron; 54 secuencias
nativas (6 con audio real local y 48 visuales aceleradas), 58–59 FPS, cero errores.
QA adicional con datos sintéticos: seis variantes de chat, teclado, persistencia,
calidad 8× y cierre ~961 ms. Se reutilizó el helper musical compilado para conservar
abierta la instancia anterior. Aceptación humana de saludo/despedida y monitores
físicos 4K/HiDPI pendiente. No se sustituyó el ejecutable instalado ni se repitieron
las 416 pruebas Python: el Core no cambió funcionalmente. Evidencia y límites en
`desktop-pet/docs/STARTUP_INTROS.md` y `POLISH_ACCEPTANCE_2026-11-26.json`.

Commits Pet publicados: `0cab30c` (implementación) y `f9d0f24` de
aceptación/documentación; rama `codex/karen-core-2`. No se publicó información
musical personal. Conservar `ollama-openclaw.Modelfile` sin agregar a Git.


## Solicitud actual: Music Presence

Comprobación posterior con Spotify Desktop real: GSMTC, clasificación y minirreproductor
correctos, incluida portada y metadatos. Perfil temporal sin historial/comentarios/voz,
sin Core y cero órdenes de reproducción; no se guardaron pistas personales en Git.
Prueba reproducible: `desktop-pet/scripts/music-spotify-live.cjs`. Los controles
de Spotify real y el resto de plataformas continúan sin certificarse. El ejecutable
instalado no se reemplazó. La continuidad tras cuota se gestiona en Codex, fuera del repo.

Pet: `4a0cb43` y `ce01fc0` publicados, puente C#/.NET Framework de Windows con GSMTC por eventos,
clasificador estricto, transporte local autenticado y política de comentarios.
Controles reales play/pause/next/previous comprobados contra una sesión sintética
silenciada de Windows MediaPlayer; esto no certifica Spotify/Apple/YouTube reales.
Python: lector `ContextMemory.music` sobre la base Core existente, sin promover
observaciones a recuerdos confirmados. `music_summary` READ disponible para Plans
y scheduler existente, con receta temporal verificada. 416 pruebas Python y
verificación real de SQLite Node/Python correctas. Pet: 190 pruebas y build completo
correctos. UI/HTTP local real con metadatos de navegador sintéticos pasa controles,
varias sesiones, filtros, historial y borrado. Extensión limitada a cinco sitios,
pairing local en loopback 18796; no instalada en Chrome/Edge del usuario.
Seis comentarios locales pregenerados y copiados fuera de Git; audio reutiliza el
pipeline actual sin TTS para estos clips. Medidas en
`desktop-pet/docs/MUSIC_METRICS_2026-11-26.json`: Electron total 619,90–624,86 MiB,
CPU media/pico 3,024/7,836 %; helper 39,06–40,75 MiB, 0,31 % de un núcleo en reposo.
GPU global compartida 32–38 %, no atribuible al módulo. Ver MUSIC_PRESENCE.md.
Percepción, historial y comentarios apagados por defecto. Sin modelos ni runner nuevo.
Pendiente: cuentas reales de Spotify/Apple/YT, llamadas y juegos/presentaciones
reales, audición humana, escritura periódica Obsidian configurada y pruebas prolongadas.
No se reemplazó el ejecutable instalado ni se cambió el modo real del usuario.

## Solicitud actual: introducciones de inicio

Motor implementado en el repositorio separado `desktop-pet`, rama
`codex/karen-core-2`; incrementos `7f61389` y `47d0109` publicados. Ver
`desktop-pet/docs/STARTUP_INTROS.md` para arquitectura y aceptación.
Se conservan los ocho estilos y el Core Python; no se cambiaron memoria ni voz.
Seis coreografías Pixi, superficie independiente sin foco/clics, guardia Windows,
preferencias persistentes en Apariencia y cinco órdenes deterministas sin Gateway.
40 saludos generados con el perfil local configurado, envolventes RMS de 20 ms;
archivos privados fuera de Git en `.private/startup-greetings` y copia local en
`%APPDATA%/karen-desktop-pet/startup-greetings`. Nunca hay TTS durante la entrada.
179 pruebas Pet y build/typecheck correctos. Matriz nativa de 48 combinaciones y
seis reproducciones a tiempo real; Escape entregado por Playwright, persistencia
tras reinicio, IPC y bloqueo en modo gaming verificados. Pasada final: 54 entradas,
cero errores, con liberación explícita de Pixi antes del cierre normal. FPS reales:
58–59 a 1080p. CPU media/pico 3,996/9,071 %; working sets de toda la instancia QA
305,39–812,44 MiB. GPU global compartida 4–44 %, sin atribución exclusiva al Pet.
Informe: `desktop-pet/docs/STARTUP_INTRO_METRICS_2026-11-26.json`.
No se reemplazó el ejecutable instalado. Faltan aceptación visual/auditiva humana,
Escape físico y juegos, presentaciones y monitores/DPI físicos distintos.
La directiva anterior de Core mantiene sus pendientes independientes.

## Continuidad

Última fase totalmente cerrada: fase 0. Incrementos de fases 1, 2 y 5 implementados;
la directiva completa sigue pendiente. No repetir la auditoría general.

Rama: `codex/personal-ai-upgrade`. Remote: `origin`, karen-classic-core.
Base anterior: `1ced62b`. Reanudación: `95f4ceb`, `0008b35`, `74641fa`,
`53bae0a` y `6df097b`, con 387 pruebas correctas.
Continuación manual: Core `22bb19d`; Pet `5ce738d` en su rama
`codex/karen-core-2`. Python 400 pruebas; Pet 166, typecheck y build correctos.
El usuario autorizó commits, push e inicio de Ollama para pruebas locales.
No comprar créditos, usar APIs de pago, canjear reinicios ni desplegar Proxmox.

Incremento actual cerrado: triggers acotados, condiciones y horas de silencio del
scheduler READ. Core `16464cd`; Pet `0245bbb`. Incluye deduplicación persistente,
cooldown, aplazamiento por recursos desconocidos y conservación de pausas concurrentes.
No se activó el runner ni se crearon tareas reales. Ver AUTOMATION.md.
Próxima tarea: alcances documentales por cliente; después interfaz móvil de metadatos
y productores automáticos de recursos/gaming. Aceptación física de voz pendiente.

## Archivos relevantes y decisiones

- `karen_core2/runtime.py`: fachada, comandos y eventos; conserva clientes existentes.
- `obsidian.py` y `events.py`: código previo sin seguimiento, reutilizado y probado.
  Modificaciones Obsidian: preservar Markdown y prevalidar antes de persistir planes.
- `obsidian_bridge.py`: configuración explícita y adaptadores del registro.
- `event_journal.py`: solo metadatos validados, rotación acotada.
- `models.py`: modo gaming compartido limita nuevas asignaciones GPU.
- `inference_queue.py`: cola acotada y priorizada dentro del router. `models.py`
  cancela streams GPU al entrar en gaming y rechaza presupuestos RAM desconocidos.
- `markdown_edits.py`: propiedades simples YAML, tags y casillas; conserva cuerpo,
  BOM y CRLF. Obsidian añade move/rename/delete/open con permisos y backups.
- `automation.py`: scheduler READ sobre Plans; apagado por defecto. Recetas cifradas,
  intervalos, simulación, historial y recuperación de lecturas tras caída de proceso.
- `automation_policy.py`: predicados permitidos, ventana local o con offset fijo,
  días, modo y métricas. Migración aditiva automation_policy_version=1.
  Eventos del propio trabajo programado se suprimen mientras un plan está en ejecución;
  pueden perderse eventos externos coincidentes. No hay replay ni bus entre procesos.
- `memory.py`: tipos user/autobiographical/prospective, FTS5 y último acceso.
  `memory_retrieval_version=1` es una migración aditiva con triggers para clientes antiguos.
- `cognition.py`: memoria explícita y notas en español sin inferencia innecesaria.
- `memory_portability.py`: preview/apply por hash, promoción explícita por recuerdo,
  procedencia reportada separada y rollback SQLite. Migración memory_import_version=1.
- `api.py` y `core_local_api.py`: schedules/handoffs, solo metadatos con core.read.
  `mobile_server.py` reutiliza esas lecturas con su archivo de tareas correcto.
- Pet: `electron/core-tasks.ts`, `core-store.ts`, `gateway.ts` y shared/local-commands.ts;
  comandos offline `/automatizaciones listar` y `/desarrollo listar`. No reemplaza el
  ejecutable 1.8.1 instalado desde otro checkout.
- `privacy.py`: redacción completa de encabezados Bearer, claves privadas y
  asignaciones de contraseñas en español; pruebas solo con marcadores sintéticos.
- `handoff.py`: solicitudes cifradas en Core SQLite, JSON, hash optimista y datos reportados.
- `.private/obsidian.json`: configuración local no publicada; no reescribir si existe.
- `ollama-openclaw.Modelfile`: archivo previo ajeno a la entrega, conservar sin cambios.

## Pruebas y medidas

Base Python 337/337; Pet 163/163 y typecheck correctos.
Entrega anterior: Python 355/355 en 61,749 s. Reanudación: 387/387 en 67,457 s.
Filesystem/FTS5, handoff, scheduler, restauración, inicio Tk y compatibilidad correctos.
La recuperación del scheduler se probó cerrando abruptamente un proceso hijo
sintético y retomando el mismo plan sin duplicarlo. RAM Windows medida realmente.
`compileall` y `git diff --check` correctos. La apertura de Obsidian usa un launcher
simulado en pruebas; su efecto visual no está certificado. No repetirlo sin necesidad.
Continuación manual: 400 pruebas Python correctas en 71,926 s; validación posterior
dirigida de importación/HTTP tras endurecer entradas malformadas. Pet 166 pruebas,
typecheck y build correctos. `qa/verify_metadata_interop.py`: Python crea SQLite y
Node compilado lo consulta; cero planes ejecutados, archivo de tareas intacto y
payloads privados ausentes. No requiere un Gateway real ni toca bases del usuario.
Aceptación real: `python qa/verify_master_live.py`, con datos sintéticos y vault temporal.
Incremento de políticas: 413 pruebas Python correctas en 74,398 s. Tras los ajustes
finales: 22 pruebas de automatización correctas en 3,154 s. Incluyen RAM real y
conflicto de memoria/cambio externo en vault temporal que disparan planes READ.
Presión GPU y carga CPU se simulan en contratos; no prueban detección de videojuegos.
Pet: 166 pruebas en 8,71 s y build/typecheck correctos. Interoperabilidad Python/Node
con event_topic verificada: sin payloads privados, sin planes y SQLite intacto.
Chat CPU gemma3:1b: primer token 4,086 s; total 4,348 s; cancelación real después
del primer fragmento. `/api/ps` vacío después; sin modelos descargados de Internet.
Mediciones: `MASTER_METRICS_2026-11-26.json`.

GPU real qwen3.5:2b: 22 capas solicitadas; `/api/ps` informó 1.904.339.844 bytes
de VRAM. Cancelación después de cambiar a gaming: 0,007 s; modelo descargado al
terminar y cola liberada. `GAMING_METRICS_2026-11-26.json` y verify_foundations_live.py.
Memoria: un resultado pertinente entre 501 registros sintéticos en 0,005613 s,
incluido un recuerdo fuera de los 200 recientes. `MEMORY_METRICS_2026-11-26.json`.

Vault real: solo carpetas Karen autorizadas; 27 notas indexadas, 33 omitidas por
validación, 0,629 s. No se enviaron documentos reales al modelo.

## Bloqueos y pasos siguientes

Voz física/AEC/barge-in requieren aceptación humana. No grabar al usuario dormido.
Siguen pendientes: control documental remoto con alcances por cliente,
interfaz móvil para los nuevos datos y productores automáticos de recursos/gaming.
La importación revisada, políticas del scheduler y metadatos de
móvil/Pet están implementados. Ver ROADMAP y KNOWN_ISSUES. No crear módulos paralelos.
El scheduler real no tiene tareas creadas y su runner permanece apagado por defecto.

Reanudar: revisar Git y documentos cambiados; ejecutar pruebas dirigidas al cambio;
conservar credenciales privadas; usar vault temporal; actualizar este checkpoint,
CURRENT_STATE y memoria Obsidian antes de agotar contexto. Hacer commit y push
solo de archivos revisados; no incluir `.private/` ni el Modelfile previo.

La continuación de este hilo se ejecutó el 2026-11-26 a las 05:32 America/La_Paz.
La misma automatización se actualizó para las 15:42:55 del 2026-11-26, cinco
minutos después del siguiente reset informado por la app. ID:
`retomar-karen-tras-reinicio-del-l-mite`. Conserva el hilo y las instrucciones.
Como quedan objetivos independientes, sigue activa. Al completar la directiva,
eliminarla con automation_update; no comprar créditos ni canjear reinicios.

## Protocolo estructurado Codex Bridge

`python -m karen_core2 handoff list` lista metadatos. `create --args JSON` acepta
project, description, acceptance y opcionalmente priority/context/files.
`read --args '{"identity":"ID"}'` exporta la tarea JSON y su hash.
`update --args JSON` exige id, expected_hash, status, test_results y blockers.
Los mismos comandos existen como `/handoff` en clásica.

Cada tarea contiene ID, proyecto, descripción, prioridad, contexto, criterios de
aceptación, estado, archivos, resultados, fecha y bloqueos. Estados: pending,
active, needs_validation, complete, blocked. Complete exige resultados reportados;
no certifica evidencia externa ni habilita herramientas. Actualizaciones con hash
obsoleto se rechazan. No hay acceso a sesiones privadas ni ejecución autónoma de código.
