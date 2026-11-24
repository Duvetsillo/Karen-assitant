# Voz y activación de Karen

Actualización 2 de noviembre de 2026: Pet 1.8.0 añade iniciativa configurable para
saludos y propuestas con voz opcional, sin abrir el micrófono automáticamente.
Respeta No molestar, presencia, cuota y horas silenciosas. Mantiene el motor de voz
elegido y permite detener su intervención. [Guía y pruebas](docs/KAREN_INTERFACE_INITIATIVE_2026-11-02.md).

Actualización 1 de noviembre de 2026: Pet 1.7.0 prepara una primera oración local
más corta, conservando las siguientes y el prefetch. En un ensayo controlado
contra los EXE, el primer audio pasó de 6,475 a 2,920 segundos, con modelo caliente.
Karen clásica ya puede cerrar su conexión TTS al cancelar incluso mientras espera
la respuesta HTTP. Pruebas y límites: [Karen 1.7.0](docs/PET_VARIANTS_2026-11-01.md).

Actualización 31 de octubre de 2026: el servicio local original admite CUDA graphs
FP32 y decoder GPU con recuperación a CPU. La misma frase de referencia pasó de
26,1 a 3,1 segundos con modelo caliente. La preparación fría sigue rondando
25 segundos. Configuración, alcance instalado, pruebas y reversión:
[Voz local acelerada](docs/LOCAL_TTS_ACCELERATION_2026-10-31.md).
Las cifras y comportamientos siguientes conservan su contexto histórico.

Referencia histórica de voz: 16 de octubre de 2026. Desktop Pet declara ahora la versión 1.6.8 en `package.json`; consulta `docs/KAREN_IMPLEMENTATION_PLAN.md` para el estado verificado más reciente. Karen original y Desktop Pet conservan la referencia original v2 y el servicio local autenticado. WhatsApp conserva su configuración y entrega de voz original.

Actualización 28 de octubre de 2026: Karen clásica reintenta abrir el micrófono tras fallos de PortAudio. Después de tres fallos muestra **Error** y continúa con esperas crecientes, limitadas a diez segundos, hasta que vuelva el dispositivo o el usuario detenga la escucha. Si el micrófono configurado es el predeterminado, vuelve a consultar el índice de entrada de Windows tras el fallo y actualiza el indicador cuando cambia; una selección explícita no cambia. Una reconexión se anuncia en el registro. La regresión usa dobles; aún falta desconexión física y suspensión de Windows. El texto de Ollama llega por streaming incluso con TTS apagado. Estas mejoras no implementan barge-in: la escucha se pausa mientras Karen genera o habla.

Si STT falla temporalmente con `OSError`, `TimeoutError` o `ValueError`, Karen libera el estado ocupado, espera hasta diez segundos y vuelve a abrir la escucha. Si falta el archivo del modelo, muestra **Error**, explica que debe configurarse un modelo instalado y detiene los reintentos. La regresión usa captura y transcripción simuladas; falta reproducir ambos fallos con el motor y hardware reales.

Si un transcript queda en la cola de Tk mientras la respuesta anterior todavía se está cerrando, Karen lo descarta y pide repetirlo. Así evita dos generaciones simultáneas. La prueba reproduce esa carrera sin hardware; la interrupción hablada durante TTS sigue pendiente.

**Cancelar generación** cierra una respuesta Ollama activa, detiene su voz y descarta el turno incompleto. La escucha sigue pausada durante la generación y la reproducción; el botón no es barge-in por voz. Si la petición HTTP aún no devuelve un stream, la cancelación espera ese retorno o su timeout.

Los resultados locales de memoria, Home Assistant, Proxmox, calendario y administración pueden contener datos privados. Karen solo los pronuncia con Kokoro, Qwen3 TTS o una voz local activa; con Edge TTS quedan en texto. `/ventana activa` permanece siempre en texto. Las respuestas generales del modelo conservan la voz configurada.

Para priorizar rapidez en el PET, elige **Voz → Motor de voz → Rápida local · Kokoro (otro timbre)**. Es una voz sintética diferente, disponible con tus recursos Kokoro locales. La prueba instalada tardó unos 6 segundos en cargar por primera vez y 0,65 segundos en sintetizar después; la reproducción comenzó en 0,91 segundos con el modelo cargado. La boca sigue la energía real del audio. No usa Windows ni envía texto a un servicio de voz externo. La voz original queda seleccionada hasta que elijas esta alternativa; WhatsApp y Karen original no cambian.

En **Karen original**, Audio ofrece un estilo de voz y personalidad: Serena, Cercana, Seria, Alegre, Ironía suave u Original. También permite activar sugerencias útiles y sarcasmo suave. Guarda los cambios con el micrófono detenido. El cliente Ollama usa esas preferencias sin cambiar tu modelo cloud.

Para activarla con la voz, selecciona **Karen/Caren: transcripción local** y pulsa **Activar micrófono**. Di solo «Karen», como un nombre normal; «Caren» es otra escritura que acepta el reconocimiento. No pronuncies la barra ni ambos nombres. También puedes decir «Karen, …» seguido de la orden. Si solo dices el nombre, tienes diez segundos para continuar. La casilla de escuchar al abrir permite hacerlo automáticamente; queda desactivada para que el PET sea el cliente que escucha ahora.

En el **PET**, Voz tiene seleccionada la voz original serena y la activación Karen/Caren está habilitada. El indicador confirma la escucha local. Desde 1.5.1, **Detener** cancela la respuesta o captura actual y conserva tu ajuste de activación. **Pausar escucha** cierra el micrófono; el estado pausado ofrece **Activar escucha**. Un fallo de micrófono queda visible con **Reintentar escucha**. Al escuchar, la mascota abre los ojos y al hablar sincroniza boca y gestos con la energía real del audio.

Activa escucha continua en el cliente que quieras usar. No se coordina automáticamente el micrófono entre dos procesos distintos. La entrada se cierra durante la reproducción de ese cliente y durante la captura de audio del PC.

Los estilos cambian ritmo, tono y ecualización con moderación, conservando la referencia. Las emociones y el sarcasmo dependen del texto; Qwen Base no proporciona instrucciones de emoción. El selector del PET controla la entrega de audio y conserva la personalidad configurada en OpenClaw.

La primera síntesis anterior tardó unos 57 segundos. Desde 1.5.2, el PET empieza por una frase corta, genera una frase siguiente durante la reproducción y prepara el modelo mientras escucha una orden o espera la respuesta. Con voz local activa y bajo consumo desactivado, el modelo puede permanecer diez minutos en memoria GPU para evitar recargas frecuentes. El bajo consumo omite esa precarga. La síntesis de frases nuevas todavía tarda; una repetición en caché no equivale a inferencia nueva. El indicador y la respuesta ocupan filas distintas, y el globo permanece visible durante la generación y reproducción. El reconocimiento también puede confundir palabras con ruido o distancia. No se cambia automáticamente al motor robótico de Windows para ocultar un error.

Fuentes de la integración original: `config.py`, `voice.py`, `voice_local.py`, `expressive_voice.py`, `karen_app.py`, `ui.py` y `karen_personality.py`. Respaldo anterior: `backups/voice-wake-styles-20261016`. El diff de integración no contiene configuración privada, referencias ni credenciales. Las notas completas se conservan en Obsidian.
