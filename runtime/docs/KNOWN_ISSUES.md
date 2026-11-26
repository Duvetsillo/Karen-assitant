# Pendientes y límites conocidos

- La directiva completa sigue abierta. Roadmap conserva lo implementado y lo pendiente.
- La edición de propiedades soporta claves YAML simples y valores JSON compatibles
  con YAML. Rechaza sintaxis ambigua, duplicados y merges; usar update revisado.
- Mover publica una copia sin sobrescribir y después elimina el origen con backup.
  Un fallo intermedio puede dejar dos copias; queda uncertain y no se repite la escritura.
  No se reescriben backlinks automáticamente al mover o renombrar.
- La apertura en Obsidian está implementada por URI. Se verificó mediante simulación
  del lanzamiento; la ventana real sigue pendiente de aceptación humana.
- El watcher usa polling de metadatos y debounce, no eventos nativos de Windows.
  Las notas vacías, mayores de 1 MiB o con posibles secretos se omiten del índice.
- Detección de conflictos por hash es optimista. Una aplicación externa que escriba
  entre la última comprobación y os.replace puede competir; no se promete CAS del SO.
- Las comprobaciones de reparse points previenen rutas comunes, pero no son un
  sandbox contra un atacante local que cambie directorios simultáneamente.
- `daily` exige nombre YYYY-MM-DD, pero el cliente elige carpeta y contenido.
- Entrar en gaming cancela streams GPU activos y las nuevas solicitudes usan CPU.
  Antes de recibir headers HTTP sigue rigiendo el timeout del proveedor.
- EventBus es de proceso y acotado; no conserva eventos para replay. El journal
  rotativo no garantiza orden/rotación coordinados entre varios procesos escritores.
- La cancelación antes del primer byte sigue dependiendo de los timeouts HTTP.
- Handoffs marcados complete contienen resultados reportados; no prueban por sí
  mismos que Codex haya ejecutado esos comandos. No activan herramientas ni despliegues.
- DPAPI exige el mismo usuario Windows para descifrar backups; migración a otro
  equipo requiere exportación explícita y traslado seguro, no copia ciega de payloads.
- La importación admite memory-engine-1 de hasta 8 MiB y 1.000 recuerdos por paquete.
  El historial externo queda reportado y no certifica experiencias ni ejecuciones locales.
  FTS5 se puede reconstruir con memory_cli.py reindex.
- Los contadores de acceso indican recuperación por software, no que el usuario
  leyó o escuchó el contenido. Contradicciones automáticas usan fact_key explícito;
  no se atribuye comprensión semántica general al índice léxico.
- Pet y móvil consultan metadatos de schedules/handoffs. La gestión remota de
  documentos y la importación/promoción de recuerdos requieren otros permisos.
- El Pet modificado se compiló en el checkout histórico desktop-pet; el ejecutable
  1.8.1 instalado desde otro checkout conserva su versión y no se reemplazó.
- Scheduler optativo y READ con triggers y condiciones declarativos. Los eventos
  durante trabajo programado se omiten para impedir bucles; esto puede omitir un
  evento externo coincidente. Solo escucha su EventBus, sin replay de logs externos.
- Tópicos resource.pressure/gaming.ended requieren productores reales configurados;
  registrarlos como triggers no implementa detección automática de videojuegos.
- Reiniciar runtimes antiguos antes de usar políticas nuevas. No se actualiza
  automáticamente el código que otro proceso ya cargó en memoria.
- La cola prioriza dentro de cada router; el lease de SO serializa procesos
  cooperantes sin prometer prioridades globales ni controlar clientes externos.
- Barge-in, AEC y recuperación con voz humana siguen pendientes. No se grabó audio.
