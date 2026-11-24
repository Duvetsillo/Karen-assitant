# Karen — burbuja reactiva y reparto de modelos

Fecha: 19 de noviembre de 2026. Evolución incremental de Jarvis y Core 2.

## Burbuja ligada a la voz

La reproducción WAV local pasa ahora por un `AnalyserNode` de Web Audio antes
de llegar a los altavoces. El renderizador calcula la energía RMS de la señal
y aplica una envolvente suavizada para modular tamaño, deformación, luminosidad
y filamentos de la burbuja. Los silencios reducen la intensidad; al terminar
o detener la lectura, vuelve a cero.

No escucha el micrófono ni solicita permisos de captura. Mide el audio de Karen
antes del control de volumen físico del equipo: silenciar Windows no transforma
esa señal en entrada de micrófono ni cambia la identidad de voz.

Se conserva la pausa manual, el movimiento reducido, la suspensión al ocultar
la página o al abrir Herramientas y el límite de partículas. El análisis usa
un búfer de 512 muestras reutilizado en el mismo bucle de dibujo. No añade otro
bucle de renderizado, WebGL, modelos o procesos. Los nodos de audio se desconectan
al terminar, cancelar o fallar la reproducción.

## Política de tareas ligeras

La conversación sencilla y el resumen/recuperación de memoria priorizan modelos
locales adecuados y se ejecutan en CPU mediante `num_gpu=0`. Así esas inferencias
no ocupan VRAM de pesos y dejan la GPU disponible para voz u otra tarea.

La selección conserva capacidades, preferencia configurada, disponibilidad,
presupuesto de RAM y latencias observadas. No cambia un modelo solo porque otro
sea mayor. Si el primer candidato falla, mantiene el fallback local acotado a dos
intentos; nunca cambia a cloud ni descarga un modelo.

Las solicitudes cortas usan contexto de 2048 y lote de 64. Si el historial
acotado supera 4200 caracteres, se conservan 4096 de contexto como antes.
El historial guardado y la memoria de proyectos no se eliminan.

## Trabajo complejo y GPU

Programación, razonamiento, herramientas y visión conservan sus categorías y
restricciones de capacidad. El router lee el número de capas real de `/api/show`
y calcula cuántas puede colocar en GPU. Reserva en su cálculo:

- Un objetivo de 1536 MiB de VRAM libre para otras necesidades.
- 512 MiB estimados para contexto y costes adicionales.
- Un margen del 25 % sobre el tamaño de los pesos estimados por capa.
- Al menos 1 GiB de RAM libre, más presupuesto de alojamiento/contexto.

Si falta VRAM, usa CPU cuando cabe en RAM. Si tampoco cabe, descarta ese candidato.
Si faltan metadatos de capas, no inventa un tamaño de offload: usa la alternativa
CPU con presupuesto válido. Reevalúa recursos después de tomar el bloqueo de
inferencia y antes de generar, porque otra aplicación puede consumir memoria.

Estos márgenes son una estimación conservadora y un límite solicitado a Ollama,
no una reserva física garantizada por Windows. Cachés, controladores, KV y otras
aplicaciones pueden cambiar el uso real. No se presenta esto como un planificador
global capaz de controlar cualquier aplicación externa.

Todas estas generaciones usan `keep_alive=0`, incluso los modelos pequeños:
al terminar se solicita su descarga de Ollama. La selección efectiva CPU/GPU
y capas se incorpora a las métricas sin textos ni credenciales. En Herramientas,
el modelo de la última respuesta muestra también CPU o GPU.

## Coordinación con la voz original

Se conserva la voz femenina adulta original y su estilo sereno. No se alterna
su identidad por otra voz ligera sin que el usuario lo decida.

Una conversación CPU puede coexistir con pesos de voz inactivos si hay al menos
3584 MiB de RAM disponibles. Ante trabajo complejo o poca RAM, se libera primero
la voz inactiva. La síntesis continúa usando el bloqueo de inferencia y la
descarga de pesos de Ollama antes de cargar su modelo.

Al finalizar la lectura, Jarvis solicita `POST /api/speech/release` para liberar
los pesos de voz que ya no necesita el audio decodificado. Al detenerla, cancela
primero su solicitud y pide la misma limpieza. La operación está autenticada,
solo admite un objeto vacío y no interrumpe síntesis activas de otros clientes.
La caché pequeña de audio y el perfil original se conservan.

El objetivo de 1536 MiB se aplica al reparto de Ollama. El modelo original de voz
todavía necesita gran parte de los 6 GB durante su propia generación; no se
promete ese margen mientras sintetiza. Liberarlo al acabar reduce ocupación en
reposo a cambio del coste de recargarlo en frío. Esta limitación se mantiene
visible en la documentación de voz; no se descarga otro modelo para ocultarla.

## Evidencia

- 270 pruebas Python de Karen correctas, incluida selección, presupuesto cambiante,
  contexto largo, CPU sin offload, GPU parcial, memoria insuficiente y limpieza
  que no interrumpe otra síntesis.
- JavaScript válido con `node --check mobile/jarvis.js`.
- Inferencia real de conversación: `qwen2:0.5b`, CPU, 0 capas GPU; Ollama informó
  `size_vram=0`. Latencia de esa ejecución: 1,657 s.
- Otra petición real, categoría razonamiento: `gemma3:1b`, GPU, 26 capas;
  Ollama informó 813 160 202 bytes de VRAM del modelo. Latencia: 3,841 s.
- No quedó ningún modelo en `/api/ps` después de completar las pruebas.
- Los nombres anteriores son modelos efectivos observados; no garantizan que cada
  solicitud futura elija esos mismos candidatos. Depende de presupuesto y fallback.
- Voz real en navegador: pico de envolvente 0,708 y nivel 0,000 tras finalizar.
  Son datos de la señal, no una medición de volumen de altavoces ni de calidad vocal.
- Tras la lectura, el servicio de voz informó `phase=cold`, `modelLoaded=false`
  y el mismo perfil `karen-original-v2`.
- A 390 px: 380 px útiles y de contenido, sin desbordamiento; controles de voz visibles.
- Sin errores ni advertencias de consola durante la aceptación.

Las latencias son observaciones de una ejecución, no un benchmark estadístico.
La evidencia local del router está en `.private/reactive-routing-live.json` y
la captura de la vista en `qa/karen-reactive-voice.jpg`, ambos excluidos de Git.
Sigue pendiente validar la experiencia física en Safari y con carga prolongada.

## Recuperación

Etiqueta previa: `recovery/jarvis-before-reactive-20261119`. Archivos principales:
`mobile/jarvis.js`, `karen_core2/models.py`, `karen_core2/runtime.py`,
`mobile_speech.py`, `mobile_server.py` y sus pruebas. No se cambian tecnologías,
configuraciones guardadas, credenciales ni Rebecca. Visión permanece pausada.
