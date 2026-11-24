# Reparación de voz en la aplicación activa

Fecha: 2026-10-31. Solicitud: resolver el aviso «Error de voz · revisa Voz» que impedía hablar con Karen antes de continuar el desarrollo.

## Diagnóstico

Se inspeccionó la aplicación instalada mediante su interfaz Windows. La sesión mostraba «Recursos: Directorio de voz de la aplicación / KAREN_PROJECT_ROOT» y disponibilidad STT sin configurar. El perfil convencional leído desde disco contenía una ruta de recursos; eso no coincidía con el estado de la sesión visible. No se atribuye esa diferencia a una causa no demostrada.

Los recursos esperados existen en `C:\karen`: intérprete `voice-runtime/Scripts/python.exe`, modelo faster-whisper-small, configuración y tokenizer. El runtime de voz utiliza Python 3.11.9, faster-whisper 1.2.1 y CTranslate2 4.8.2. El worker de reconocimiento instalado procesó un segundo de PCM sintético silencioso y respondió `{"text":""}` con código de salida 0. Se verificaron carga e inferencia local, sin grabar al usuario ni enviar datos a un proveedor.

## Acción aplicada

Se volvió a seleccionar `C:\karen` con el selector «Elegir carpeta de recursos de voz» de la aplicación activa. El indicador cambió de error a «Di “Karen” para activarme», con el botón «Pausar escucha». La ruta visible cambió a `C:\karen` y la escucha continuó activa en observaciones posteriores. Se conservó el micrófono Fifine seleccionado y no se aceptaron permisos de Windows ni se cambiaron ajustes de seguridad.

Se creó una copia del perfil convencional en `backups/voice-repair-20261031T223451Z/`, con ACL restringida al usuario Windows. Ese respaldo no se presenta como prueba de la ubicación efectiva de todas las preferencias de la sesión: el archivo convencional ya contenía la ruta y no cambió durante la operación. No se leyó ni descifró el contenido de la bóveda de credenciales.

## Alcance de la comprobación

Se verificaron recursos reales, inferencia con silencio sintético y la escucha activa de la instalación del usuario. No se afirma haber reconocido una frase real del usuario ni haber validado una conversación completa por voz. El usuario puede probar «Karen» seguido de una pregunta. No se instalaron paquetes, se reiniciaron servicios ni se modificó el código para resolver esta configuración de sesión.
