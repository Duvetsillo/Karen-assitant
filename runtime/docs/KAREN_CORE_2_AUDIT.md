# Karen Core 2 — auditoría previa

## Alcance y evidencia

Se inspeccionaron los módulos Python de raíz, las interfaces y fuentes Electron,
los contratos compartidos, los adaptadores, las pruebas y los modelos reales de
Ollama. No se leyó el contenido de credenciales ni se modificó Rebecca.
La línea base pasó 207 pruebas Python y 161 pruebas de Pet antes de los cambios.
Los cambios anteriores del usuario se conservaron. Rama de trabajo:
`codex/karen-core-2`. Respaldo de 159 archivos bajo `.private/core2-recovery/`.

## Arquitectura existente

| Área | Implementación comprobada |
| --- | --- |
| Escritorio clásico | Python/Tkinter, `karen_app.py`, `ui.py`, `targets.py` |
| Pet | Electron 44, React 19, Zustand, Pixi; repositorio separado `desktop-pet/` |
| Comunicación clásica | Colas y trabajadores Python; Tk solo recibe actualizaciones de interfaz |
| Comunicación Pet | IPC Electron validado; WebSocket autenticado a OpenClaw local |
| Ollama | Clásica: HTTP `/api/chat`, streaming y contexto acotado; Pet: adaptador OpenClaw |
| Historial | `Conversations`, SQLite, turnos atómicos; Core compartido opcional |
| Memoria | `MemoryStore`, memoria por proyecto, confirmada/inferida, sensibilidad, caducidad y deduplicación |
| Herramientas | `AdminRuntime`, esquemas, operaciones nombradas, aprobación y auditoría |
| Tareas | `TaskEngine`, SQLite separado ya existente, locks de SO, cancelación cooperativa, estados inciertos |
| Voz | Wake word local, Whisper/faster-whisper, servicios locales Kokoro/Qwen y control de recursos compartidos |
| API | Core v1 de lectura en loopback, DPAPI y tokens por cliente; móvil con cookie firmada |
| iPhone | Cliente instalable servido por `mobile_server.py`; acceso privado Tailscale |
| Percepción Pet | Captura seleccionada, adjuntos, señalamiento y acciones de Windows ya existentes |
| Integraciones | Home Assistant, SSH, Proxmox, Gmail/gog, iCloud, recordatorios OpenClaw, benchmarks Aetherion |
| Monitor | Alertas persistentes de CPU/RAM/disco, modos, silencio y consultas de sensores Windows |
| Mantenimiento | Backups con SQLite online backup, integridad y hashes |

No se partió de una supuesta ausencia de memoria, captura, herramientas o tareas.

## Límites encontrados

1. TaskEngine guardaba hashes del plan y argumentos. No permitía recuperar por
   sí solo una receta completa tras reiniciar.
2. Los motores de conversación, los permisos y el ciclo de vida de modelos no
   estaban unificados entre clientes.
3. La configuración guardada de clásica apuntaba a otro PC de la LAN. No cumple
   el nuevo requisito de inferencia exclusivamente en este PC.
4. Existían opciones de Ollama Cloud y Edge TTS. No se eliminan los archivos de
   configuración: Core 2 impone alternativas locales en ejecución.
5. Las alertas eran de umbral; no conservaban una serie histórica para tendencias
   de recursos, variaciones por proceso o eventos repetidos de servicios.
6. No había un planificador estructurado común, roles lógicos ni panel de planes.
7. La percepción de Pet no equivalía a un router local que comprobara capacidades
   visuales reales, recursos disponibles y límites de transferencia.

## Inventario local comprobado

RTX 2060, 6144 MiB VRAM. RAM física visible: aproximadamente 15,9 GiB.
Ollama local 0.40.16. Consultas reales a `/api/tags` y `/api/show`:

| Modelo | Capacidades anunciadas relevantes |
| --- | --- |
| `gemma3:1b` | completion |
| `gemma3:4b` | completion, vision |
| `qwen3.5:2b` | completion, vision, tools, thinking |
| `qwen3.5:4b` | completion, vision, tools, thinking |
| `qwen2.5-coder:3b` | completion, tools, insert |
| `llama3.2:3b` | completion, tools |
| `qwen3:4b` | completion, tools, thinking según metadatos consultados |
| `qwen2:0.5b` | completion |

`beam:cloud` se excluye. El alias `karen-openclaw:4b` no devolvió metadatos de
capacidades utilizables y se excluye del router hasta poder verificarlos.
No se descargó ningún modelo. No se atribuyó visión a Qwen3 por su nombre.

Durante la aceptación hubo solo unos 2,2 GiB RAM y 0,2 GiB VRAM libres. El router
rechazó modelos sin presupuesto suficiente. Tras liberar aplicaciones, hubo
aproximadamente 3,9 GiB RAM y 4,8 GiB VRAM libres; las pruebas locales avanzaron.

## Plan incremental aplicado

1. Fijar línea base y respaldos.
2. Añadir módulos sobre TaskEngine y MemoryStore, manteniendo contratos v1.
3. Añadir planes cifrados, dependencias, evidencia y reanudación explícita.
4. Añadir memoria contextual y roles lógicos sin procesos o modelos simultáneos.
5. Validar visión local bajo demanda con datos sintéticos propios.
6. Conectar clásica, móvil, API de lectura y Pet.
7. Añadir panel Core 2 y vista Jarvis opcional.
8. Ejecutar regresión, compilación y aceptación real; documentar límites.
