# Karen Music Presence — 2026-11-26

## Contratos y adaptador nativo

Implementado un puente GSMTC en C#/.NET Framework con ensamblados incluidos en
Windows. `npm run build:music` usa el compilador del sistema; no instala SDK,
runtime, paquete NuGet ni modelos. El ejecutable se empaqueta en `dist-native`,
desempaquetado de ASAR. Solo se inicia al habilitar percepción musical.

Suscribe SessionsChanged, MediaPropertiesChanged, PlaybackInfoChanged y
TimelinePropertiesChanged. Suscripciones revocadas al recibir EOF; el timeout de
cierre solo afecta al helper propio. No hace polling del catálogo multimedia.
Las operaciones WinRT esperan su finalización con límite, sin consultar LLM.
Devuelve metadatos disponibles, controles, portada en memoria de hasta 256 KiB y
un identificador interno derivado de metadatos cuando la plataforma no ofrece ID.
Ese hash no se presenta como identificador oficial de canción.

GSMTC no proporciona origen de pestaña ni categoría de YouTube, y tampoco control
general de volumen. No se añaden controles inexistentes ni se envían teclas globales.
El clasificador rechaza navegadores sin evidencia de dominio, podcasts conocidos,
tutoriales, entrevistas, gameplay y YouTube ambiguo. La clasificación de plataformas
en fixtures no certifica compatibilidad real con sus aplicaciones.

Contratos en `shared/music.ts`, adaptador en `electron/music-adapter.ts`, memoria
en `electron/music-memory.ts` sobre la conexión existente de Karen Core y política
de comentarios en MusicCommentEngine. La memoria musical usa tablas aditivas,
versionadas y separa escucha estimada de preferencias explícitas. El lector Python
`ContextMemory.music` no promueve observaciones a recuerdos confirmados.

Percepción, historial y comentarios están apagados por defecto. La política conserva
10 % por canción, 45 s escuchados, 35 minutos de cooldown y dos comentarios por
tres horas. La guardia consulta escritorio y datos de uso del micrófono, sin capturar
audio. Apps de comunicación conocidas bloquean de forma conservadora aunque no se
pueda demostrar una llamada. No es un detector universal de llamadas.

Verificación inicial: compilación del puente correcta; `music-native-probe.cjs`
recibió un snapshot real de Windows y una respuesta de contexto, cerrándose por EOF.
Solo se registró el número de sesiones; no se guardaron metadatos del usuario.
Pruebas de clasificación/política/memoria y transporte autenticado correctas.
El complemento usa loopback 18796; los tests de transporte usan un puerto temporal,
con aislamiento de respuestas y rechazo de orígenes web y credenciales ausentes.
Spotify Desktop fue comprobado después con una sesión real: detección, clasificación,
metadatos y minirreproductor correctos. Sus controles de reproducción reales siguen
sin probarse. Spotify Web, Apple Music y YouTube reales siguen sin certificación;
sus pruebas de metadatos son fixtures, no sus cuentas reales.

Referencia primaria: [GSMTC de Microsoft](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssession).

## Uso y preferencias

Ajustes → Música permite habilitar percepción, minirreproductor, plataformas,
filtrado estricto, gestos, reacciones silenciosas en modo Gaming, comentarios,
probabilidad, volumen, cooldown, cuota, historial, borrado y exportación Markdown.
Percepción, comentarios, historial y exportación empiezan apagados. La selección de
sesión es explícita en el reproductor cuando hay varias; sin selección se prioriza
una sesión que está reproduciendo. El minirreproductor se abre desde la mascota,
se mueve por su cabecera y permite anclar, minimizar u ocultar.

Título, artista, álbum y portada aparecen solo cuando se obtienen. Los controles
se deshabilitan u ocultan según capacidades de la sesión. GSMTC no ofrece volumen
por sesión; el complemento puede controlar el volumen del elemento HTML de su
pestaña. No se cambian teclas multimedia globales ni volumen general de Windows.
No se descargan ni extraen audios de plataformas. No se añadió un reproductor de
archivos locales, que era opcional.

