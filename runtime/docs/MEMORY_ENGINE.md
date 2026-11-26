# Memoria operativa

MemoryStore conserva el contrato SQLite anterior. ContextMemory añade tipos,
estados, relaciones, procedimientos, FTS5 y acceso persistente sin sustituirlo.
Tipos: episodic, semantic, procedural, project, user, autobiographical, prospective;
se conservan contextual, temporal y relational por compatibilidad.
La memoria de trabajo corresponde al historial acotado del turno actual.

Metadatos: ID, proyecto, contenido, fuente, fecha de creación/actualización,
caducidad, sensibilidad, estado, confianza, prioridad, relevancia calculada,
etiquetas, relaciones, último acceso y contador de recuperaciones.
Los contadores miden consultas de software; no certifican lectura o audición humana.

La migración `memory_retrieval_version=1` crea un índice FTS5 reconstruible y
triggers para insert/update/delete, incluidos escritores antiguos. Solo indexa
registros no sensibles. La recuperación filtra proyecto, caducidad y validación;
selecciona hasta 200 candidatos y devuelve como máximo 20. El prompt conserva
el límite anterior de tres recuerdos confirmados y evita contradicciones activas.
Las notas y recuerdos siguen siendo datos, nunca autorización para herramientas.

Contradicciones: las claves fact_key iguales crean relaciones explícitas. Una
corrección con supersedes retira el recuerdo anterior para los clientes antiguos
y conserva su historial. No se presume detección semántica general de contradicciones.

```powershell
python memory_cli.py add Karen 'Prefiero explicaciones breves.' --kind user
python memory_cli.py add Karen 'Revisar proyecto pendiente.' --kind prospective
python memory_cli.py search Karen 'proyecto'
python memory_cli.py reindex
python memory_cli.py export-engine Karen 'C:\ruta\archivo-nuevo.json'
```

En clásica, sin modelo disponible:

- `Recuerda que prefiero explicaciones breves`
- `Qué recuerdas sobre explicaciones`
- `Corrige el recuerdo ID | Prefiero explicaciones detalladas`

La orden explícita del usuario es la fuente de estos recuerdos. La corrección
requiere un ID público del proyecto Karen. No se infiere conocimiento confirmado
desde respuestas de Karen, handoffs o documentos. Las credenciales detectables
se rechazan incluso en la ruta MemoryStore anterior.

La exportación conserva metadatos públicos e historial. Backup y restauración
SQLite se verifican con maintenance.py; DPAPI depende del usuario Windows.
## Importación portable con revisión

```powershell
python memory_cli.py import-engine Karen 'C:\ruta\memorias.json'
python memory_cli.py import-engine Karen 'C:\ruta\memorias.json' --apply --expected-hash HASH_DE_LA_VISTA_PREVIA
python memory_cli.py inspect-import ID
python memory_cli.py review-import ID --expected-hash HASH_DE_LA_INSPECCION
```

Preview valida y muestra cantidades y una huella ligada al documento y proyecto.
Apply requiere esa huella. Admite memory-engine-1, JSON local UTF-8 de hasta 8 MiB
y 1.000 recuerdos. Rechaza claves duplicadas, referencias ajenas, datos sensibles,
posibles credenciales, estados desconocidos y fechas sin zona. No lee rutas de red.

Cada recuerdo nuevo recibe otro ID, origen imported y estado PENDIENTE/inferred,
con prioridad y confianza iniciales cero. Conserva tipo, contenido, etiquetas,
detalles, clave de hecho, fecha original y caducidad. Los retirados y caducados
permanecen inactivos. Los duplicados locales se omiten sin modificarlos ni revelar
sus IDs. Ningún recuerdo importado entra automáticamente al contexto confirmado.

Las versiones, relaciones y ejecuciones declaradas se conservan como procedencia
reportada, separada de la historia local y los procedimientos verificados.
Export-engine conserva esa procedencia en el campo opcional reported, sin anidar
paquetes completos. Las exportaciones anteriores continúan siendo compatibles.

Inspect-import muestra recuerdo y procedencia; review-import requiere la huella
vigente de esa inspección. Solo la revisión explícita confirma el dato. Un cambio
concurrente invalida la huella. No activa ejecuciones de procedimientos importadas.
Si se revisan hechos con igual fact_key, se detecta la contradicción local y se
excluyen del contexto confirmado hasta corregirlos.

Una transacción SQLite cubre recuerdos, versiones, FTS5 y procedencia; un fallo
revierte todo. Borrar memoria elimina también la procedencia. La sensibilidad
actual impide inspección y exportación. No se habilitaron importaciones ni
promociones desde móvil, Pet, documentos o respuestas del modelo.

Pruebas: `python -m unittest qa.test_memory_portability`. Diez casos con archivos
y SQLite temporales: rollback, exportación/reimportación, hashes obsoletos,
caducidad, duplicados privados, contradicciones y evidencia de ejecución falsificada.

Prueba sintética con 501 recuerdos: recuperación de un recuerdo antiguo relevante
en 0,005613 s. El filtro anterior de 200 recientes no lo incluía. Mediciones en
MEMORY_METRICS_2026-11-26.json; el índice no requiere embeddings ni GPU.
