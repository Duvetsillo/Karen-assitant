# Karen Core 2

Evolución incremental. Se conservan Tkinter, Electron, Ollama, los almacenes
SQLite, las integraciones y los mecanismos de aprobación existentes.

## Componentes

`karen_core2/runtime.py` es la fachada compartida. Se carga dentro del proceso
de clásica o del servidor móvil. No crea un daemon de inteligencia adicional.

| Módulo | Responsabilidad |
| --- | --- |
| `models.py` | Solo loopback, comprobación de capacidades, presupuesto RAM/VRAM, lease de SO, fallback local y latencias |
| `skills.py` | Manifiestos y esquemas por código, adaptadores existentes y procesos cancelables |
| `planning.py` | DAG persistente, subtareas TaskEngine, idempotencia, aprobación, resultados y recuperación |
| `memory.py` | Tipos de memoria, relaciones, relevancia, caducidad y procedimientos verificados |
| `vision.py` | Captura de pantalla/ventana bajo demanda, análisis local y clic autorizado ligado a captura vigente |
| `diagnostics.py` | Series acotadas, variaciones de procesos y fallos de servicios sin falsas causalidades |
| `privacy.py` | Cifrado DPAPI, redacción y huellas para auditoría |
| `api.py` | Extensión de lectura para Core v1 |
| `panel.py` | Panel opcional dentro de la ventana clásica |

## Flujo de planificación

La propuesta del modelo es solo datos JSON. El código valida nombres, argumentos,
dependencias, ciclos y permisos. Los permisos provienen del registro, no del modelo.
Cada paso ejecuta una herramienta registrada mediante el TaskEngine existente.
El paso solo termina cuando su verificador por código acepta la evidencia.

«Diagnostica mi PC» y «Optimiza mi PC» preparan un flujo inicial de lectura:
muestra de tendencias, CPU, RAM, disco, procesos e informe. La petición vaga de
optimización no autoriza borrar archivos, detener procesos ni cambiar servicios.
Los cambios se proponen como operaciones concretas y requieren sus permisos.

La planificación generada tiene un máximo de 24 pasos y admite una corrección
de esquema antes de ejecutar. Las lecturas fallidas tienen como máximo dos
intentos por ejecución. Las escrituras no se repiten automáticamente.
Cancelar señala al TaskEngine y a los procesos administrados; no se anuncia
cancelación retroactiva de una escritura que ya pudo ocurrir.

## Persistencia y recuperación

No se introduce otra base:

- La base de tareas existente aloja planes, pasos, auditoría y series de sensores.
- La base Core/conversaciones existente conserva memorias y metadatos nuevos.
- Los esquemas base siguen en versión 1; las extensiones tienen versiones propias.

Los planes completos y sus resultados se cifran con DPAPI del usuario Windows.
La auditoría conserva herramienta, fecha, autorizador y hashes de parámetros y
resultados, sin cuerpos de archivos ni secretos. Las pantallas autorizadas pueden
mostrar la evidencia descifrada. La API Core de lectura y Pet reciben solo estados.

Tras una caída, una lectura activa queda `interrupted`. La reanudación explícita
salta pasos ya verificados. Una escritura activa queda `uncertain` y no se repite.
La revisión del efecto real de una escritura incierta es una acción humana.
No hay aprobación global inferida de texto, ni reejecución por abrir un historial.

## Memoria

Se amplía MemoryStore, no se reemplaza. Tipos: episódica, semántica, procedimental
y de proyecto. Estados: confirmado, hipótesis y temporal con caducidad.
La recuperación es léxica, acotada a 200 recuerdos del proyecto y hasta 20
resultados. Combina coincidencia, confirmación, prioridad y orden reciente.
No necesita embeddings ni otro modelo cargado.

Las relaciones no cruzan proyectos ni permiten leer recuerdos sensibles.
Reemplazar un hecho obsoleto caduca el anterior también para clientes v1.
Solo un plan terminado y verificado puede guardarse como procedimiento.
No se almacenan credenciales en esta memoria contextual.

## Agentes lógicos y habilidades

