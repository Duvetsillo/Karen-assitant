# Memoria musical compartida — 2026-11-26

`ContextMemory.music` expone observaciones musicales guardadas por Pet sobre la
conexión Core existente. El lector Python no crea tablas musicales ni promueve
metadatos a recuerdos confirmados. `history(limit=200)` y `summary()` son lecturas
acotadas, con datos explícitamente reportados y gustos separados de reproducciones.

El escritor Pet usa la misma base `KAREN_CORE_DB`, contrato aditivo
`core_meta.music_version=1`, `core_music_tracks` y `core_music_plays`. Sin Core
conectado, la percepción y el reproductor funcionan, pero la memoria indica que
no está disponible. No se crea un almacén musical paralelo.

Historial apagado por defecto. Si se habilita, se registra tiempo escuchado estimado,
reproducciones, repeticiones y omisiones por una orden de siguiente confirmada con
margen respecto al final conocido. Saltos externos no se infieren automáticamente.
Gustos/recuerdos musicales requieren una orden explícita y el historial habilitado.
Borrar historial elimina solo las dos tablas de datos musicales y conserva memoria
general, preferencias y metadatos de versión.

No hay letras, grabaciones, audio, portadas ni transcripciones en esas tablas. Un
identificador con prefijo `metadata:` es un fingerprint interno, no un ID oficial.

Verificación:

- `python -m unittest discover -s qa -p 'test_*.py'`: 416 pruebas correctas.
- `python qa/verify_music_interop.py`: Node compilado escribe sobre un Core temporal;
  Python lee los 45 s y la preferencia explícita. El borrado musical conserva un
  recuerdo general sintético. No se abren bases reales del usuario.
- Pet: pruebas dirigidas de clasificación, política, SQLite y transporte local.

Detalles del motor multimedia y limitaciones por plataforma:
`desktop-pet/docs/MUSIC_PRESENCE.md`. El primer incremento Pet es `4a0cb43`, publicado.
Interfaz y HTTP local pasan con metadatos sintéticos; controles GSMTC pasan con
MediaPlayer sintético silenciado. No se certifican proveedores comerciales por
el mero hecho de pasar fixtures.

`music_summary` está registrado como herramienta READ para Plans y para el scheduler
existente. Una receta con ese único paso se ejecutó correctamente en un Core temporal
sin LLM. Puede emplearse para resúmenes periódicos; no se activó el runner ni se
crearon tareas en bases reales. La exportación Markdown del reproductor requiere
elegir un archivo; no autoriza escrituras periódicas automáticas al vault.
