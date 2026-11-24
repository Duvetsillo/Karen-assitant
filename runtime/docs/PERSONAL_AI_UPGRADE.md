# Karen personal local — estado y operación

24 de noviembre de 2026. Entrega incremental sobre Python/Tkinter y Core 2.
El plan completo sigue en desarrollo; esta entrega no implementa full-duplex.

## Iniciar y configurar

Desde `C:\karen`:

```powershell
./start_karen.ps1
python personal_profile.py show
python personal_profile.py init
python personal_profile.py set initiative moderate
python personal_profile.py set verbosity brief
```

El lanzador usa Python 3.11 cuando está instalado, aplica inferencia Ollama
loopback y conserva la configuración guardada. `requirements.txt` incluye ahora
Pillow, necesario para la visión ya existente. Instala requisitos con el mismo
intérprete que usará el lanzador. La voz sigue necesitando sus entornos/modelos
locales existentes y el repositorio separado `desktop-pet/python`; esta entrega
no descarga pesos ni reconstruye esos entornos.

Una instalación sin `admin_policy.json` inicia con SSH y subredes sin autorizar;
consultar esa política vacía no crea archivos ni habilita destinos. Una política
existente conserva sus autorizaciones y los formatos inválidos fallan cerrados.

La identidad vive en `.private/personality.json`; `KAREN_PERSONALITY_FILE` permite
elegir otro archivo privado absoluto. La consulta no crea el archivo. El perfil
se valida y reemplaza atómicamente; datos corruptos producen un error explícito.
Se recarga para cada respuesta. Tono, humor, formalidad, iniciativa, detalle,
expresividad e interrupciones son independientes del LLM. Los controles antiguos
que desactivan sugerencias o sarcasmo siguen restringiendo el comportamiento.
Nombre e idioma son preferencias, no un almacén de biografía o credenciales.

Configura recursos antes de iniciar:

```powershell
$env:KAREN_RESOURCE_PROFILE = 'balanced'
$env:KAREN_VRAM_RESERVE_MIB = '1536'
./start_karen.ps1
```

`economy` fuerza CPU para todas las categorías del LLM, contexto de 2048 y
salida máxima de 192 tokens. `balanced` conserva los límites anteriores y
conversación/memoria en CPU. `quality` permite contexto de 4096 y conversación
de hasta 512 tokens; conserva la misma reserva y las comprobaciones de RAM.
La reserva configurable tiene mínimo de 1024 MiB. No reserva físicamente VRAM,
no controla aplicaciones externas y no es todavía un planificador global de
STT, TTS y LLM. Los proveedores heredados de TTS conservan sus límites propios.

## Conversación e interrupciones

El escritorio sigue recibiendo y segmentando el LLM en streaming. Cada petición
tiene un UUID y colas acotadas. La síntesis anticipa la siguiente frase mientras
se reproduce la anterior. Se registran en RAM frases generadas, sintetizadas y
entregadas por completo al dispositivo. No se guardan grabaciones.

**Detener voz** cancela audio y síntesis pendiente; el texto puede continuar.
**Cancelar generación** cancela texto y audio, incluso si el HTTP ya terminó
y todavía se está reproduciendo la respuesta. Las frases parciales quedan sin
confirmación; el rechazo de callbacks antiguos evita incorporarlos a otro turno.

Tras detener una explicación, escribe «continúa» o una corrección cuando termine
la petición actual. Core 2 recibe la pregunta anterior, las últimas frases
entregadas y las primeras no confirmadas, con límites de tamaño y alcance al
mismo chat/sesión/proveedor. Ese contexto se consume tras una respuesta correcta.
El modelo decide cómo retomar; la interpretación semántica no está certificada.
Los resultados de herramientas/comandos privados no entran en esta continuidad.
La recepción de audio por Windows tampoco prueba que el usuario lo oyó.

La captura nativa **todavía se pausa al responder**. No se añadió escucha RMS
simultánea sin AEC: confundiría altavoces y voz del usuario. Full-duplex, barge-in
acústico, STT parcial, discriminación de «ajá» y detección semántica del final
de turno siguen pendientes. El HTTP móvil conserva respuesta completa.

## Conocimiento revisado

En la pestaña **Core 2**, usa **Importar conocimiento** y **Ver documentos
locales**. La selección confirma almacenamiento local y pregunta si contiene
información sensible. Importar no aprueba el uso como contexto.

```powershell
python knowledge_cli.py import 'C:\ruta\nota.md'
python knowledge_cli.py list
python knowledge_cli.py review ID
python knowledge_cli.py approve ID
python knowledge_cli.py search 'proyecto telescopio'
python knowledge_cli.py delete ID
```

En el chat clásico están disponibles `/conocimiento`, `/conocimiento buscar TEXTO`,
`/conocimiento revisar ID`, `/conocimiento aprobar ID` y `/conocimiento eliminar ID`.
Son comandos locales: su respuesta no se guarda como conversación ni se envía
al LLM. La importación sensible por CLI requiere **ambas** opciones `--sensitive
--allow-sensitive`; revisión y eliminación sensibles requieren `--allow-sensitive`.
Ni siquiera un documento sensible aprobado participa en recuperación automática.