Comandos deterministas offline, con o sin «Karen»:

- ¿Qué canción está sonando?; pausa/continúa la música.
- Siguiente canción; canción anterior; sube/baja el volumen.
- Abre/cierra tu reproductor; no comentes la música.
- Me gusta/no me gusta esta canción; recuerda esta canción.

La identificación responde con metadatos conocidos. Si se pide mediante voz, puede
leer esa respuesta con el proveedor existente; no se necesita LLM. Los gestos
musicales usan las capas actuales de Pixi, dos notas discretas y balanceo suave.
No afirman medir BPM, clasificar calma/entusiasmo ni inferir emociones del usuario.
No hay captura de audio ni FFT residente.

## Complemento opcional Chrome/Edge

Carpeta: `extensions/music-presence`. Cargar como extensión sin empaquetar desde
el modo desarrollador del navegador. En Karen activa percepción y genera el código;
cópialo a las opciones del complemento y recarga la pestaña musical. La instalación
en el navegador del usuario no se hizo automáticamente.
El empaquetado incluye esa carpeta fuera de ASAR, en
`resources/app.asar.unpacked/extensions/music-presence`, para que Chrome/Edge puedan
leerla. La configuración se revisó; no se generó un instalador nuevo en esta entrega.

Permiso API: `storage`. Content scripts solo en `open.spotify.com`, `music.apple.com`,
`music.youtube.com`, `www.youtube.com` y `youtube.com`. Acceso de red del background
solo a `http://127.0.0.1:18796`. No se concede `<all_urls>`, tabs, microphone,
tabCapture ni acceso general de navegación. El background obtiene el ID de su pestaña
del remitente, autentica solicitudes y entrega controles solo al cliente y pista
correspondientes. El código se conserva en el almacén DPAPI de Karen y en el storage
local de la extensión; revocarlo corta el canal. No aparece en snapshots ni logs.

YouTube exige categoría Music/10 y un ID de vídeo válido; también YouTube Music
necesita categoría, pues aloja podcasts. Se excluyen los anuncios indicados por el
reproductor y los vídeos ambiguos. En Spotify Web se exige un enlace de canción,
rechazando episodios/podcasts. Si esos datos no están disponibles, la sesión se
omite. Los selectores y Media Session de cada web necesitan aceptación real: su
ausencia reduce cobertura y no se sustituye por una clasificación de LLM.

El canal usa eventos de DOM/media con debounce, heartbeat de metadatos cada 15 s
si existe un elemento multimedia y long polling de comandos, no consultas al modelo.
Las sesiones web caducan si se pierde contacto. No se envía audio y no se recuperan
portadas remotas desde URLs suministradas por páginas.

## Comentarios y memoria

Una evaluación probabilística por reproducción elegible, tras 45 s escuchados.
Se deduplica por pista en la sesión de Karen, con cola reciente de textos, cooldown
y límite de dos por tres horas. Cambiar canción, escritorio protegido, ausencia,
introducción o desactivar comentarios cancela una reacción pendiente/activa.
Las conversaciones y voz tienen prioridad. Apps de comunicación conocidas o un
micrófono indicado como activo bloquean de forma conservadora; no se ha probado
con todas las aplicaciones de llamada ni presentaciones reales.

Se generaron seis comentarios genéricos con la voz local configurada. Reproducción
por AudioDirector y su medidor ya existente, sin TTS para esos clips y con volumen
independiente. Si falta el audio/perfil correcto, la reacción queda visual.

```powershell
npm run generate:intro-greetings -- --settings "$env:APPDATA/karen-desktop-pet/settings.json" --output "$env:APPDATA/karen-desktop-pet/music-comments" --catalog assets/music-comments/catalog.json --resume
```

