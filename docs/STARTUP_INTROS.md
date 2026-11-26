# Introducciones de inicio — 2026-11-26

Motor local Electron/React/Pixi. Seis secuencias: Breakthrough, Glass, Awakening,
Materialization, Sleepy y Surprise. Reutiliza `PetRenderer` y sus diez texturas
procedurales por apariencia; no cambia los ocho estilos, la voz, la memoria ni Core.

## Uso

Apariencia → Introducciones de inicio permite activar, seleccionar una entrada
aleatoria/fija/contextual, previsualizar, controlar saludo, efectos, volumen,
movimiento reducido, Escape, monitor y 30/60 FPS. Usa el `settings.json` existente.
La selección contextual depende de la hora local; aleatoria evita repetir la anterior
dentro del proceso. Solo el primer `ready-to-show` del Pet dispara el arranque.
Reconexiones, resume y segunda instancia no reproducen otra entrada.

Comandos deterministas de escritorio, también con Gateway desconectado:

- «Karen, reproduce tu introducción».
- «Karen, cambia tu introducción».
- «Karen, reproduce Awakening» (también cualquiera de los otros cinco nombres).
- «Karen, usa introducciones aleatorias».
- «Karen, desactiva los saludos de inicio» (silencia la voz de estas entradas).

## Responsabilidades

- `electron/startup-intros.ts`: StartupIntroManager, ventana independiente,
  monitor en coordenadas DIP, preparación, handshake, watchdog y restauración.
- `shared/startup-intros.ts`: IntroRegistry, preferencias, enrutador y IntroTimeline.
  La transición final interpola al centro y escala que usa el Pet habitual.
- `src/intros/IntroRenderer.ts`: AvatarAdapter para las capas ya existentes,
  efectos 2D, tiempo monotónico, expresiones y cierre de la reproducción.
- `src/intros/AudioCueManager.ts`: audio WAV precargado, reloj de Web Audio para
  la boca y un efecto sonoro breve creado en memoria. Nunca sintetiza voz.
- `electron/greeting-library.ts`: GreetingLibrary, versión de voz y ResourceCache
  acotado por reproducción. Ausencia/corrupción de recursos produce una entrada muda.
- `electron/intro-guard.ts`: guardia Windows limitada a la duración de la entrada.

La capa es transparente, sin bordes, sin foco y siempre deja pasar el ratón.
No necesita capturas: las grietas, fragmentos y bandas digitales son geometría
superpuesta. No modifica ni lee píxeles del escritorio. El foco previo se conserva
al no activarse la ventana. Escape usa la guardia nativa de Windows y un listener
local de teclado. Al cerrar no quedan superficies, audio ni temporizadores del motor.

Antes de crear la capa se consulta SHQueryUserNotificationState y el rectángulo
del foreground. Se omite ante pantalla completa, presentación, gaming o No molestar;
si la consulta falla se omite también. Durante la reproducción se siguen comprobando
Windows y Escape. La propia capa puede causar QUNS_BUSY: solo se tolera ese estado
con el foreground original intacto y sin fullscreen. Bloqueo, suspensión, cambio
de monitor, cambios de preferencias y recuperación de bandeja cancelan la entrada.

En el monitor habitual la llegada coincide con la mascota real. Si se elige otro
monitor, el destino se calcula en el espacio virtual y puede salir de los límites
de la capa antes de reaparecer en el monitor de origen. No se extiende una ventana
sobre todos los monitores. La validación física de esta variante sigue pendiente.

## Voz pregenerada

El catálogo de `assets/startup-greetings/catalog.json` contiene 40 textos en nueve
categorías. Los audios se guardan en `<userData>/startup-greetings`, fuera del repo.
Cada entrada del manifiesto incluye archivo, texto, duración, categoría, intros,
versión de proveedor/perfil/estilo, envolvente RMS normalizada y paso de 20 ms.
La versión debe coincidir con la configuración activa; no se sustituye la voz.
La boca lee estos datos con el reloj de reproducción, sin modelos de lip sync.
Sleepy usa la categoría horaria y Surprise prioriza humor. Las demás categorías
quedan disponibles en la biblioteca para futuras reglas de selección.

Generación explícita fuera del arranque, con el proveedor y estilo de los ajustes:

```powershell
npm run generate:intro-greetings -- --settings "$env:APPDATA/karen-desktop-pet/settings.json" --output "$env:APPDATA/karen-desktop-pet/startup-greetings" --resume
```

El generador rechaza Edge o un perfil local ausente, sin sustituir la voz ni
descargar modelos. Reutiliza NativeVoice y el servicio local existente. Valida WAV
PCM, obtiene la envolvente y publica el manifiesto de forma atómica tras cada
saludo. `--resume` vuelve a analizar los WAV existentes y reutiliza solo coincidencias
de texto y versión. La síntesis offline puede usar el modelo de voz ya instalado;
el reproductor de introducciones nunca lo consulta.

En este equipo se generaron y validaron los 40 WAV con la voz original configurada,
estilo serene, y se copiaron al directorio local de reproducción. No se distribuyen
referencias privadas ni audios en Git. Una instalación distinta necesita generar
su biblioteca; el motor funciona en silencio si no está disponible.

## Referencias estudiadas

