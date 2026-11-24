# KAREN — actualización personal local

Fecha de inicio: 24 de noviembre de 2026. Rama: `codex/personal-ai-upgrade`.

## Estado inicial y arquitectura

- Aplicación existente Python/Tkinter; Electron/OpenClaw en un repositorio independiente ignorado (`desktop-pet/`). No es una aplicación Node principal.
- Core 2 integrado en los lanzadores: Ollama loopback, streaming en escritorio, clasificación determinista, cancelación, SQLite contextual, herramientas con aprobación, planes recuperables, diagnósticos y visión pausada.
- Voz: Qwen3 local con perfil fijo y servicio persistente compartido; Kokoro y Edge heredados. STT Whisper/Faster-Whisper. No se descargan modelos en esta actualización.
- El listener clásico cierra la captura durante transcripción, generación y reproducción. No hay full-duplex ni cancelación acústica de eco comprobados. La API móvil devuelve respuestas completas.
- Estado previo: cuatro archivos modificados de Home Assistant y dos archivos nuevos. Se conservan fuera de los commits de esta entrega.
- Recursos reales iniciales: RTX 2060, 6144 MiB totales, 1134 MiB usados y 4822 MiB libres. RAM física 16663404 KiB, disponible 6161888 KiB. Son instantáneas, no reservas.
- Python predeterminado 3.14.7; Python 3.11 instalado y seleccionado por el lanzador. Node 24.19.0.

## Fase 0 — auditoría

Completada. Línea base: `python -m unittest discover -s qa -p 'test_*.py'`: **305 pruebas, OK, 62.873 s** (Python predeterminado). Python 3.11 detectó una dependencia previa ausente (`PIL`); se añadió Pillow a requirements y se instaló Pillow 13.0.0 en ese intérprete. Resultados locales en `tmp/`, excluidos de Git.

## Decisiones

- Ampliar Core 2 y la voz existente, sin reescritura ni cambios de credenciales, servicios o dispositivos externos.
- Datos nuevos en `.private/`; nunca incluir perfiles personales, documentos, audio o bases en Git.
- Priorizar identidad persistente, cancelación y continuidad verificables. No habilitar captura simultánea sin control de eco validado.
- Commits por cambios funcionales comprobados; push normal a la rama independiente. No modificar fechas ni crear commits vacíos.

## Tareas, archivos y pruebas

- Auditoría: este archivo. Sin cambios funcionales todavía.

## Bloqueos y pendientes

- Full-duplex, AEC, transcripción incremental y validación auditiva del acento requieren implementación y prueba física; no se presentan como completados.
- Calidad/latencia de TTS y límites de VRAM no se deducen del número de parámetros.
- No activar herramientas externas, capturas ni automatizaciones existentes durante las pruebas.

## Fase 1 — identidad y proveedor local

Implementada la personalidad persistente con escritura atómica y validación estricta. `personal_profile.py show|init|set CAMPO VALOR` configura nombre, idioma, tono, humor, formalidad, detalle, iniciativa, expresividad e interrupciones. Ambos motores de conversación consumen el perfil; no se autoriza escritura desde el LLM. Las preferencias antiguas explícitas siguen restringiendo sugerencias y sarcasmo. El archivo no se crea al consultar y permanece en `.private/`.

Core 2 convierte Edge a Qwen3 local, conservando los demás proveedores configurados y el perfil de voz existente. Sin perfil Qwen instalado, hace falta prepararlo; no se descarga ni se cambia la voz automáticamente. Kokoro conserva su selección explícita como respaldo heredado.

Archivos: `personal_profile.py`, `karen_personality.py`, `karen_core2/runtime.py`, `.env.example`, pruebas de perfil y expectativa local en `qa/test_core2.py`. Pruebas: `python -m unittest qa.test_personal_profile qa.test_core2_models qa.test_core2`: OK (resultado detallado en registro local).

## Conversación y conocimiento — integración funcional

- Turnos con UUID, señales separadas para cancelar generación o solo audio, colas limitadas y rechazo de fragmentos obsoletos. Se distinguen frases generadas, sintetizadas y reproducidas completamente por el dispositivo. No demuestra que el usuario las oyó. Una frase interrumpida queda sin confirmación.
- Core 2 recibe continuidad acotada al siguiente turno del mismo chat/sesión/proveedor. Puede retomar una explicación o atender correcciones; la intención la interpreta el modelo, sin prometer acierto semántico. Resultados de herramientas y comandos privados nunca se transfieren como continuidad.
- Conocimiento local en el SQLite existente: TXT, Markdown, JSON, CSV y HTML UTF-8, máximo 1 MiB y 256 fragmentos. Extracción sin scripts ni descargas de imágenes, deduplicación, versiones por fuente, revisión, aprobación explícita, búsqueda FTS5 y eliminación de fuente/fragmentos/índice. No son embeddings semánticos.
- Los documentos pendientes y sensibles quedan fuera del contexto automático. El almacenamiento sensible exige autorización explícita. El filtro de posibles credenciales es conservador y no garantiza detectar todo secreto.
- Importación y lista en Core 2 de Tkinter; revisión/aprobación/eliminación mediante `/conocimiento` o `knowledge_cli.py`. No se modificaron las rutas de publicación del servidor móvil ni las integraciones externas.
- Menú Más acciones conserva controles secundarios y deja resultados legibles en 1180×850. Corregidas etiquetas españolas con codificación dañada. Verificación visual de la ventana sintética propia: salida de 13 px antes a 110 px en tamaño mínimo después. Skill impeccable; detector mecánico sin hallazgos (no equivale a auditoría de accesibilidad).

Archivos principales: `conversation_turn.py`, `voice.py`, `karen_app.py`, `karen_core2/runtime.py`, `karen_core2/knowledge.py`, `knowledge_cli.py`, `karen_core2/panel.py`, `ui.py`, `requirements.txt` y pruebas específicas. Pruebas de conocimiento, turnos, Core 2 y GUI: 39 OK antes de ampliar la verificación de cola; políticas y GUI ampliada: 13 OK; cola y GUI: 9 OK. Regresión intermedia: 317 OK, 56.570 s. Regresiones finales con ambos intérpretes en curso.

## Próxima tarea

Completar regresión final, documentar aceptación y realizar la integración en main autorizada por el usuario. Después, prioridad funcional: captura full-duplex con AEC verificable y STT incremental. No habilitar captura simultánea nativa basándose solo en RMS.

## Recursos — perfiles y medidas

Implementados `economy`, `balanced` (predeterminado) y `quality`, con margen configurable de VRAM (1536 MiB por defecto, mínimo 1024). Economy no coloca pesos del LLM en GPU y limita salida a 192 tokens; los perfiles superiores conservan conversación/memoria en CPU. No se cargan varios modelos por esta configuración. Los márgenes son estimaciones, no reservas físicas. Las métricas registran tiempo real hasta el primer fragmento de texto, sin guardar preguntas.

Pruebas específicas de políticas, conocimiento, turnos y GUI: 25 OK; posteriormente políticas, GUI con importación, conocimiento y conversaciones: 25 OK. Medición sintética de Core 2 con SQLite temporal: `gemma3:1b`, CPU, 2 fragmentos, primer token 4.685 s, total 4.753 s. RAM disponible antes/después: 6979002368 / 6062333952 bytes; VRAM disponible: 5186256896 / 5191499776 bytes. Instantáneas, no picos ni consumo atribuible solo a Karen. Sin micrófono, reproducción o síntesis en esa medición.