Los audios y manifiestos locales están fuera de Git. El historial usa Core y requiere
su conexión; no se crea una segunda base de recuerdos. Resúmenes incluyen frecuencias
observadas y gustos explícitos, sin convertir una escucha en preferencia. La operación
READ `music_summary` de Core puede incorporarse al scheduler existente. No se activó
su runner ni se crearon tareas reales. Exportar Markdown abre un diálogo para elegir
el archivo: no se escribe automáticamente en un vault ni se amplían sus permisos.
La escritura periódica automática en Obsidian sigue pendiente de configuración y
aprobación mediante el flujo documental existente.

## Verificación final y límites

- `npm test`: 190 pruebas correctas; `npm run build`: typecheck, Vite, Electron y C#
  correctos. Persiste el aviso previo de tamaño del chunk Pixi.
- `node scripts/music-native-controls.cjs`: sesión GSMTC real, MediaPlayer sintético
  silenciado; play, pause, next, previous, rechazo de volumen y retirada de sesión.
- `node scripts/music-ui-smoke.cjs`: ventanas Electron y HTTP real, control de
  navegador simulado; varias sesiones, cambio de plataforma, seek, IPC aislado,
  filtros, preferencias explícitas y borrado. Cero errores del renderizador.
- Extensión probada en un DOM/Media Session sintético, no en Chrome/Edge del usuario.
- Core: 416 pruebas Python correctas, incluida receta musical READ en scheduler
  temporal. `qa/verify_music_interop.py` verifica escritura Node y lectura Python y
  conserva memoria general al borrar datos musicales.
- `startup-intros-smoke.cjs --checks-only`: Escape de Playwright, persistencia y
  bloqueo gaming correctos después de la integración. Un escritorio protegido puede
  omitir la introducción; el arnés lo distingue de un fallo de renderizado.

Medición de siete segundos, 13 muestras: CPU Electron media/pico 3,024/7,836 %;
suma de working sets 619,90–624,86 MiB incluyendo panel, Pet y reproductor, con
páginas compartidas contadas en cada proceso. Helper GSMTC: 39,06–40,75 MiB y
0,31 % de un núcleo en cinco segundos de suscripción inactiva con sondas de contexto.
Cuatro lecturas globales GPU: 32–38 %, VRAM 1026–1031 MiB; incluyen otros procesos,
no son consumo exclusivo del módulo. No se certifica ausencia de fugas prolongadas.
Datos: [MUSIC_METRICS_2026-11-26.json](MUSIC_METRICS_2026-11-26.json).

Pendientes: pruebas reales por plataforma/cuenta, DOM actual de sitios, llamadas y
sesiones de presentación/juegos reales, aceptación auditiva humana y pruebas de
duración prolongada. No se reemplazó el ejecutable instalado ni se descargaron modelos.

## Aceptación Spotify Desktop real — 2026-11-26

El usuario tenía Spotify reproduciendo. El puente recibió la sesión de la aplicación
de Windows y el clasificador la aceptó como Spotify. El minirreproductor del código
actual mostró título, artista y portada reales, con duración/progreso y el botón de
pausa habilitado según capacidades reportadas. No se pulsó ese control ni se envió
ninguna orden a Spotify. No se guardaron títulos, artistas o historial en el repo.

`node scripts/music-spotify-live.cjs` pasó en un perfil temporal con historial,
comentarios y voz apagados, sin Core conectado. Cierra únicamente su instancia de
QA y elimina su perfil. Por defecto imprime solo indicadores técnicos; `--show-track`
permite ver la pista en consola de forma explícita. No captura pantalla ni audio.
Este resultado acredita lectura y renderizado con Spotify Desktop real, no prueba
de todos sus controles ni de Spotify Web. El ejecutable instalado sigue intacto.
`--keep-open` deja visibles la mascota y el minirreproductor, ocultando los ajustes,
solo después de pasar la comprobación. Mantiene el perfil aislado hasta salir de
esa instancia mediante la bandeja; entonces lo elimina. No cierra otra Karen instalada.
