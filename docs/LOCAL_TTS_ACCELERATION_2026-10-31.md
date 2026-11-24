# Voz local acelerada de Karen — Windows, 2026-10-31

Actualización 2026-11-01: la cancelación clásica pendiente en el corte original
se resolvió mediante una conexión interrumpible y se comprobó con el modelo real.
Pet 1.7.0 reduce además la espera de su primera oración. Véase
[la continuación verificada](PET_VARIANTS_2026-11-01.md); las limitaciones al final
de este documento describen el estado del 31 de octubre.

## Resultado verificado

Se conserva Qwen3-TTS-12Hz-0.6B-Base, la referencia original sintética
`karen-original-v2` y su SHA-256
`14262d618b6439cc9625ae59ef3f314d3f304f556fc0e9d976004151eaa8d85d`.
No se clonó una persona ni se sustituyó el timbre por Kokoro/Windows/Edge.
No se enviaron textos o referencias a proveedores externos.

La ruta nueva usa CUDA graphs para talker/predictor, FP32 y SDPA. Solo el
decodificador del codec pasa a CUDA si hay al menos 950 MiB libres; el encoder
del codec permanece en CPU. El speaker encoder vuelve a CPU tras obtener la
referencia. El decoder limita sus bloques a 24 frames con 25 frames de contexto.
Si falta memoria CUDA al decodificar, reintenta una sola vez los mismos tokens
en CPU, sin cambiar la identidad. Esta recuperación de OOM se comprobó con
un doble; la ejecución GPU real sí se comprobó en el equipo descrito abajo.

## Dependencias y arquitectura

- Servicio único compatible con clientes anteriores: loopback autenticado
  `127.0.0.1:18790`, protocolo 2, `/prepare`, `/speech`, `/health`.
- Un hilo persistente ejecuta inferencia; salud/HTTP siguen concurrentes.
  Máximo cuatro peticiones de inferencia aceptadas, incluida la activa.
- Cancelar/cerrar una conexión HTTP de síntesis aborta su generación entre
  frames. Se restauran los métodos temporales del predictor/decoder y no se
  guarda audio parcial en caché. No cancela conexiones de otros clientes.
- Métricas de generación, decoder, tokens y dispositivo disponibles en salud.
  Errores muestran clase y ubicaciones de código, sin texto de usuario,
  mensajes de excepción, rutas absolutas ni credenciales.
- Cache de hasta ocho clips o 12 MB; descarga tras inactividad. La conversación
  mantiene el modelo caliente diez minutos para evitar recargas frecuentes.
- Pet de código fuente divide respuestas locales en oraciones de al menos
  70 caracteres, máximo 240, y prepara un clip siguiente durante reproducción.
  Los demás motores conservan su segmentación anterior.
- Es audio progresivo por oraciones; **no es streaming PCM ni lectura del texto
  parcial del modelo**. Se espera el mensaje final y cada clip completo.

Entorno original sin actualizar: Python 3.11.9, torch 2.6.0+cu126,
Transformers 4.57.3 y qwen-tts 0.1.1. Overlay separado `tts-fast-runtime`
con faster-qwen3-tts **0.2.6**, sin instalar sus dependencias. No usar versiones
nuevas de ese paquete en expressive-runtime sin revisar compatibilidad.

El predictor acelerado usa top-k 50, temperatura 0.55 y top-p 1.0; el talker
conserva top-p 0.9 del perfil. En esta combinación Turing, aplicar top-p 0.9 al
predictor capturado produjo audio inválido; se descartó esa configuración.
FP16 provocó un device-side assert y también quedó descartado. No se alteró
el JSON del perfil original para esconder esas diferencias del backend.

## Mediciones reales

Windows 11 26200, RTX 2060 de 6 GB, Ryzen 5 5500, 16 GB RAM.
Son muestras locales con texto sintético; no un benchmark estadístico de todos
los usos ni una promesa para otros equipos. RTF = generación / duración de audio,
menor es mejor. La caché no intervino en las tres muestras finales.

| Caso | Entrega HTTP del WAV | Duración del WAV | RTF |
| --- | ---: | ---: | ---: |
| Anterior: «Hola. Soy Karen y estoy lista para ayudarte.» | 26,126 s | 5,021 s | 5,203 |
| Acelerado: mismo texto, estilo Serena | 3,111 s | 4,170 s | 0,746 |
| «Podemos conversar con calma y revisar tus pendientes.» | 3,108 s | 4,003 s | 0,777 |
| «La temperatura del procesador depende de sus sensores.» | 3,840 s | 4,511 s | 0,851 |

