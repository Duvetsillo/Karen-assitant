# Integración Obsidian

No requiere CLI, plugin, REST API ni modelo. Usa archivos Markdown y SQLite FTS5.
La configuración local vive junto al SQLite Core: `obsidian.json` con campos
`vault` absoluto y `scopes` como array de carpetas relativas con `/`.
`KAREN_OBSIDIAN_CONFIG` selecciona otra configuración.

Las variables tienen prioridad sobre el archivo cuando se fija el vault:

```powershell
$env:KAREN_OBSIDIAN_VAULT='C:\Obsidian\Data Base'
$env:KAREN_OBSIDIAN_SCOPES='["Karen Asistant/Desktop Pet","00_Sistema/Proyectos/karen"]'
python -m karen_core2 obsidian reindex
python -m karen_core2 obsidian status
python -m karen_core2 obsidian search --args '{"query":"Karen"}'
```

En clásica: `/obsidian list`, `/obsidian status`, `/obsidian reindex`,
`/obsidian search {"query":"Karen"}` o `busca en obsidian Karen`.
Para leer: `/obsidian read {"path":"CARPETA/Nota.md"}`.

También se reconocen órdenes explícitas sin inferencia:

- `Lee la nota de Obsidian CARPETA/Nota.md`
- `Abre la nota de Obsidian CARPETA/Nota.md`
- `Crea una nota en Obsidian CARPETA/Nota.md | CONTENIDO`
- `Añade a la nota de Obsidian CARPETA/Nota.md | CONTENIDO`

Las escrituras y apertura mantienen sus permisos y revisión por operación.

Operaciones estructuradas disponibles: list, status, search, read, backlinks,
tasks, tags, properties, create, daily, update, append, link y reindex.
También move, rename, delete, open, properties_set, tags_set y tasks_set.
Sus parámetros se declaran en `ObsidianManager.SCHEMAS`; el puente los convierte
en manifiestos para Plans. Resultados de lectura son objetos/listas JSON; las
escrituras devuelven path, hash, verified y backup_id. `NoteConflict` exige releer;
`PermissionError` indica ausencia de autorización; ValueError rechaza esquema/ruta.

Crear requiere path/content. Update requiere path/content/expected_hash;
section opcional identifica un encabezado Markdown exacto y único.
Append requiere path/content/expected_hash. Link requiere path/target/expected_hash.
Daily crea una nota con nombre YYYY-MM-DD.md y no sobrescribe una existente.
Las escrituras generan planes y exigen aprobación del paso en la interfaz existente.
Si no hay callback, quedan awaiting_approval y pueden retomarse por ID.

El watcher inicia con CoreRuntime cuando la configuración es válida y se cierra
con la ventana clásica. Polling 2 s, debounce 250 ms, hasta 10.000 notas y 1 MiB por
nota. La configuración inválida deshabilita el módulo y registra un código seguro.
FTS5 usa términos escapados; los resultados verifican el hash contra el archivo.

Backups y journal de cambios quedan fuera del vault, junto a obsidian-index.sqlite3.
El índice guarda textos locales autorizados; no se envían a modelos por indexar.
Las notas con posibles credenciales se omiten. No se reorganiza la bóveda.

Move requiere path/target/expected_hash; rename requiere path/name/expected_hash.
Nunca sobrescriben el destino ni reescriben backlinks automáticamente. Un fallo
intermedio conserva copias y exige revisión del estado uncertain.
Delete requiere path/expected_hash y confirmación del plan y paso exactos.
Se conserva una copia previa fuera del vault y se elimina la entrada FTS5.

Properties_set acepta values_json, un objeto JSON con claves simples cuyos valores
son YAML válido. Conserva campos ajenos, cuerpo, CRLF y BOM; rechaza YAML ambiguo.
Tags_set acepta tags_json como lista JSON. Tasks_set acepta line entero y done
booleano. Los tres requieren path y expected_hash y pasan por aprobación.

Open requiere path/expected_hash y permiso sensible. Solicita apertura mediante
el [URI oficial](https://obsidian.md/help/uri), con ruta absoluta codificada.
El recibo distingue launch_requested de ui_verified; no demuestra que la ventana se abrió.

Pruebas destructivas solo en vault temporal: `python -m unittest qa.test_obsidian`.
Herramientas y limitaciones restantes: CAPABILITIES.md y KNOWN_ISSUES.md.
