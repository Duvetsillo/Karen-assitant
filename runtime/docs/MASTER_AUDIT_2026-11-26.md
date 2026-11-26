# Auditoría incremental — 2026-11-26

## Alcance

Repositorio `C:\karen`, Python 3.14.7, SQLite 3.50.4, Windows 11.
Pet es un repositorio separado: Node 24.19.0, Electron, React, Pixi y TypeScript.
No se sustituye este stack por Fastify ni se despliega en Proxmox.

Estado Git inicial: tres archivos sin seguimiento, `karen_core2/events.py`,
`karen_core2/obsidian.py`, `ollama-openclaw.Modelfile`. Se consideran trabajo previo;
se reutilizan los dos módulos Python y se conserva el Modelfile sin cambios.

## Inventario por módulo

| Módulo objetivo | Estado inicial | Evidencia y límite |
| --- | --- | --- |
| Interface Layer | EXISTING | Tkinter, Pet y móvil; no rediseñar |
| Cognitive Core / Context Manager | PARTIAL | runtime.py, intención determinista, historial acotado; falta Obsidian |
| Model Router | EXISTING | models.py, Ollama loopback, streaming, lease, cancelación, fallback |
| Memory Engine / Persistence | EXISTING | MemoryStore, ContextMemory, SQLite, correcciones, backups; tipos incompletos |
| Personality Engine | EXISTING | personal_profile.py y karen_personality.py |
| Voice Engine | PARTIAL | voz local, cancelación y recuperación; barge-in/AEC físicos pendientes |
| Knowledge Engine | EXISTING | documentos revisados, FTS5, fragmentos acotados |
| Obsidian Manager | PARTIAL | módulo previo no conectado ni cubierto por pruebas |
| Agent Orchestrator | EXISTING | roles lógicos, registro validado, planes persistentes |
| System Awareness | EXISTING | sensores Windows, contexto bajo demanda |
| Resource Manager | PARTIAL | perfiles CPU/GPU, reserva estimada, lease; modo gaming no enlazado al router |
| Perception Engine | EXISTING | captura autorizada temporal, visión local, clic revisado |
| Proactive Engine | PARTIAL | alertas persistentes, quiet hours, gaming; no seguimiento de proyectos |
| Automation Engine | PARTIAL | TaskEngine y Plans persistentes; no scheduler común |
| Learning Engine | PARTIAL | correcciones y procedimientos; no evolución autónoma |
| Codex Bridge | PARTIAL | Git y documentación; falta protocolo estructurado de handoff |
| Security Engine | EXISTING | esquemas, herramientas nombradas, aprobación por operación, DPAPI |
| Diagnostics Engine | PARTIAL | sensores, tendencias, métricas; sin log común rotativo |
| Event Bus | PARTIAL | módulo previo validado, sin integración en runtime |

EXISTING significa código localizado, no aceptación física de todas sus capacidades.
VERIFIED se asigna únicamente a resultados concretos en CURRENT_STATE y HANDOFF.

## Referencia medida

Consulta de sensores: 0,1233 s. RAM disponible: 8.207.585.280 bytes.
VRAM libre: 5.282.725.888 bytes, total: 6.442.450.944 bytes.
Son instantáneas, no presupuestos permanentes ni consumo exclusivo de Karen.
Ollama `/api/tags`: ConnectTimeout a 2 s. Inferencia real BLOCKED mientras no responda.
Pet: 25 archivos, 163 pruebas correctas, 8,67 s. Python base: 337 correctas en 60,426 s.
Tras iniciar Ollama por autorización expresa, se verificaron ocho modelos locales
y una conversación real. La regresión final pasó 355 pruebas en 61,749 s.

## Prioridad

Conectar los módulos previos de Obsidian y eventos con la fachada existente.
Validar archivos reales, FTS5, cambios externos, conflictos, permisos y reinicio
en una bóveda temporal antes de habilitar carpetas documentales reales.
Completar después gaming, handoff y observabilidad; registrar límites de cada fase.