- [Capri Desktop](https://github.com/lachydotmcg/capri-desktop): `app/ArtIntros.cs`
  y `app/MainframeIntros.cs`: contrato de intro, preparación de recursos, tiempo,
  dibujo, selección y liberación de superficies.
- [Startup Intros](https://github.com/lachydotmcg/capri-mods/blob/main/mods/startup-intros/startup-intros.capri-code):
  Start/Begin/Draw/Stop, duración por secuencia, señales una sola vez, imágenes
  reutilizadas y llegada hacia el rectángulo de la mascota. El mod ofrece Hijack,
  Shatter y Wake; sus geometrías de personaje son específicas de Capri.
- [Licencia de Capri](https://github.com/lachydotmcg/capri-desktop/blob/main/LICENSE.md):
  PolyForm Noncommercial 1.0.0, con avisos de atribución. No se encontró LICENSE
  explícita en la raíz de capri-mods. Esta implementación es propia: no incorpora
  código, trazados, recursos, sonidos ni identidad de Capri.

## Verificación y mediciones

`npm test`: 179 pruebas correctas. `npm run build`: typecheck, Vite y Electron
correctos, con el aviso conocido de tamaño del chunk Pixi. Prueba nativa con perfil
temporal: seis reproducciones a tiempo real y 48 combinaciones intro/apariencia
con reloj acelerado, todas con restauración de coordenadas y dos ventanas al acabar.
Las 54 reproducciones de la pasada final cargaron el saludo y su WAV. Escape de
Playwright, persistencia tras reiniciar, aislamiento de IPC y modo gaming pasaron.
El arnés inicialmente trató el cierre por Escape como error al enviar key-up sobre
una ventana ya destruida; la pasada final ya incluye esa comprobación corregida.
El cierre normal desmonta React/Pixi y libera las texturas antes de destruir la
ventana; cancelaciones nativas destruyen su WebContents y su guardia acotada.

Comandos reproducibles, con perfil de QA temporal y sin acceso a bases del usuario:

```powershell
npm test
npm run build
node scripts/startup-intros-smoke.cjs --matrix
```

El smoke usa `.private/startup-greetings` cuando existe; copia únicamente los audios
y metadatos del perfil a un directorio temporal. No inicia modelos ni Gateway.
Las capturas PNG contienen solo la superficie generada, con transparencia; no se
captura el escritorio. Resultados locales en `qa/startup-intros`, ignorado por Git.

Medición final: Windows 11/Electron 44.7.2, 1920×1080; 58–59 FPS en las seis
reproducciones a tiempo real. 218 muestras de procesos Electron: CPU media 3,996 %,
pico 9,071 %; suma de working sets 305,39–812,44 MiB, 635,08 MiB tras tres segundos
de reposo después de la matriz. Incluye panel y mascota, reinicio del perfil de QA
y páginas compartidas contadas en cada working set; no es RAM exclusiva de la intro.

75 muestras de nvidia-smi: GPU 4–44 %, VRAM 648–913 MiB. Son lecturas del adaptador
completo compartido y no permiten atribuir ese consumo exclusivamente a Karen.
No se afirma ausencia de fugas a largo plazo a partir de estas cifras. Sí se
comprobó que cada reproducción deja exactamente las dos ventanas habituales.
Datos resumidos: [STARTUP_INTRO_METRICS_2026-11-26.json](STARTUP_INTRO_METRICS_2026-11-26.json).

No se reemplazó el ejecutable instalado. Quedan pendientes la aceptación visual y
auditiva humana, Escape físico, juegos/presentaciones reales y monitores/DPI físicos
distintos. Contratos y Playwright no sustituyen esas comprobaciones.


## Nitidez, saludo y salida — 2026-11-26

Las texturas conservan su tamaño lógico y se rasterizan según pantalla/DPI.
Awakening reserva más detalle para los ojos (8× en la prueba 1920×1080), con
mipmaps; el cuerpo y la boca aparecen al terminar el primer plano. Presupuesto
máximo de 48 MiB de píxeles RGBA fuente, excluyendo copias del driver y mipmaps.
No equivale a una medición de RAM. El escritorio mantiene su resolución habitual.

El regreso prepara la mascota transparente, espera su fotograma y la revela antes
de liberar la ventana de introducción; IPC limitado al frame y token esperado,
con recuperación de 700 ms y watchdog. El saludo sigue el reloj real de audio,
reintenta una salida suspendida y respeta el dispositivo de salida configurado.
Apariencia muestra si existe una biblioteca compatible; no genera voz al arrancar.

La despedida dura 780 ms (180 ms con movimiento reducido), con guiño, gesto y
fundido. Tiene límite nativo de 1200 ms; una mascota oculta o un cierre de sesión
no esperan la animación. Se puede desactivar en Apariencia. Escape puede omitirla
cuando el renderer recibe la tecla; no se registra un atajo global nuevo.

Verificación: 197 pruebas Pet, typecheck, Vite y compilación Electron correctos.
Se reutilizó el puente musical ya compilado para conservar abierta la instancia
musical del usuario. Matriz nativa: seis secuencias con audio local a tiempo real
(58–59 FPS) y 48 combinaciones visuales con reloj acelerado, sin errores; persisten
los ajustes y se omiten en modo gaming. `scripts/polish-smoke.cjs` comprueba tres
formas de chat a 50/100 %, texto largo y multilingüe sintético, editor multilínea,
envío offline, Más opciones/Escape, calidad y despedida real (~961 ms incluyendo
50 ms de espera de QA). Datos resumidos: POLISH_ACCEPTANCE_2026-11-26.json.

Chat: Globo, Panel o Cinta en Apariencia, con entrada breve y movimiento reducido.
Editor Enter para enviar, Shift+Enter para nueva línea y Escape para cerrar;
conserva borradores editados durante el envío y bloquea envíos duplicados. La
conversación deja de seguir respuestas si se está leyendo arriba. Los accesos
secundarios están en Más opciones. Se conservan las ocho apariencias.

Pendiente: audición humana del saludo, aceptación de ambas salidas y monitores
físicos HiDPI/4K; el presupuesto 4K está cubierto por pruebas de cálculo. El paquete
instalado sigue sin reemplazarse; la vista ejecutada procede del repositorio.
