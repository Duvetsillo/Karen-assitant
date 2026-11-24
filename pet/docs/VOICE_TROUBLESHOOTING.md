# Recuperar la voz de Karen

## Escucha y reproducción son controles distintos

**Activar al decir Karen o Caren** controla la escucha local del micrófono.
**Leer las respuestas** controla el audio de salida. Una opción puede estar
activada mientras la otra está apagada. El modo No molestar pausa ambas en
ejecución y conserva sus preferencias para volver al modo Normal.

## Si aparece «Escucha detenida»

Pet muestra la causa debajo del estado. La misma causa aparece en Ajustes → Voz,
incluso si esa ventana se abre después del fallo.

| Causa | Acción |
| --- | --- |
| Otra interfaz usa el micrófono | Pausa la escucha de la otra interfaz de Karen y reintenta. No se fuerza el bloqueo. |
| Micrófono elegido desconectado | Reconecta ese dispositivo o selecciona explícitamente otra entrada en Voz. |
| Acceso denegado | Comprueba Privacidad y seguridad → Micrófono en Windows; después reintenta. |
| Windows no puede abrirlo | Comprueba el cable, el dispositivo predeterminado y aplicaciones que usen entrada exclusiva. |
| Modelo o dependencias ausentes | Revisa la carpeta con `voice-runtime` y `voice-models/faster-whisper-small`. |

Un dispositivo guardado que aún no aparece en el inventario conserva su opción
visible: no se muestra falsamente el predeterminado de Windows. Actualizar los
dispositivos abre y cierra brevemente el micrófono para obtener sus nombres.
Karen no cambia silenciosamente a otra entrada.

Los errores transitorios al abrir o grabar reintentan dos veces con espera.
Después queda detenido con un botón para reintentar. Denegar permiso no inicia
un bucle de solicitudes. Pausar o detener invalida los callbacks anteriores.
Los fragmentos de una grabación fallida se descartan antes del reconocimiento.

## Si escucha, pero no habla

Comprueba Leer las respuestas, volumen, dispositivo de salida y motor elegido.
Consultar motores revisa recursos y servicio; no demuestra que haya ocurrido
reproducción física. Probar voz de Karen genera una frase real con ese motor.

La voz original conserva el perfil y la referencia verificados. Necesita sus
recursos locales y margen de memoria para inferencia. Con RAM o VRAM ocupadas,
no basta con que existan los archivos. El error no autoriza sustituir la voz,
cerrar otras aplicaciones ni enviar texto a un proveedor externo.

## Comprobación de desarrollo

Desde `pet/`:

```powershell
npm test
npm run build
npm run test:voice:contracts
```

Las pruebas de regresión no prueban acústica, acento ni captura con un micrófono
físico. La activación actual transcribe fragmentos locales con voz; no hay AEC
validado, STT incremental ni interrupción vocal durante la reproducción.

Para aceptación física: decir «Karen, dime la hora», comprobar que se activa una
sola vez, escuchar la respuesta con Leer las respuestas activado y confirmar
que vuelve a escuchar. Repetir tras pausar/reanudar y desconectar/reconectar la
entrada. Ninguna prueba necesita enviar grabaciones a GitHub.