Formatos integrados: TXT, Markdown, JSON, CSV y HTML en UTF-8; máximo 1 MiB,
256 fragmentos de hasta 1200 caracteres. HTML se vuelve texto sin ejecutar
scripts ni descargar recursos. CSV no ejecuta fórmulas. No se importan directorios,
archivos comprimidos, rutas relativas ni compartidos UNC. El filtro de posibles
credenciales es conservador: puede rechazar texto legítimo y no garantiza
detectar todos los secretos. Revisa tus documentos antes de importarlos.

Los datos usan tablas adicionales y FTS5 en el SQLite existente. La recuperación
incluye como máximo tres fragmentos públicos aprobados de versiones activas,
con nombre de fuente, ID y posición. Una nueva versión permanece pendiente hasta
aprobarla; al hacerlo se retira la versión anterior de esa fuente del contexto.
Las versiones anteriores siguen revisables y se eliminan por ID.

Los documentos son datos no confiables, nunca instrucciones, permisos o hechos
personales confirmados. El chat de Core 2 no recibe herramientas ejecutables a
partir de ellos. Esto limita ejecución, pero no demuestra inmunidad del LLM a
manipulación textual. La búsqueda actual es **léxica FTS5**, no embeddings ni
aprendizaje autónomo. PDF, DOCX, fotografías, importadores sociales especializados,
embeddings y consolidación en inactividad quedan pendientes.

## Voz seleccionada y licencias

Se conserva el proveedor local instalado: Qwen3-TTS Base 0.6B (metadatos locales
`tts_model_size=0b6`, `tts_model_type=base`), perfil fijo y servicio persistente.
Core 2 convierte Edge a Qwen3 en ejecución; no sobrescribe ajustes ni cambia
referencias de voz. Kokoro queda como alternativa ligera existente seleccionable,
sin promoverlo a voz principal. El perfil fijo puede seguir prevaleciendo sobre
esa selección heredada; no se promete una conmutación automática CPU para Qwen.

El modelo oficial [Qwen3-TTS 0.6B Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base)
declara Apache-2.0 y español. La ruta Windows existente usa FP32 y decodificador
CPU para la RTX 2060; no se sustituyó por el ejemplo BF16/FlashAttention del modelo.
Esto no garantiza acento latinoamericano satisfactorio ni latencia publicada.
No se descargaron muestras ni se clonó otra voz. La procedencia/autorización de
la referencia ya configurada debe mantenerse documentada por su propietario.

Alternativas examinadas sin instalar pesos:

