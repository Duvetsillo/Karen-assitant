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

Completada. Línea base: `python -m unittest discover -s qa -p 'test_*.py'`: **305 pruebas, OK, 62.873 s** (Python predeterminado). Otra ejecución con Python 3.11 está en curso; resultados locales en `tmp/`, excluidos de Git.

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

## Próxima tarea

Turnos cancelables con seguimiento de audio realmente entregado al dispositivo y continuidad explícita tras una interrupción manual. Mantener la captura acústica simultánea pendiente hasta validar AEC.
