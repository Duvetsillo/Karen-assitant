# Estado comprobado — 2026-11-26

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


## Music Presence

Percepción GSMTC por eventos, minirreproductor independiente, comandos deterministas,
gestos silenciosos y seis comentarios pregenerados. Percepción, historial y comentarios
apagados por defecto. Complemento opcional de Chrome/Edge limitado a sitios musicales,
con canal autenticado local. No captura audio ni requiere GPU para clasificar música.
Memoria en Core existente, lector `ContextMemory.music` y herramienta READ `music_summary`
para resúmenes del scheduler; no se activó su runner ni se crearon tareas reales.

416 pruebas Python, 190 Pet y build/typecheck/C# correctos. Interoperabilidad SQLite
Node/Python real con datos temporales. Controles GSMTC verificados sobre MediaPlayer
sintético silenciado; UI/HTTP sobre navegador simulado. No se certifican plataformas
comerciales, llamadas o presentaciones reales por esas pruebas. Sin reemplazo del
ejecutable instalado. Ver `MUSIC_MEMORY.md` y `desktop-pet/docs/MUSIC_PRESENCE.md`.

Aceptación posterior: Spotify Desktop real confirmado en lectura, clasificación y
renderizado del minirreproductor con portada/metadatos. Sin órdenes a Spotify ni
historial real; los controles reales y proveedores web/Apple siguen pendientes.

## Introducciones de inicio de Pet

Implementadas seis entradas usando Electron/React/Pixi y el avatar existente.
Ventana temporal separada, reloj monotónico, expresiones, saludo WAV con envolvente
pregenerada, transición al Pet, cancelación y fallback. Controles en Apariencia,
persistencia y comandos locales sin LLM. 40 saludos locales generados con la voz
original configurada; no se publican audios ni referencias privadas. Ver
`../desktop-pet/docs/STARTUP_INTROS.md`.

179 pruebas Pet y compilación correctas; 48 combinaciones de intro/apariencia más
seis reproducciones a tiempo real verificadas en Electron con perfil temporal.
Persistencia tras reiniciar, IPC aislado, modo gaming y Escape de Playwright correctos.
Aceptación física de voz/tecla y monitores/juegos/presentaciones reales pendiente.
El ejecutable instalado sigue sin reemplazarse. No hubo cambios funcionales de Python.

Fase 0 completada: [auditoría e inventario](MASTER_AUDIT_2026-11-26.md).
Fases 1 y 2: ampliaciones funcionales verificadas; todavía no cumplen toda la directiva.

Se conservaron Python/Tkinter, Pet, modelos locales, memoria, conocimiento, voz,
TaskEngine, Plans, perfiles, permisos, integraciones y mecanismos de backup.
No se cambiaron la interfaz ni los proveedores funcionales.

Cambios de esta entrega:

- Obsidian conectado al registro y a los planes con aprobación por operación.
  CLI, comandos locales y búsqueda determinista en español.
- Watcher de metadatos con debounce, FTS5, hashes, backups, historial y conflictos.
  La lectura conserva espacios y saltos de línea para evitar alterar Markdown al editar.
- Validación de ruta y credenciales antes de persistir un plan documental.
  Configuración inválida deshabilita Obsidian sin impedir el inicio del núcleo.
- EventBus conectado a conversaciones, tareas y Obsidian; journal rotativo acotado.
- El router respeta el modo gaming compartido al asignar nuevas inferencias.
- Protocolo Codex Bridge con handoffs cifrados, criterios, pruebas, bloqueos,
  estado persistente y hashes para rechazar actualizaciones obsoletas.

Configuración local creada fuera de Git: `.private/obsidian.json`, limitada a
`Karen Asistant/Desktop Pet` y `00_Sistema/Proyectos/karen` dentro del vault existente.
Indexación real: 27 notas aceptadas, 33 omitidas por validación, 0,629 s.
No se indexó toda la bóveda ni se modificaron plugins.

Pruebas base: Python 337 correctas en 60,426 s; Pet 163 en 8,67 s.
Regresión final: Python 355 correctas en 61,749 s; incluye inicio Tk real,
permisos, memoria, restauración con handoffs y compatibilidad existente.
Pet typecheck correcto. Aceptación real: respuesta y stream cancelable con
`gemma3:1b`, CPU en gaming, plan de nota temporal y modelos descargados al terminar.
Primer token 4,086 s, respuesta 4,348 s. [Mediciones](MASTER_METRICS_2026-11-26.json).

## Reanudación automática de las 05:32

Obsidian añade move/rename/delete, apertura por URI y edición estructurada de
propiedades YAML, etiquetas y casillas Markdown. Las escrituras conservan hashes,
backups y aprobación por paso. Delete exige confirmación del plan y paso exactos.
La apertura solo confirma solicitud al sistema operativo; no se abrió Obsidian
durante las pruebas. YAML complejo exige edición completa revisada.