- [Chatterbox Multilingual](https://github.com/resemble-ai/chatterbox): proyecto
  abierto con español; compatibilidad y presupuesto Windows de esta PC no medidos.
- [OpenVoice V2](https://github.com/myshell-ai/OpenVoice) y
  [MeloTTS](https://github.com/myshell-ai/MeloTTS): candidatos para conversión y
  síntesis. No se validaron aquí pesos concretos, acento ni entornos Windows;
  por ello no se sustituyó el proveedor funcional.
- [Piper actual](https://github.com/OHF-Voice/piper1-gpl): runtime GPL; cada voz
  necesita revisión independiente de su MODEL_CARD. No se seleccionaron pesos
  ni se presenta un fallback Piper como instalado.

## Evidencia y límites

Línea base: 305 pruebas correctas en Python 3.14, 62.873 s. Regresión funcional
final: 330 pruebas correctas en Python 3.14 (62.107 s) y Python 3.11 (61.485 s).
La prueba inicial de 3.11 detectó Pillow ausente; se corrigió e instaló 13.0.0.
La comprobación adicional del commit publicado, sin configuración privada,
descubrió y corrigió la dependencia del archivo administrativo ignorado.
**Resultado final limpio: 333 pruebas OK en Python 3.11, 61.450 s**, sobre
`e4e73b7`, con dependencias de código existentes y sin ajustes personales.
Incluye GUI Tk real, importación revisada, persistencia, exclusión sensible,
versiones, índices, cancelación de audio anticipado y límites de recursos.

Medición única con prompt sintético, SQLite temporal y `gemma3:1b` en CPU:

| Medida | Resultado |
| --- | --- |
| Primer fragmento del LLM | 4.685 s |
| Generación total | 4.753 s |
| Fragmentos recibidos | 2 |
| RAM disponible antes / después | 6979002368 / 6062333952 bytes |
| VRAM disponible antes / después | 5186256896 / 5191499776 bytes |

Son instantáneas, no máximos ni consumo exclusivo de Karen. No miden STT,
TTS, audio, RTF o interrupción física; no cumplen por sí mismas el objetivo de
primer audio de 0.5–1.5 s. No se cargó otro modelo ni se usó micrófono.
La GUI propia se inspeccionó a 1360×900 y 1180×850; se corrigió el espacio de
resultados y texto mal codificado. El detector de diseño no encontró problemas;
no sustituye una auditoría de accesibilidad o prueba auditiva.

Para repetir la medición con datos sintéticos: `python qa/measure_personal_core.py`.
Guarda métricas en `tmp/personal-core-metrics.json`, sin preguntas ni respuesta.
Omite la medición si Ollama ya informa un modelo cargado para no desalojarlo.

## Respaldo y recuperación

Los documentos importados, índices y recuerdos están en el SQLite existente;
la personalidad está en `.private/`. El respaldo existente copia esa carpeta
y usa la API online de SQLite, sin mezclar WAL/SHM de distintas fechas:

```powershell
python maintenance.py backup 'C:\karen\backups\personal-20261124'
python maintenance.py verify 'C:\karen\backups\personal-20261124'
```

Elige un directorio nuevo. Para restaurar, cierra Karen, sus servidores y
clientes que escriban. Conserva primero una copia de los archivos actuales.
Verifica el manifiesto y copia desde `user-data/.private/` a la ruta privada
de destino; no copies WAL, SHM ni locks de otra sesión. Reinicia y consulta
perfil, recuerdos y documentos. No hay restauración automática sobre datos vivos.
Una ruta personalizada fuera de `.private/` requiere respaldo explícito aparte.
Los datos protegidos con DPAPI necesitan el mismo usuario Windows.

Eliminar documentos retira filas, fragmentos y entradas FTS; no borra el archivo
original seleccionado. El borrado lógico y `secure_delete` no prometen borrado
forense de WAL, SSD o respaldos históricos. Los respaldos conservan sus copias
hasta retirarlos explícitamente; pueden reintroducir documentos al restaurar.

## Aceptación del objetivo completo

PASS indica únicamente el alcance comprobado, no equivalencia con ChatGPT Voice.

| # | Criterio | Estado y alcance |
| --- | --- | --- |
| 1 | Inicio Windows | PASS: ventana Tk real con almacenes temporales |
| 2 | Todas las funciones anteriores | NOT TESTED: regresión pasa; dispositivos externos no ejercitados |
| 3 | Identidad persistente | PASS: guardar, recargar y aplicar con distintos estilos |
| 4 | Conversación streaming | PASS: prueba real Ollama local y regresiones |
| 5 | Escuchar mientras habla | FAIL: captura clásica pausada |
| 6 | Interrupción vocal | FAIL: solo cancelación manual integrada |
| 7 | Ausencia de audio obsoleto | NOT TESTED físicamente; pruebas de colas/cancelación pasan |
| 8 | Retomar explicación | NOT TESTED semánticamente; contexto de continuidad integrado |
| 9 | Confirmación breve frente a interrupción | NOT TESTED; clasificación acústica pendiente |
| 10 | Síntesis femenina local | NOT TESTED en esta sesión; proveedor/perfil existentes conservados |
| 11 | Proveedores sustituibles | PASS en contratos/configuración; no se probaron nuevos TTS |
| 12 | Recuerdos persistentes | PASS: pruebas SQLite y reinicio de almacenes |
| 13 | Recuperación relevante | PASS léxico; recuperación vectorial pendiente |
| 14 | Corregir/eliminar recuerdos | PASS: regresiones de memoria existentes |
| 15 | Importación/indexación | PASS para formatos textuales indicados |
| 16 | Documentos no ejecutan órdenes | PASS en frontera de herramientas; no prueba inmunidad textual |
| 17 | No saturar GPU deliberadamente | PASS: inferencia medida CPU y pruebas del margen solicitado |
| 18 | Degradación ante falta de VRAM | NOT TESTED físicamente; router CPU cubierto, Qwen TTS sin fallback CPU |
| 19 | Datos privados fuera de Git | PASS: archivos privados ignorados y staging explícito |
| 20 | Restauración de respaldo | PASS sintético conjunto de perfil, memoria, documentos e índice; producción no probada |
| 21 | Acciones sensibles autorizadas | PASS en regresiones de planes y documentos sensibles |
| 22 | Ejecución documentada | PASS en GUI local; instalación nueva completa no ejercitada |

## Siguiente fase concreta

1. Implementar captura de navegador con AEC nativo o un AEC Windows verificable,
   manteniendo el control explícito de micrófono y sin Web Speech remoto.
2. STT incremental CPU con ventanas acotadas, estabilización de parciales y
   detección de fin de turno por voz, texto y silencio. Evitar inferencia LLM
   por cada fragmento de audio.
3. Unir esa captura con UUID, cancelación y recibos de reproducción ya integrados;
   medir interrupción y primer audio con dispositivos reales.
4. Medir TTS con margen real de VRAM y validar acento con el usuario; evaluar
   Piper solo después de verificar licencia y calidad de una voz concreta.
5. Ampliar importación, perfil personal y recuperación semántica sin convertir
   documentos importados o inferencias en hechos confirmados automáticamente.
