# Karen Desktop Pet 1.7.0 — variantes, reposo y respuesta de voz

Fecha local: 2026-11-01, America/La_Paz. Código incremental sobre Karen existente;
no se reemplazaron modelos, identidad vocal, proveedores ni mecanismos de permisos.

## Funciones terminadas

### Apariencia y extremidades

Ocho estilos reales: Cristal, Nube, Órbita, Lucero, Flor, Aurora, Ámbar y Nocturna.
Aurora añade silueta de gota y acabado jade; Ámbar, forma de cometa y reflejos
cálidos; Nocturna conserva la forma lunar con un acabado más oscuro.
Los cinco estilos anteriores siguen disponibles.

En **Apariencia → Su silueta**:

- **Completa:** brazos y piernas.
- **Sin brazos:** conserva piernas.
- **Flotante:** sin brazos ni piernas.
- Interruptores independientes **Mostrar brazos** y **Mostrar piernas**.
- Botón **Ocultar brazos y piernas**.

El botón con figura humana de la barra de Karen alterna el cuerpo completo y
el flotante. Su estado se comunica con `aria-pressed`. Los controles se
distribuyen en dos filas cuando la ventana es pequeña para conservar su tamaño.
Las miniaturas, el renderizador y sus etiquetas accesibles reflejan la selección.
Los brazos ocultos también dejan de participar en la máscara de interacción:
no quedan zonas invisibles del brazo capturando el ratón.

Las ocho formas admiten las cuatro combinaciones de extremidades: 32 combinaciones
de estilo/cuerpo, además de los colores, tamaño y controles existentes. No se
crearon asistentes, memorias o conexiones independientes por apariencia.

Capturas del renderizador real, no mockups:

| Completa | Sin brazos | Flotante |
| --- | --- | --- |
| ![Karen con brazos y piernas](../desktop-pet/qa/variants/with-arms-and-legs.png) | ![Karen sin brazos](../desktop-pet/qa/variants/without-arms.png) | ![Karen flotante](../desktop-pet/qa/variants/without-arms-and-legs.png) |

| Aurora | Ámbar | Nocturna |
| --- | --- | --- |
| ![Aurora](../desktop-pet/qa/variants/aurora.png) | ![Ámbar](../desktop-pet/qa/variants/ember.png) | ![Nocturna](../desktop-pet/qa/variants/midnight.png) |

### Actividades de reposo

En **Comportamiento → Cuando tiene un rato libre** se puede activar/desactivar
el entretenimiento, elegir una actividad o alternarlas y ajustar la espera
entre 15 y 300 segundos. La intensidad usa el nivel de actividad existente.

Karen puede jugar con una luz que rebota, estirarse o mirar una constelación.
Son animaciones decorativas dentro de su ventana: no abren juegos externos,
no usan IA, micrófono o capturas y no realizan tareas del sistema.
No se presentan como trabajo ejecutado por un agente.

La espera predeterminada es 30 segundos. Los clips duran 8,5/6,5/10 segundos;
entre clips descansan de 60 a 100 segundos según la intensidad. No hay otro
bucle de animación ni llamadas periódicas al modelo. La máquina principal
del asistente mantiene la autoridad sobre escucha, pensamiento, voz y errores.

Se suspenden ante captura activa, respuesta pendiente, señalamiento, trabajo
activo comunicado por Core, arrastre, estados no IDLE, reposo y ventana oculta.
También se desactivan con actividad cero, movimiento reducido, bajo consumo,
Gaming y No molestar. Al volver a mostrar la ventana se espera de nuevo: no
se reproduce de golpe un juego atrasado. Cambiar ajustes cuenta como interacción.
Estos mecanismos no sustituyen un motor de automatizaciones u objetivos persistentes.

![Juego con una luz](../desktop-pet/qa/variants/idle-play.png)
![Constelación](../desktop-pet/qa/variants/idle-stargaze.png)

## Respuesta y recursos

