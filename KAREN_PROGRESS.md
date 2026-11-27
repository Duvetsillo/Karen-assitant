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


## Integración de Pet — 26 de noviembre de 2026

Por indicación del usuario, este vuelve a ser el repositorio canónico. Se incorporó
el subtree Pet desde `karen-desktop-pet/codex/karen-core-2` (`f9d0f24`), manteniendo
los cambios propios de 1.8.1: recuperación de voz, presets, corazón y movimiento.
Se integran introducciones, música, metadatos Core y chat. Los conflictos de
Renderer, texturas y Apariencia se resolvieron conservando ambos comportamientos;
el corazón participa ahora en el ocultado inicial y la resolución adaptativa.

Verificación combinada: 210 pruebas Pet; typecheck y build completo, incluido
helper musical C#, correctos. Datos locales y modelos no se incorporan. El trabajo
de interfaz y la integración actual del runtime continúan en esta carpeta.


## Runtime consolidado — 26 de noviembre de 2026

Se incorporó el delta de Core `e7a1f1b..876024c` bajo `runtime/` mediante aplicación
tridireccional. Se conserva personal_learning.py y sus nueve pruebas propias.
Incluye memoria/importación portable, Obsidian acotado, scheduler READ optativo,
eventos/handoff, política de recursos, MusicMemory y trabajo Home Assistant ya
versionado. No se desplegó ni activó ningún servicio, runner o integración.

Los verificadores buscan `../pet` en esta distribución y siguen admitiendo la
estructura histórica. AGENTS de raíz/runtime identifica este repositorio canónico.

Validación ejecutada aquí: **425 pruebas Python OK**, 87,304 s, usando el entorno
Python 3.11 existente sin copiarlo. Las tres pruebas de interoperabilidad Core/Pet,
metadatos sin payload y música Node/Python pasan con bases temporales. No se
modificaron datos reales ni se ejecutaron planes. Los 210 tests Pet y su build
completo pasaron en la integración anterior. El cliente histórico permanece intacto.


## Interfaz integrada — 26 de noviembre de 2026

Navegación agrupada por uso, búsqueda con Ctrl+K y acentos ignorados, recuperación
cuando no hay resultados, iconos propios y panel lateral con navegación desplazable
independiente. Conserva identidad, ocho formas, presets y vista sobre claro/oscuro.
Conversación extraída a componentes: borrador retenido entre pestañas, mensajes
largos y código legibles, copia explícita y acotada en Windows (sin lector de
portapapeles expuesto), paginación, lectura sin saltos y regreso al final. Accesos
rápidos solo rellenan el editor; no ejecutan órdenes ni transmiten datos.

Introducciones separa escena, audio y opciones avanzadas; Música agrupa plataformas
y oculta el emparejamiento avanzado hasta solicitarlo. Todos los controles conservan
su funcionalidad. Movimiento reducido y salida de errores existentes preservados.

Verificación: 210 pruebas Pet, typecheck/Vite/Electron, auditoría de fuentes y QA
nativa de diez secciones en 1120×800 y 820×640. Se probaron búsqueda con teclado,
borrador, 65+ mensajes sintéticos, paginación, scroll, copia real con API asíncrona,
salida HTML tratada como texto, código largo, movimiento reducido y secciones
avanzadas. QA Pet: seis variantes, Awakening 8× (~24,95 MB RGBA fuente), despedida
1060 ms y cero errores. Los resultados de UI usan datos sintéticos y no certifican
voz física. Se añade CI del Pet en la raíz: GitHub no ejecuta workflows anidados.

El código se publica en `Duvetsillo/Karen-assitant`, rama `main`. Los checkouts
antiguos quedan conservados. No se cambian modelos, datos privados ni instalación.


Entregas publicadas en main: `65f9c28` (integración Pet), `8dfa530` (runtime) y
`d1ee1c3` (interfaz). Se confirma igualdad de HEAD remoto con `git ls-remote` tras
cada publicación; ya aparecen en el repositorio que utiliza el usuario.
El cierre documental añade CI operativo del Pet y guía de revisión. Pruebas
adicionales: 26 contratos Python de voz y cuatro tests del cliente histórico OK;
YAML de CI parseado. La ejecución de GitHub Actions se distingue de estas pruebas
locales: no se declara aprobada por haber añadido el workflow.

Quedó abierta `Karen · Revisión de interfaz`, ejecutada desde `pet/` con un perfil
temporal sin datos, historial musical ni conexión al modelo. La instancia del
usuario se conserva; no se instaló ni reinició su ejecutable. Para revisar de nuevo:
`cd pet; node scripts/open-interface-review.cjs`. El inicio normal sigue disponible
en `start_pet.ps1` con la base y recursos locales existentes. La revisión no genera
saludos ni copia modelos o credenciales. La aceptación física de voz sigue pendiente.


## Experience Update — fase 1, 26/11/2026

Auditoría y nuevo encargo en pet/docs/EXPERIENCE_UPDATE.md. Inicio centrado en
Presencia, tokens centralizados y centro de control modular. 210 pruebas Pet,
typecheck/Vite y QA nativa de 17 secciones en dos resoluciones correctos.
Próximo bloque: prioridades/estados y scheduler de comportamientos. El usuario
solicita actualizar el ejecutable del escritorio al concluir todas las fases.


## Experience Update — fase 2, 26/11/2026

Primer incremento fed51db publicado. Ahora: avatar siempre flotante, treinta
estados, prioridades y mezcla de poses, cinco niveles de actividad, idle variable
y cuatro frecuencias de saludo. 216 pruebas Pet y QA nativa de treinta estados,
ocho estilos, escalas, persistencia y reposo correctas. Detalles y límites en
pet/docs/EXPERIENCE_UPDATE.md. Próximo: cápsula musical y después manager/router.
El ejecutable del escritorio se actualizará al concluir la entrega completa.
