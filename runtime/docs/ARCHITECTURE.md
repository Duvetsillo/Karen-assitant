# Arquitectura actual

Monolito modular Python, con clientes Tkinter y móvil. Pet conserva Electron/React
y su repositorio separado. La arquitectura detallada existente continúa en
[KAREN_CORE_2.md](KAREN_CORE_2.md); no se ha migrado a Node ni creado otro servidor.

`CoreRuntime` reúne memoria, conocimiento, modelos, planes, roles, diagnóstico,
percepción, Obsidian, eventos y handoffs. `Plans` valida herramientas del registro
y delega en `TaskEngine`; el modelo nunca asigna permisos.

SQLite Core conserva memoria, conocimiento y handoffs. SQLite de tareas conserva
planes y estados existentes. Obsidian mantiene documentos compartidos; su SQLite
FTS5 es reconstruible y está fuera del vault. El journal JSONL solo recibe eventos
validados, sin contenido de notas o conversaciones. No es una cola persistente.

El router lee `core.mode` del mismo archivo Core. Gaming impide nuevas asignaciones
GPU y cancela streams GPU activos; todos los requests usan `keep_alive: 0`.
InferenceQueue limita y prioriza solicitudes dentro del router; el lease del SO
conserva la exclusión entre procesos cooperantes. No cambia procesos externos.

Configuración: identidad y personalidad existentes; credenciales DPAPI existentes;
Obsidian en `obsidian.json` junto al SQLite Core o variables de entorno.
Los índices y backups Obsidian no se sincronizan dentro de la bóveda.

Los handoffs usan una extensión de esquema versión 1 dentro del SQLite Core y
payload DPAPI. Su JSON puede consultarse mediante CLI; no leen sesiones privadas
de Codex, no ejecutan cambios y no certifican resultados externos automáticamente.

Automations vive dentro del runtime y usa Plans/TaskEngine existentes. Guarda
recetas cifradas y ocurrencias en la base de tareas. Solo READ puede programarse;
el runner de 30 segundos es optativo. Recupera lecturas tras una caída y agrupa
vencimientos atrasados. No se instala un servicio de Windows.

ContextMemory añade una migración `memory_retrieval_version=1`, FTS5 y metadatos
de acceso. Los triggers mantienen el índice al escribir desde clientes antiguos.
El ranking recibe candidatos pertinentes del proyecto, no toda la base de memoria.
Cognition reconoce intenciones y comandos deterministas del usuario. Documentos
recuperados nunca pasan por ese despacho ni generan permisos.

MemoryPortability añade `memory_import_version=1` y conserva procedencia en una
tabla separada. Importar crea memorias pendientes en una transacción; revisar
requiere hash vigente de cada recuerdo. La evidencia externa nunca entra en la
tabla de ejecuciones locales. Los recibos de procedimiento conservan campos
autoritativos calculados por código.

Core API y móvil comparten un lector SQLite ro de metadatos. Pet utiliza sus
adaptadores existentes con versiones y campos compatibles; no necesita otro
servicio ni Gateway para esas consultas. Contrato en CLIENT_METADATA.md.