La misma primera frase se entrega aproximadamente **8,4 veces más rápido**.
Cambió la duración generada; no equivale a comparar waveforms idénticos.
El baseline y la prueba acelerada usan la misma referencia/modelo, pero el
muestreo y el estilo pueden producir diferencias de ritmo y audio.
La última preparación fría completa tardó **25,039 s**, separada de la síntesis.
El codec pasó de 6–8 s en CPU a **0,235–0,404 s** en GPU en esas muestras.
La prueba aislada CUDA registró pico de **4478,3 MiB** asignados por Torch;
no incluye toda la VRAM usada por Windows y otras aplicaciones.

Prueba Electron con dos oraciones, salida silenciada y síntesis GPU real:

- Primer `Audio.play()` completado: **5,157 s** desde el inicio del ensayo.
- Segunda oración: transición de preparación a reproducción en **24,3 ms**;
  su generación se solapó con la reproducción de la primera.
- Reproducción completa: **16,944 s**, sin errores del renderer.
- Cancelación HTTP durante inferencia: servicio recuperado en **0,141 s**.
- Una síntesis nueva después de cancelar volvió a decodificar correctamente.

Whisper small local transcribió las tres muestras finales con **WER 0** tras
normalizar puntuación/mayúsculas. Es una comprobación de inteligibilidad sobre
tres frases conocidas; no mide naturalidad, semejanza humana ni calidad subjetiva.
Las pruebas nativas silenciadas tampoco sustituyen la revisión auditiva del usuario.

Resultados privados/locales, excluidos de Git:
`qa/tts-baseline-20261031.json`, `qa/tts-accelerated-service-20261031.json`,
`qa/tts-final-intelligibility-20261031.json`, `desktop-pet/qa/accelerated-voice-native.json`.
Muestras nuevas: `qa/tts-accelerated-service-0.wav` a `-2.wav`.

## Instalar y arrancar en Windows

En `C:\karen`, con el entorno original y los modelos ya instalados:

```powershell
python setup_fast_tts.py
python setup_fast_tts.py --activate
& .\expressive-runtime\Scripts\python.exe .\expressive_service.py
```

El primer comando comprueba versiones/CUDA, instala el wheel con SHA-256
fijado y añade una referencia de lectura al site-packages original. No actualiza
Torch, Transformers ni Qwen. El segundo selecciona el backend para el siguiente
arranque, respaldando cualquier configuración previa. El tercer comando es
para diagnóstico manual: no iniciarlo si ya existe el servicio en 18790.
En uso normal los clientes lo inician automáticamente.

Karen clásica: `powershell -ExecutionPolicy Bypass -File .\start_karen.ps1`.
Pet: conservar carpeta de recursos `C:\karen` y motor local original.
Los modelos existentes no se descargan otra vez. No se necesita una API de pago.
El backend acelerado requiere CUDA; no se ha validado en una máquina sin GPU.
El motor Kokoro CPU existente sigue siendo una elección explícita de otro timbre.

Para forzar decoder CPU conservando graphs, escribir sin BOM:

```powershell
python -c "import json; from pathlib import Path; Path('voice-models/tts-runtime.json').write_text(json.dumps({'schema':1,'backend':'cuda-graphs-fp32','decoder':'cpu'}),encoding='utf-8')"
```

Reiniciar el servicio cuando no esté generando. Esto evita reservar VRAM para el
decoder y aumenta la latencia. No cerrar a ciegas todos los procesos Python.

## Repetir verificaciones

```powershell
& .\expressive-runtime\Scripts\python.exe .\qa\measure_tts.py
cd desktop-pet
npm run test:voice:contracts
npm test -- --reporter=dot
npm run build
npm run test:voice:accelerated
```

`measure_tts.py` no reproduce ni captura sonido. Comprobar `cacheHit` antes de
comparar ejecuciones; repetir el mismo texto puede usar caché. El smoke nativo
usa perfil temporal, base Core temporal, volumen cero, STT/wake apagados y texto
sintético. No modifica el perfil habitual ni envía chats al Gateway.
`qa/probe_fast_tts.py` es experimental, carga otro modelo y requiere antes detener
el servicio y liberar su GPU; no ejecutarlo en paralelo al servicio productivo.

