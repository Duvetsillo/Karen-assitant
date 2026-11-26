# Cambios

## 2026-11-26

### Triggers y condiciones

- Scheduler READ por eventos con filtros exactos, cooldown, pendientes persistentes
  y supresión de bucles entre herramientas programadas.
- Quiet hours persistentes y predicados finitos de modos, fechas y recursos medidos.
- Se preserva una pausa concurrente al terminar y se evita que diez tareas aplazadas
  impidan ejecutar otras. Políticas inválidas no se modifican durante simulación.
- Python 413 pruebas correctas; Pet 166, typecheck, build e interoperabilidad correctos.
- Instrucción permanente: commits y push tras cada incremento verificado.

### Importación portable y metadatos de clientes

- Importación revisada por hash y proyecto, estado pendiente, rollback atómico,
  procedencia reportada conservada y promoción explícita por recuerdo.
- Duplicados locales intactos; caducidad y sensibilidad conservadas. Las relaciones
  declaradas no se activan y los procedimientos no obtienen evidencia de ejecución.
- Se impide que detalles de un procedimiento sustituyan ID, estado o verificación local.
- Core API/móvil consultan metadatos autenticados de automatización y desarrollo.
  Pet ofrece consultas offline equivalentes sin transferirlas a OpenClaw ni TTS.
- Prueba cruzada Python/SQLite/Node compilado correcta. Python: 400 pruebas;
  Pet: 166 pruebas, typecheck y build. Ejecutable instalado conservado.

### Reanudación de las 05:32

- Obsidian: mover, renombrar, eliminar con backup, apertura por URI y edición de
  propiedades, etiquetas y tareas. Confirmación destructiva ligada a plan y paso.
- Cola de inferencia priorizada, rechazo de presupuestos RAM desconocidos y
  cancelación de streams GPU activos al entrar en gaming. Verificación Ollama real.
- Eventos de memoria emitidos después de confirmar SQLite.
- Scheduler READ optativo, persistente, con simulación, historial, reintentos,
  idempotencia y recuperación tras caída real de un proceso hijo de prueba.
- 376 pruebas Python correctas; 28 verificaciones posteriores dirigidas correctas.
- Memoria: tipos user/autobiographical/prospective, FTS5 compatible con clientes
  antiguos, ranking acotado y último acceso persistente. Credenciales rechazadas en MemoryStore.
- Conversación: intenciones y memoria explícita en español; lectura y escritura
  documental determinista con permisos existentes. Prueba sintética de recuperación en 5,613 ms.
- Seguridad: corrección de redacción incompleta de encabezados Bearer, cobertura
  de claves privadas y rechazo de asignaciones de contraseñas en español.
- Cierre de la reanudación: 387 pruebas Python correctas en 67,457 s; checkpoint
  actualizado para continuar importación, clientes y automatización avanzada.

- Auditoría incremental del stack real, capacidades, Git, pruebas y recursos.
- Reutilizados los módulos previos sin seguimiento `events.py` y `obsidian.py`.
  Se preservó `ollama-openclaw.Modelfile` sin cambios y fuera de esta entrega.
- Integración Obsidian con CoreRuntime, planes aprobados, comandos locales y CLI.
- Corrección de pérdida de espacios/saltos de línea en lectura para edición Markdown.
- Validación documental antes de almacenar planes y degradación ante configuración inválida.
- Journal JSONL rotativo de eventos sin contenido privado.
- Gaming compartido limita nuevas inferencias a CPU.
- Handoffs persistentes y cifrados para colaboración con Codex, sin acceso a sesiones privadas.
- Pruebas de filesystem/SQLite reales, regresión y aceptación Ollama con datos sintéticos.

Historial anterior: [KAREN_PROGRESS](../KAREN_PROGRESS.md) y documentos Core 2 existentes.