- Primera frase local: umbral de 40 caracteres en una oración completa;
  siguientes clips mantienen 70 y máximo 240 caracteres. No se separan saludos
  cortos ni se omite texto. El siguiente clip se prepara durante la reproducción.
- Se solicita precarga de voz también al detectar la palabra de activación.
  Se conserva la restricción de no precargar en bajo consumo o con voz desactivada.
- Karen clásica ahora cierra su propia conexión HTTP TTS al cancelar, incluso
  esperando cabeceras o cuerpo. El servicio cancela entre frames sin detener
  otras conexiones. No es barge-in ni cancelación del modelo de conversación.
- Renderizado en reposo limitado a 24 FPS; bajo consumo, movimiento desactivado,
  movimiento reducido o sueño, a 12. Escucha/voz/operaciones conservan hasta 60.
  Una ventana oculta detiene el ticker. No se añadieron dependencias gráficas.

Prueba real de cancelación clásica: retorno al cliente **0,058 s**, recuperación
del servicio **0,138 s**, síntesis posterior válida. Sin reproducción ni micrófono.
La referencia original `karen-original-v2` permanece intacta.

En el primer ensayo del mismo texto y voz local con modelo caliente, el comienzo
de reproducción pasó de **7,624 s** en 1.6.8 a **2,887 s** en la fuente 1.7.0.
Se mide desde recibir el mensaje final hasta comenzar el audio; no incluye STT
ni espera del proveedor de conversación. Texto sintético, salida silenciada,
ambas primeras síntesis sin caché. La división cambia la prosodia y la duración
total del WAV; no es una comparación de waveforms idénticos ni una garantía
de tiempo para cualquier respuesta. El primer ensayo coincidió con otra prueba
gráfica aislada; se conserva una segunda comparación controlada contra el EXE.

Segunda comparación, ejecutada secuencialmente sin otro smoke gráfico:
**6,475 s → 2,920 s** hasta primer audio, 1.6.8 frente al EXE 1.7.0,
aproximadamente **55 % menos espera** para ese texto. Ambas primeras síntesis
sin caché y decoder GPU; 1.7.0 continuó la segunda oración tras 83 ms y terminó
la reproducción a los 12,226 s. Su cancelación posterior recuperó el servicio
en 0,387 s. Resultados `accelerated-voice-baseline-170-controlled.json` y
`accelerated-voice-packaged-170-controlled.json`, dentro de `desktop-pet/qa`.
La preparación fría del modelo continúa siendo un coste separado; no desaparece.

En la prueba visual de fuente se observaron **21 FPS** en reposo (techo 24) y
`percentCPUUsage` de **0,387 y 0,383** en los dos procesos renderer durante una
muestra corta. Se conservan los campos CPU/memoria originales de Electron en
el JSON de resultados; no se extrapolan a consumo eléctrico o estabilidad de horas.

## Pruebas y reproducción

```powershell
cd C:\karen\desktop-pet
npm test -- --reporter=dot
npm run test:voice:contracts
npm run build
npm run test:variants
npm run test:styles
npm run test:voice:accelerated
cd ..
& .\expressive-runtime\Scripts\python.exe .\qa\verify_classic_voice_cancel.py
```

Unitarias: 143 TypeScript Pet, 25 contratos Python de voz, 165 clásicas.
La cancelación HTTP se prueba también con sockets de loopback reales sin modelo,
antes de conectar, esperando cabeceras y esperando cuerpo. Las pruebas del
planificador de reposo cubren prioridad, accesibilidad, reloj corregido y suspensión.

`test:variants` usa Electron/WebGL reales, perfil y base Core temporales, STT/wake
apagados y sin Gateway. Compara píxeles de brazos y piernas, recorre las ocho
formas, tamaños 50/100/200 %, espera los tres pasatiempos reales, comprueba
prioridad/reduced-motion/visibilidad y reinicia para verificar persistencia.
La salida no contiene preferencias o conversaciones del perfil habitual.

`test:voice:accelerated` sí usa el Qwen local real con texto sintético y volumen
cero. El mensaje final se inyecta en QA: no prueba un diálogo real con el Gateway.
No se atribuye una mejora a la generación de texto de OpenClaw/Ollama.