Pruebas de esta continuación: 165 unitarias clásicas, 131 TypeScript Pet,
22 contratos Python de voz; typecheck/build Windows y smoke GPU/Electron reales.
Las recuperaciones OOM y aislamiento de sockets tienen pruebas con dobles/sockets;
no se provocó agotamiento real de VRAM de una aplicación del usuario.

También pasó el mismo smoke contra el EXE empaquetado, utilizando el worker
de la instalación actual: primer audio 4,504 s, separación entre oraciones
23,4 ms y recuperación de cancelación 0,403 s. Resultado conservado en
`desktop-pet/qa/accelerated-voice-packaged.json`. El renderer empaquetado no se
ha instalado sobre el habitual; el motor de voz instalado sí está actualizado.

Paquete: `desktop-pet/release/voice-cuda-20261031/Karen Desktop Pet Setup 1.6.8.exe`,
129220890 bytes, SHA-256
`BA31C63C480FA7C7E2BAC151F3756A1273AA0037E415CD5F6397DA4534A7D151`.
Compilación NSIS Windows x64 local, sin firma y sin publicación. Se verificó el
EXE desempaquetado, no el flujo de instalación/desinstalación del instalador.

## Reversión

Se actualizaron **solo** `shared_voice_service.py` y el nuevo `voice_acceleration.py`
del directorio Python desempaquetado de la instalación existente. Perfil y estilo
instalados se compararon con fuente y eran idénticos. Se reinició exclusivamente
el proceso TTS inactivo y se verificó que arrancaba desde esa ruta instalada.
La aplicación instalada conserva su renderer anterior; el nuevo renderer con
segmentación por oraciones está en el paquete de esta entrega, aún sin instalar.

Respaldo de los workers instalados:
`backups/voice-service-installed-20261101T021547Z` (nombre con fecha UTC;
corresponde al 31 de octubre en America/La_Paz). Su manifest registra hashes
anteriores/nuevos. El worker anterior se guardó y el helper no existía antes.
Los hashes de fuente, worker instalado y paquete nuevo fueron idénticos.
Para revertir esa actualización, detener solo TTS, copiar el worker guardado a
su ruta original y seleccionar backend `standard`. No es necesario eliminar el
helper; el worker antiguo no lo importa. No restaurar datos ni perfil de usuario.

Respaldo previo de código/datos/referencia: `backups/before-local-tts-20261031`.
No se modificaron referencia WAV, active-voice.json, perfil, credenciales ni bases
de conversación. No hay migración de esquema.

Para desactivar la aceleración conservando el mismo modelo/voz:

```powershell
python -c "import json; from pathlib import Path; Path('voice-models/tts-runtime.json').write_text(json.dumps({'schema':1,'backend':'standard'}),encoding='utf-8')"
```

Reiniciar solo el proceso verificado que escucha en 18790 cuando esté inactivo.
No borrar modelos, runtimes, historiales ni credenciales. Para revertir código,
extraer source.zip del respaldo en un directorio de revisión y restaurar solo
archivos afectados, preservando los cambios posteriores del usuario.
Los clientes protocolo 2 siguen siendo compatibles con el servicio anterior.

## Fuentes y licencias

- Modelo/API: [Qwen3-TTS oficial](https://github.com/QwenLM/Qwen3-TTS).
- Acelerador: [faster-qwen3-tts](https://github.com/andimarafioti/faster-qwen3-tts),
  licencia MIT incluida en `tts-fast-runtime/Lib/site-packages/faster_qwen3_tts-0.2.6.dist-info/licenses/LICENSE`.
- Wheel fijado: SHA-256 `3881a41dc189f0a6e93fa047f376deffeb2fa84e888e7d570f79b3e2267765cc`.

No se adoptan las cifras publicitadas de latencia del modelo como mediciones de
Karen. El barge-in por voz/VAD, reproducción PCM continua, latencia desde el fin
de voz del usuario y revisión física del micrófono siguen pendientes. El cliente
Python clásico todavía descarta su audio al cancelar, pero su petición urllib
puede seguir esperando respuesta; la cancelación real medida aquí corresponde
a la conexión abortada de Pet. No se presenta esa limitación clásica como resuelta.
