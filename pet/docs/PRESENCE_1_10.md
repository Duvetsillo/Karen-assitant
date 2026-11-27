# Presencia y recuperación local — 1.10.0

## Diagnóstico y corrección de OpenClaw

El rechazo genérico de esquema ocultaba un HTTP 400 de Ollama: el prompt superaba
el contexto disponible. Se inspeccionó únicamente el error técnico del registro
local. La sesión compartida tenía ~28.186 tokens. Configuración local respaldada:
Qwen3:4b queda con contextTokens/contextWindow y params.num_ctx coherentes en 32.768,
maxTokens 2.048. La prueba sintética larga dejó de rechazar el formato, pero agotó
150 segundos; no se considera una solución de latencia para conversar.

Gemma3:1b ya estaba instalado. Se registró localmente con contexto 16.384,
maxTokens 1.024, params.num_ctx y compat.supportsTools=false según el contrato
instalado de OpenClaw. No se descargaron pesos ni se alteraron las herramientas
permitidas o el modelo predeterminado de otros clientes. Es un modelo de charla;
las herramientas LLM requieren otro modelo compatible. Los comandos Core siguen
siendo deterministas y locales.

Nueva opción de sesión propia del Pet (agent:main:karen-desktop), separada de main.
Conserva el agente/persona y la memoria Core; el historial compartido permanece
accesible al cambiar la opción. Sin reset, compaction ni borrado automático.
Las preferencias antiguas mantienen shared hasta cambiar explícitamente de opción.
Errores conocidos dan una orientación segura sin mostrar respuestas crudas del
proveedor ni repetir una orden aceptada.

Prueba real por Gateway, sesión sintética independiente: status ok, respuesta
no vacía, gemma3:1b, 17,21 s incluyendo CLI. Perfil local totalmente temporal:
respuesta con 6.663 tokens de entrada, 36,52 s en frío. No son una garantía de
latencia estable ni aceptación de calidad. Configuración privada fuera de Git.

## Saludos y reposo

78 frases en nueve categorías, selección de regreso, mezcla contextual y exclusión
del saludo anterior. Biblioteca local combina texto y audios compatibles; si
falta un audio, puede mostrar el saludo sin inferencia ni síntesis en el arranque.
Generación reanudable por texto/hash: reutiliza los 40 WAV existentes. Se generaron
los 38 nuevos con la voz local configurada; biblioteca completa de 78 validada
por análisis WAV/envolvente en staging privado, pendiente de instalar al cerrar app.

Once clips: luz, estiramiento, estrellas, deriva, giro, curiosidad, luciérnagas,
meditación, bostezo, baile y órbita. La bolsa aleatoria agota la ronda antes de
repetir; pausas variables, cesión inmediata a tareas/voz y respeto de reducción de
movimiento/bajo consumo. Poses limitadas sin brazos ni piernas.

## Pantalla completa

Control independiente fullscreenHide. Comprobación nativa cada segundo del tamaño
y marco de la ventana activa frente al monitor, excluyendo Explorer y Karen.
Sin imagen, título, contenido o registro persistente. No activa la observación
general; categorías/inactividad/batería conservan su permiso y frecuencia de 15 s.

Reutiliza despedida breve y confirmación de frame, con plazo máximo; oculta solo
la ventana propia del Pet. Restaura sin robar foco solo lo ocultado por este control.
Un cierre manual se conserva; una salida rápida cancela la animación y una muestra
fallida no autoriza a cambiar visibilidad. Bloqueo e introducción se respetan.

QA Windows real con ventana de prueba y foco nativo: ventana normal conservada,
pantalla completa detectada, ocultación animada, regreso y ocultación manual correctos,
observación general apagada y cero errores. El foco debe estar realmente en la
ventana controlada; una ventana de fondo del usuario en fullscreen no cuenta como
fallo del detector. No certifica cada juego con modo exclusivo u otro monitor.

## Entrega

Empaquetado, instalación y verificación final pendientes. No confundir los audios
generados en staging con una biblioteca ya instalada.

Validación incremental: 256 pruebas Pet y typecheck correctos; auditoría del código fuente sin datos privados. QA de las once actividades y cierre de instalación en curso.

## Corrección de reposo — 2026-11-27 / 1.10.1

El perfil real instalado 1.10.0 tenía sleepAfter=60 e idleAfter=30: tras el primer
clip, la pausa entre actividades superaba el umbral de sueño y la mascota quedaba
en SLEEPING indefinidamente. No era ausencia de las once animaciones.

Nuevo valor explícito sleepAfter=0, «No dormir automáticamente», como valor inicial.
Los tiempos positivos y el sueño solicitado manualmente conservan su significado.
El control ahora dice «Dormir automáticamente» y explica el efecto de tiempos cortos.
Con actividad máxima, la pausa entre clips pasa a ~15–21 s; baja actividad mantiene
pausas largas. Sin inferencias, audio ni percepción adicional para animarse.

257 tests y typecheck/build correctos. La prueba nativa en tiempo real de 76 s y
la instalación/configuración del perfil real se documentarán al completarse.
La aceptación previa Pet → Gateway → Ollama de 1.10.0 fue correcta (7,72 s), pero
la entrega anterior se interrumpió antes de copiar los 78 audios al perfil real.