El router dispone de cola acotada con prioridades dentro del proceso. RAM
desconocida bloquea nuevas cargas. Entrar en gaming cancela streams GPU activos.
Prueba real qwen3.5:2b: Ollama informó 1.904.339.844 bytes de VRAM durante la
generación; cancelación tras el cambio: 0,007 s. Al terminar, ningún modelo cargado.
Medidas: [GAMING_METRICS_2026-11-26.json](GAMING_METRICS_2026-11-26.json).

Scheduler persistente dentro del runtime, optativo y limitado a herramientas READ.
Incluye una fecha o intervalo, reintentos acotados, simulación, historial,
idempotencia y recuperación de lecturas tras caída real de un proceso hijo de prueba.
No se crearon automatizaciones en la base real. [Uso y límites](AUTOMATION.md).
Se añadieron eventos de memoria después del commit SQLite.

Regresión de esta ampliación: 376 pruebas Python correctas en 64,379 s.
Validación posterior dirigida a scheduler/móvil/Tk: 28 correctas en 13,365 s.
Pet conserva la verificación previa; su código no se modificó en esta reanudación.

## Memoria y conversación determinista

Se añadieron memoria de usuario, autobiográfica y prospectiva, conservando los
tipos previos. La memoria de trabajo sigue en el contexto acotado de conversación.
Recuperación FTS5 en todo el proyecto, con hasta 200 candidatos pertinentes antes
del ranking y hasta 20 resultados. Cambios de clientes antiguos actualizan el índice
mediante triggers SQLite; los recuerdos sensibles quedan fuera del índice.
Cada recuperación registra último acceso y contador. El export incluye esos metadatos.
MemoryStore también rechaza nuevas credenciales incluso en la ruta CLI antigua.

Prueba sintética: un recuerdo relevante entre 501 registros se recuperó en
0,005613 s; el límite anterior de 200 recientes lo excluía. Ver MEMORY_METRICS.
Correcciones explícitas en español retiran el recuerdo anterior y sobreviven al
reinicio. Intenciones deterministas no necesitan un modelo disponible.
La creación y ampliación de notas en lenguaje natural conserva aprobación por paso.

Regresión final de la reanudación: **387 pruebas Python correctas en 67,457 s**.
Incluye corrección de redacción incompleta de encabezados de acceso y rechazo
de nuevas asignaciones de contraseñas en español. `compileall` correcto.

## Importación portable y clientes

Importación memory-engine-1 con preview, hash ligado al proyecto y transacción
SQLite. Diez pruebas verifican datos pendientes, revisión explícita por recuerdo,
rollback, colisiones sin alterar memoria local y procedencia reportada preservada.
Los procedimientos importados no adquieren evidencia local. Se protegieron sus
campos autoritativos frente a detalles falsificados.

Core API y móvil consultan metadatos de schedules/handoffs con permisos existentes.
Pet añade `/automatizaciones listar` y `/desarrollo listar` offline, sin transferir
datos a OpenClaw, pronunciar resultados ni permitir escrituras. Prueba cruzada
Python/SQLite/Node correcta: archivo de tareas intacto y cero planes ejecutados.
Pet pasa 166 pruebas, typecheck y build. El ejecutable instalado no se reemplazó.
Regresión Python: 400 pruebas correctas en 71,926 s. La última validación de
importación pasó diez pruebas adicionales dirigidas tras endurecer duplicados internos.

## Scheduler por eventos y condiciones

Triggers validados del EventBus, cooldown, deduplicación persistente, una ocurrencia
pendiente por tarea y supresión de eventos durante trabajo programado para evitar
bucles. Horas de silencio persistentes reutilizan la lógica del monitor existente.
Condiciones declarativas de modo, día, ventana, RAM/VRAM y CPU; sin sensores válidos
se aplaza la ejecución. Continúa limitado a READ y apagado por defecto.

Se corrigieron la reactivación de tareas pausadas al completarse un plan y el bloqueo
de tareas ejecutables detrás de diez tareas aplazadas. Dry-run ya no cambia estados
cuando una política está dañada. Pet muestra el tipo de trigger y fecha de aceptación.
Pruebas reales de cambios de memoria e índice de vault temporal disparan lecturas de RAM.
Regresión: 413 pruebas Python correctas en 74,398 s; 22 comprobaciones finales de
política/scheduler correctas. Pet: 166 pruebas, typecheck y build correctos.
Interoperabilidad Python/Node compilado correcta, incluidos metadatos de eventos.

Voz física, AEC/barge-in, productores adicionales de recursos/juegos, interfaz
móvil y gestión documental remota con alcances por cliente siguen pendientes.
La directiva completa continúa parcial. El ejecutable instalado no se reemplazó.
