# Karen — repositorio e integración del runtime

Fecha: 24 de noviembre de 2026.

## Destino correcto

- Repositorio: `https://github.com/Duvetsillo/Karen-assitant`.
- Carpeta: `C:\Users\Dayve\Documents\GitHub\Karen-assitant`.
- La publicación anterior fue a `Duvetsillo/karen-classic-core`, cuyo checkout
  operativo está en `C:\karen`. Esa diferencia explica por qué los cambios no
  aparecían en este repositorio.

## Integración

El código operativo ya validado se incorpora bajo `runtime/`, conservando
`cliente.py`, `config.py`, documentación y pruebas históricas en la raíz.
Los siete commits de la actualización mantienen autoría, fechas y mensajes
al aplicarse a ese directorio. La base anterior se importa como snapshot;
no se mezclan dos clientes con contratos diferentes en los mismos archivos.

Antes de añadir esta documentación se comprobó igualdad exacta entre el árbol
`runtime/` y el commit original `e7a1f1b`: ambos tienen Git tree
`b88c13a04531bf24c84cfdc6d85765e90e558050`.

Las dependencias de código locales usadas en la verificación se enlazan mediante
junctions ignorados por Git. No se copian modelos, archivos privados, configuración
de usuario ni los cambios de Home Assistant que seguían sin commit en `C:\karen`.

## Validación

- Evidencia anterior: 333 pruebas correctas sobre código limpio en Python 3.11.
- Suite Windows desde `runtime/` en esta carpeta: **333 pruebas OK, Python 3.11,
  60.844 s**.
- Cliente histórico: **4 pruebas pytest OK, 0.03 s**; `python cliente.py --help`
  correcto. `cliente.py`, `config.py` y `tests/` conservan su contenido anterior.
- CI portable de la raíz: limitada explícitamente a las pruebas históricas en
  `tests/`, evitando mezclar módulos `config` y dependencias Windows del runtime.
- Comandos, límites y siguientes fases: `runtime/docs/PERSONAL_AI_UPGRADE.md`.

## Siguiente tarea

Continuar el desarrollo y publicar los próximos cambios en este repositorio.
La siguiente fase funcional de Karen sigue siendo full-duplex con AEC comprobable
y STT incremental, según el registro del runtime. La integración utiliza avance
normal de `main`, sin forzar el push ni sustituir su historial anterior.

## Prioridad del usuario — Desktop Pet y memoria personal

El usuario aclaró que usa principalmente Desktop Pet y no quiere centrar la
evolución en el cliente verde. Se prioriza el puente de memoria y la futura
sección «Mis datos» del Pet, conservando los clientes existentes.

Añadido `runtime/personal_learning.py`: perfiles propios registrados por
instrucción explícita, observaciones con procedencia y fecha, y afirmaciones
públicas no confirmadas separadas del contexto verificado. No reentrena modelos,
no inicia sesiones, no hace scraping ni transmite recuerdos automáticamente.
Datos de incorporación, informes y respaldo de la base operativa permanecen
fuera de Git. Las pruebas y documentación utilizan ejemplos sintéticos.

`start_pet.ps1` lee la base compartida de la configuración persistente de Windows
y permite iniciarlo sin abrir Tkinter. La guía `docs/PET_PERSONAL_MEMORY.md`
explica consultas y transferencias explícitas. La recuperación automática y el
panel visual de fotos/documentos todavía no están integrados en el Pet.

Validación de esta fase: 9 pruebas nuevas de fuentes; regresión completa del
runtime **342 OK, Python 3.11, 60.508 s**; puente Core/Gateway de Pet **34 OK**;
cliente histórico **4 OK**. El lector real del Pet pudo consultar recuerdos
persistidos en la base operativa desde otro proceso. Lanzador validado sin abrir
la aplicación y con rechazo de base ausente. No hubo transmisión al Gateway,
inferencia sobre rasgos sensibles ni entrenamiento de pesos. El informe de datos
incorporados y su respaldo quedan en almacenamiento privado, no en esta guía.

## Apariencia y animaciones de Pet

Prioridad confirmada por el usuario: apariencia y animaciones de la mascota.
El código completo de Desktop Pet está ahora en `pet/`, dentro de este
repositorio. El lanzador de la raíz prefiere esta carpeta.

Se conserva la identidad de cristal: contorno más definido, cara profunda,
reflejos de ojos y corazón independiente. El movimiento tiene respiración,
inclinación con resorte y saludo breve. Apariencia añade tres ritmos y una
vista previa sobre fondo claro u oscuro. Se mantienen los límites de Gaming,
reposo y movimiento reducido. El panel «Mis datos» sigue pendiente.

Validación: 170 pruebas de Pet aprobadas, compilación TypeScript/Vite correcta
y revisión visual en 1280×720 y 820×640, incluyendo saludo, reposo y ambos
fondos. La advertencia de tamaño del paquete Pixi continúa sin impedir la
compilación. Los datos personales y credenciales permanecen fuera de Git.

## Recuperación de voz — Pet 1.8.1

El aviso compartido por el usuario procede de la activación por voz, no del
motor de síntesis. En la instalación local, el modelo de reconocimiento pudo
cargar y procesar silencio sintético en un proceso real. Una prueba adicional
de TTS Windows → PCM → Whisper terminó sin usar ni reproducir el micrófono,
con errores de transcripción; no constituye aceptación acústica.

Corregidos el cierre definitivo ante fallos transitorios del grabador y la
pérdida de su causa entre Pet y Ajustes. Los reintentos son acotados, respetan
el bloqueo entre interfaces y descartan grabaciones fallidas. Un micrófono
guardado ausente conserva su selección visible. Los avisos anteriores se
limpian al recuperar la escucha sin borrar errores ajenos de conversación.

Validación: **176 pruebas de Pet aprobadas en 27 archivos**, comprobación de
tipos y compilación correctas. La instancia nativa de prueba mostró la causa
real de bloqueo de micrófono. La guía `pet/docs/VOICE_TROUBLESHOOTING.md`
describe recuperación y aceptación física. Ajustes y almacén DPAPI respaldados
localmente; ningún dato de usuario se incorpora a los commits.

Límites: el fallo físico original no se ha reproducido con el micrófono del
usuario. Se observó poca RAM/VRAM libre; no se forzó una inferencia Qwen bajo
esa carga ni se modificaron programas externos. Siguen pendientes AEC e
interrupción vocal verificables, STT incremental y la sección de datos propios.

Entrega local comprobada: instalador NSIS 1.8.1 terminó con código 0 y Pet se
reinició desde su ruta instalada habitual. El paquete instalado, preload y
worker coinciden con la compilación. `settings.json` y `vault.dpapi` conservaron
sus hashes. Pasaron también 26 contratos Python de voz. El instalador local
permanece en `pet/release/`, fuera de Git; no se publicó una release remota.

Preferencia persistente del usuario: commits/push durante el trabajo y registro
continuo en Obsidian. Se añadió `AGENTS.md`; la bitácora y el índice de la
colección existente de Desktop Pet reflejan esta entrega y sus pendientes.
