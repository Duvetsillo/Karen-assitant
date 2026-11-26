# Capacidades y evidencia

| Capacidad | Estado | Evidencia/límite |
| --- | --- | --- |
| Chat local y streaming | VERIFIED | Ollama real, gemma3:1b, verify_master_live.py |
| Cancelar inferencia | VERIFIED | Stream real interrumpido tras primer fragmento; no prueba barge-in vocal |
| Identidad y personalidad persistentes | EXISTING | personal_profile.py; regresiones existentes |
| Memoria, correcciones y recuperación | VERIFIED | Suites memory/core2/knowledge y restauración SQLite temporal |
| Memoria tipada y FTS5 | VERIFIED | Tipos user/autobiographical/prospective; recuperación de un recuerdo fuera de los 200 recientes; triggers de clientes antiguos; accesos persistentes |
| Intenciones deterministas en español | VERIFIED | Recuerda, consulta y corrige memoria; busca, lee, crea y añade notas; sin inferencia y con permisos conservados |
| Importación portable | VERIFIED | Preview, hash, transacción, duplicados intactos, estado pendiente y promoción explícita; procedencia reportada conservada |
| Metadatos móvil/Pet | VERIFIED | HTTP autenticado, SQLite real y lectura cruzada desde Node compilado; sin ejecutar ni descifrar tareas |
| Planes, permisos y tareas persistentes | VERIFIED | TaskEngine/Plans; regresiones y plan documental real temporal |
| Obsidian list/search/read/create/update/append/link/daily | VERIFIED | Filesystem y FTS5 reales en test_obsidian.py; validación humana del flujo pendiente |
| Obsidian propiedades/tags/tareas/backlinks | VERIFIED | Edición de propiedades simples, tags YAML y casillas; conserva CRLF/BOM; YAML complejo requiere update revisado |
| Obsidian move/rename/delete | VERIFIED | Archivos temporales reales, colisiones, conflictos, backups y confirmación exacta para eliminar |
| Obsidian open | PARTIAL | URI construida y permiso comprobados; lanzamiento simulado, UI pendiente |
| Watcher y conflictos Obsidian | VERIFIED | Creación, cambio, eliminación externa y hash obsoleto en vault temporal |
| Búsqueda de Obsidian en lenguaje natural | PARTIAL | Regla `busca en obsidian TEXTO`; sin ejecución libre desde LLM |
| Codex Bridge | PARTIAL | Handoffs persistentes cifrados y JSON; sin certificación automática de capacidades |
| Gaming | VERIFIED | Streams GPU se cancelan al cambiar modo; prueba Ollama real con medición de VRAM; requests sin respuesta siguen sujetos al timeout HTTP |
| Cola de inferencia | VERIFIED | Prioridad, límite, timeout y cancelación con hilos reales; prioridades solo dentro del router |
| Eventos y logs | PARTIAL | Conversaciones, planes, Obsidian, memoria y scheduler; otros productores pendientes |
| Voz con interrupción natural/AEC | BLOCKED | Requiere aceptación con micrófono y altavoces reales |
| Automatización persistente común | VERIFIED | READ: fechas/intervalos, triggers locales, cooldown, deduplicación, condiciones, quiet hours y recuperación real; límites en AUTOMATION.md |
| Percepción y agentes | EXISTING | Core 2 previo; no se capturaron pantallas/cámara en esta entrega |

VERIFIED describe la prueba indicada, no certifica cualquier dispositivo o aplicación.
