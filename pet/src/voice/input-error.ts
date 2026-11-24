/** Keep browser error names for recovery while explaining how to restore input. */
export function inputError(error: unknown, selectedDevice = false): Error {
  const original = error instanceof Error ? error : new Error('No se pudo abrir el micrófono.');
  const messages: Record<string, string> = {
    NotAllowedError: 'Windows no permite usar el micrófono. Revisa Privacidad y seguridad → Micrófono y vuelve a activar la escucha.',
    SecurityError: 'El acceso al micrófono está bloqueado. Revisa los permisos de Windows.',
    NotFoundError: selectedDevice
      ? 'El micrófono elegido ya no está conectado. En Voz, conecta ese dispositivo o elige otra entrada.'
      : 'No hay un micrófono disponible. Conecta uno y pulsa Reintentar escucha.',
    OverconstrainedError: 'El micrófono elegido ya no está disponible. Revisa el dispositivo de entrada en Voz.',
    NotReadableError: 'Windows no puede abrir el micrófono. Comprueba la conexión y si otra aplicación lo usa en exclusiva.',
    AbortError: 'Windows interrumpió la apertura del micrófono. Se puede reintentar la escucha.',
  };
  const busy = /Otra (?:interfaz|ventana) de Karen usa el micrófono/.test(original.message);
  const result = new Error(busy
    ? 'Otra interfaz de Karen usa el micrófono. Pausa su escucha para liberar la entrada.'
    : messages[original.name] || original.message.replace(/^Error invoking remote method '[^']+': (?:Error: )?/, ''));
  result.name = busy ? 'MicrophoneBusyError' : original.name;
  return result;
}
