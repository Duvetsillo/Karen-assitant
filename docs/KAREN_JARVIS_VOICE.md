# Karen Jarvis — restauración de voz local

Fecha: 19 de noviembre de 2026. Solicitud: voz femenina, elegante y calmada.

## Causa y solución

La nueva vista Jarvis enviaba y mostraba texto, pero no solicitaba síntesis ni
reproducía audio. El chat móvil habitual tenía lectura del navegador; Jarvis no
estaba conectado al motor local existente.

Ahora Jarvis lee automáticamente las respuestas con la identidad original
`karen-original-v2`, una voz femenina adulta en español latinoamericano neutral.
Usa el estilo existente `serene`: ritmo ligeramente pausado y timbre suavizado.
No se genera una identidad nueva ni se sustituye la referencia. La apreciación
de «elegante» es subjetiva; el botón de prueba permite escuchar el resultado.

Se conserva Qwen3-TTS local y el servicio compartido con escritorio/Pet. No usa
SpeechSynthesis del navegador, servicios cloud, voces remotas ni modelos nuevos.
Los ajustes guardados y la personalización de voz anterior no se sobrescriben.

## Controles

- **Voz: activa / silenciada**: lectura automática, guardada como preferencia del navegador.
- **Probar voz**: reproduce «Hola. Estoy aquí contigo.» con el perfil y estilo locales.
- **Detener**: para este audio y cancela su solicitud de síntesis, sin detener otros clientes.
- **Escuchar**: aparece en cada respuesta de Karen y permite volver a leerla.

La voz sale por el dispositivo de audio del navegador en el equipo que abre la
página. En el iPhone se escucha en el iPhone; en la ventana del escritorio, en
la salida seleccionada para Edge/Windows. No se reproduce adicionalmente en el
servidor del PC. Un navegador puede necesitar un clic en **Probar voz** o
**Escuchar** antes de permitir audio. La activación se realiza mediante Web Audio
desde un gesto del usuario; los rechazos se muestran, no se ocultan.

## Memoria en una GPU de 6 GB

La prueba completa detectó que mantener los pesos de voz cargados impedía
generar la siguiente respuesta cuando RAM/VRAM estaban casi agotadas.

El puente móvil libera los pesos de voz inactivos antes del razonamiento.
El servicio conserva la identidad y su caché pequeña de audio. Antes de
sintetizar, el puente adquiere el bloqueo de inferencia Python y descarga los
modelos residentes de Ollama. De esta manera alterna chat y voz en este flujo,
en lugar de forzar ambos modelos grandes sobre la misma VRAM.

La nueva operación interna `/release` está autenticada, verifica el perfil y
rechaza liberar el motor cuando está sintetizando. No cambia las operaciones
anteriores `/speech` y `/prepare`. Otros programas que usan Ollama o voz fuera
de este puente conservan sus comportamientos; esto no constituye un planificador
global de GPU para todas las aplicaciones.

En una prueba real, la VRAM disponible pasó de 424 673 280 a 5 034 213 376 bytes
al liberar la voz. La siguiente conversación local se completó correctamente.
La primera síntesis de la prueba tardó 55,14 segundos para 2,47 segundos de audio.
La recarga de pesos puede volver a costar tiempo al alternar. Las frases en la
caché son más rápidas; no se promete latencia instantánea.

## Transporte y límites

- `POST /api/speech`: WAV local con identificador de solicitud y hasta 1200 caracteres.
- `POST /api/speech/cancel`: cancelación por identificador, ligada a la sesión autenticada.
- Se conservan las comprobaciones de cookie, Host y Origin del servidor móvil.
- La web divide la lectura en fragmentos cortos, los reproduce en orden y permite detenerlos.
- Una solicitud de síntesis activa por puente; sin cola ilimitada. Identificadores ya
  atendidos o cancelados no vuelven a ejecutarse.
- Tiempo máximo de síntesis de 120 segundos por solicitud y audio limitado a 24 MB.
- No se guardan textos de voz en logs, memoria de proyectos ni archivos temporales del puente.
  El servicio de voz existente conserva su caché acotada en RAM.
- La web no puede seleccionar otro proveedor, perfil o estilo enviando parámetros adicionales.

## Verificación

- Regresión Karen: 263 pruebas correctas.
- Desktop Pet: 163 pruebas correctas en Vitest.
- Voz y transporte Python de Pet: 26 pruebas correctas, incluida liberación que
  no interrumpe generación y conserva identidad/caché.
- Diez pruebas específicas del puente móvil: autenticación, origen, perfil sereno,
  parámetros, cancelación anticipada, aislamiento entre sesiones, duplicados,
  concurrencia, timeout y errores sin detalles privados.
- Navegador: WAV sintetizado y reproducido; estado **Hablando** observado;
  respuesta real del chat leída automáticamente hasta **Lectura terminada · voz local**.
- Vista de 390 px: sin desbordamiento horizontal y controles de voz visibles.
- Sin errores de consola en la aceptación de voz. SHA-256 de `settings.json` intacto.

La prueba del navegador verifica reproducción y finalización del audio, no mide
el volumen físico de los altavoces. Si no se escucha, probar el botón y revisar
la salida/volumen de Edge en Windows. Sigue pendiente la prueba física en Safari.

## Recuperación y archivos

Punto anterior: `recovery/jarvis-before-voice-20261119` en Karen.
Cambios principales: `mobile_speech.py`, `mobile_server.py`, archivos Jarvis,
`expressive_voice.py`, cliente/servicio compartidos de voz en `desktop-pet/python`
y sus pruebas. Deben conservarse ambas revisiones de los repositorios al actualizar,
porque la liberación de memoria requiere el cliente y servicio nuevos.

El servidor móvil se reinicia para cargar el puente; el acceso directo y el código
privado no cambian. No se modifican Rebecca ni las credenciales.