SYSTEM, DEVELOPER, RESEARCHER, HOME, ANALYST y ORCHESTRATOR comparten la misma
fachada, memoria, router y registro. Son roles de ejecución, no seis modelos
cargados ni seis procesos. SYSTEM usa inventarios y herramientas de Windows;
DEVELOPER usa lectura y operaciones de archivos; RESEARCHER hace síntesis local;
HOME consulta el puente existente; ANALYST contrasta mediciones; ORCHESTRATOR
valida y coordina los planes.

Cada habilidad declara identificador, nombre, descripción, rol, permiso, esquema,
validador, handler, verificador y timeout. Solo código confiable registra habilidades.
No se cargan plugins arbitrarios desde respuestas del modelo. El planificador
no registra ejecución libre de PowerShell ni SSH. La administración clásica
con scripts revisados conserva su aprobación explícita existente.

Permisos: lectura, reversible, sensible y destructivo. Las lecturas no piden
aprobación adicional. Las escrituras del núcleo requieren decisión por operación;
las destructivas requieren confirmación ligada al plan y paso exactos. No se
incluye una habilidad destructiva genérica. El acceso móvil nunca hereda la
función de aprobación del escritorio.

## Router, rendimiento y privacidad

El router solo conecta a HTTP loopback y rechaza redirects, proveedores cloud,
alias de Ollama Cloud y metadatos `remote_host`/`remote_model`. No ofrece `pull`.
Selecciona por capacidad real, tarea, presupuesto de memoria y latencias medidas.
Comprueba el catálogo; un nombre grande no demuestra mejor calidad.

Clásica y móvil Core 2 comparten un lock de SO para inferencia. El router descarga
de VRAM otros modelos de Ollama antes de cambiar y libera los grandes al terminar.
Un modelo de hasta 1 GiB puede quedar caliente 60 segundos. Contexto: 4096 tokens;
batch: 128; salida de conversación: 256 tokens. Bajo presión de VRAM puede usar CPU
solo si hay RAM suficiente. No cierra aplicaciones del usuario para hacer espacio.

El launcher fija `OLLAMA_MAX_LOADED_MODELS=1` y `OLLAMA_NUM_PARALLEL=1` únicamente
cuando debe iniciar un servidor Ollama nuevo. Un Ollama ya abierto conserva su
entorno. Las llamadas directas de terceros o del gateway OpenClaw no adquieren
el lease Python; no se puede prometer exclusión global fuera de los clientes
cooperantes. No se reinicia ni reconfigura otro software para ocultar ese límite.

La configuración guardada no se sobrescribe. Los puntos de entrada de clásica
y móvil aplican endpoint loopback en memoria. Pet exige gateway loopback y modelo
del proveedor Ollama no cloud. Su voz efectiva usa un motor local si la preferencia
guardada era Edge. La voz local existente y el wake word se conservan.

## Percepción

Empieza pausada. Solo captura por una acción explícita. No existe bucle de capturas.
Imágenes de hasta 1280 px y 4 MiB permanecen en memoria. La pausa descarta la
captura y cancela el análisis en streaming. La falta de modelo o recursos da un
error claro, sin descargar alternativas. El texto de pantalla se trata como dato
no confiable, nunca como autorización ni instrucciones de ejecución.

El clic es una habilidad sensible. Necesita captura vigente de menos de 60 segundos,
coordenadas válidas, mismo HWND y proceso y geometría sin cambios. Después de la
aprobación restaura únicamente la ventana revisada. La captura se consume una vez.
El recibo distingue enviar entrada de demostrar el efecto funcional en la aplicación.

## Tendencias

El monitor sigue siendo optativo. `watch-pc --trends` añade muestras a la base de
tareas. Retención: 720 muestras de recursos, 7200 muestras de procesos y 500 fallos
de servicio; los eventos se deduplican por RecordId. Las recomendaciones exigen
evidencia suficiente. Una variación de RAM no demuestra una fuga; eventos de un
servicio no prueban su causa ni predicen con certeza una caída.

Documentos relacionados: [[KAREN_CORE_2_AUDIT]], [[KAREN_CORE_2_OPERATIONS]],
[[KAREN_CORE_2_ACCEPTANCE]].