Resultados locales: `desktop-pet/qa/variants/source-results.json`,
`desktop-pet/qa/variants/packaged-results.json`,
`desktop-pet/qa/accelerated-voice-*-170*.json`,
`qa/classic-voice-cancel-20261101.json`. Las imágenes se regeneran con el smoke.

## Inicio y compatibilidad

Código fuente: `cd C:\karen\desktop-pet; npm run dev`.
Windows empaquetado: `release/variants-170-20261101/win-unpacked/Karen Desktop Pet.exe`.
Cerrar la Pet anterior antes de abrir otra compilación con el perfil habitual.
El instalador se encuentra en
`desktop-pet/release/variants-170-20261101/Karen Desktop Pet Setup 1.7.0.exe`.

Se mantienen los perfiles/proveedores/credenciales existentes. Los ajustes
anteriores reciben valores predeterminados para los nuevos campos sin borrar
voz, tamaño, estilo o conexiones. El overlay TTS y modelos siguen en `C:\karen`;
el instalador no descarga ni incorpora otra copia de esos modelos.
El paquete completo no se instala automáticamente sobre la aplicación abierta.
La cancelación clásica sí está disponible desde el código de este repositorio.

Instalador NSIS x64 final: **129223350 bytes**, SHA-256
`A9EB0786D78A0E9DFE3A35C585775ABD98E0D9E2FCB03EDFDDEB167FF7F87D0A`.
Compilación local sin firma, sin publicación. La ejecución del EXE se verifica
por separado del flujo de instalación/desinstalación; no se presenta el segundo
como probado por haber construido el instalador.

El smoke completo pasó también en el EXE final 1.7.0: ocho estilos, tres
actividades, comparación de píxeles, controles a tres escalas, persistencia,
movimiento reducido y ocultar/mostrar nativo, sin errores renderer. Observó
22 FPS en reposo y valores CPU 0,381/0,387 por renderer en esa muestra.
La regresión visual adicional recorrió 15 estados de demostración en cada uno
de los ocho estilos (120 combinaciones), navegación por teclado y persistencia.
Esos estados son simulaciones visuales; no ejecuciones reales de agentes.

La recuperación de visibilidad incorpora una señal tipada de Electron por
ventana: no depende únicamente de que Windows entregue Page Visibility a tiempo.
El respaldo final se conserva en `backups/delivery-pet-170-20261101` e incluye
fuente/datos y una selección de capturas de revisión, con hashes verificados.

## Reversión

Respaldo previo: `backups/before-pet-variants-20261101`, verificado con maintenance.py.
No se migraron las bases ni se modificó el perfil productivo durante los smokes.
Antes de instalar/revertir, cerrar Karen y respaldar su directorio real `userData`,
incluidos ajustes y blobs DPAPI sin descifrarlos, además de los datos Core.

Para retirar solo esta entrega, revisar source.zip en otro directorio y restaurar
los archivos afectados, preservando cambios ajenos. Reinstalar/abrir la compilación
anterior si se había instalado 1.7.0. No sobrescribir historiales nuevos.

Si se seleccionó una forma nueva, una versión antigua no la reconocerá: cambiar
Aurora/Ámbar a Cristal y Nocturna a Órbita antes de regresar. O restaurar solo los
ajustes anteriores tras respaldar los actuales. Los campos nuevos que una versión
antigua ignore no requieren borrar otros ajustes. No se modificó ninguna política
de autorización, servidor de red, integración doméstica o servicio personal.

## Límites

El asistente autónomo completo continúa pendiente. No se añadieron VAD/barge-in,
PCM continuo, una nueva memoria o automatizaciones reales a través de estos juegos.
No se verificó suspensión de Windows, micrófono desconectado, funcionamiento sin
GPU o estabilidad de varias horas en esta continuación. Persiste el aviso de tamaño
del chunk PixiJS. El paquete local no tiene firma digital.
