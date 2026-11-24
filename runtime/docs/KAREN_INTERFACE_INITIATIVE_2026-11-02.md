# Karen 1.8.0: interfaz, estabilidad e iniciativa

Fecha: 2 de noviembre de 2026. Cambios incrementales sobre 1.7.0, sin reemplazar
proveedores, conversaciones, motores de voz ni mecanismos de autorización.

## Qué cambia

- Conversación con más espacio, tipografía mayor, estados de voz reales y accesos
  para consultar tareas y chats anteriores. Los accesos preparan el mensaje;
  el usuario decide enviarlo.
- Navegación agrupada, tonos azul profundo y cian, selector de modo accesible desde
  cualquier sección y controles del modelo plegables.
- Vista de la mascota más grande en Apariencia, Comportamiento y Voz. La conversación
  y el centro de iniciativa no reservan una columna permanente para una animación.
- Ocho estilos, brazos y piernas independientes y actividades decorativas se conservan.
- Centro **Iniciativa** con activación, voz opcional, intervalo de 15–240 minutos,
  límite diario de 1–12 propuestas, horas silenciosas y pausa de una hora.
- Saludo diario, preguntas de compañía, aviso de desconexión y avisos de cambios
  de tareas observados en el archivo compartido. Cada aviso muestra su motivo.
- Historial local acotado a 30 propuestas, con cuota, última intervención, pausa y
  deduplicación persistidas en `%APPDATA%\karen-desktop-pet\initiative.json`.

Las preguntas de compañía son reglas y textos locales. **No equivalen a un agente
que inventa y ejecuta planes por iniciativa propia.** No se llama automáticamente
a OpenClaw ni se envía el historial a modelos para redactarlas. El motor de voz
elegido por el usuario sí puede necesitar red, como ocurría antes de esta entrega.

## Fallos corregidos

1. **Error al cargar una apariencia guardada.** La prueba de arranque reprodujo
   `Cannot read properties of null (reading 'clear')` en el batcher de Pixi.
   Karen montaba el renderizador antes de recibir los ajustes y podía destruirlo
   inmediatamente para cambiar de apariencia. Ahora espera la configuración inicial
   y sustituye texturas dentro del mismo contexto WebGL. Las pruebas verifican
   la identidad del canvas durante nueve cambios consecutivos y ausencia de errores.
2. **Clics perdidos con seguimiento del cursor desactivado.** Las posiciones nativas
   necesarias para decidir qué zonas reciben clics estaban ligadas al ajuste de
   movimiento de los ojos. Se desacoplaron: apagar la mirada ya no corta esos eventos.
3. **Compositor pequeño y desplazamiento innecesario.** Se evita desplazar un chat
   vacío hasta su final; el diseño compacto mantiene accesible Enviar incluso con una
   sugerencia y el selector de modelo desplegado a 820 × 620 de ventana.
4. **Mensajes de voz confusos.** La preparación solo se etiqueta como voz original
   cuando se utiliza realmente el motor local de esa voz.
5. **Reposo que conserva una espera anterior.** Al dejar de recrear Pixi, el
   planificador conservaba el plazo de cuando las animaciones estaban apagadas.
   Se recalcula al reactivar o cambiar el plazo. Una prueba reproduce la secuencia
   de 30 a 15 segundos y los tres juegos vuelven a pasar en Electron real.

No se afirma haber reproducido o resuelto todos los posibles errores de micrófono,
Gateway o hardware. Los fallos de este apartado tienen pruebas específicas.

## Cómo funciona la iniciativa

Hay un solo planificador en el proceso principal de Electron. Las ventanas Pet y
Ajustes reciben el mismo evento tipado `initiative`, con contrato propio versión 1.
El diario se escribe antes de anunciar una propuesta; si no puede guardarse, no
se anuncia. Un diario incompatible se conserva y la función queda inactiva.

Para intervenir automáticamente Karen espera al menos 90 segundos desde la última
interacción en sus interfaces. Comprueba que la mascota esté visible, el equipo
desbloqueado y que haya actividad del usuario en los últimos tres minutos. Respeta
Gaming, No molestar, cuota, pausa y horas silenciosas del equipo. No interviene
durante captura, síntesis/reproducción, una respuesta pendiente, percepción o
actividad de otra interfaz publicada en Core.

El planificador comprueba condiciones cada 15 segundos; no carga un modelo de
conversación. El globo se cierra tras dos minutos y conserva el aviso en el historial.
El modo pequeño de la mascota tiene una versión compacta del globo.

**Sugerir ahora** es una petición manual: puede omitir pausa, horario, intervalo y
cuota. Sigue necesitando iniciativa activada, presencia, visibilidad, modo Normal y
que Karen esté libre. Las peticiones manuales también cuentan en el total diario.

Si se activa **Decir las sugerencias en voz alta**, utiliza el pipeline y motor de
voz ya configurados, siempre que **Leer respuestas** siga activo. Descartar,
silenciar o empezar a interactuar cancela la voz de iniciativa. No activa el
micrófono automáticamente ni amplía permisos. El barge-in por voz sigue pendiente.

## Tareas y permisos

Para avisos de tareas, iniciar Pet con rutas absolutas a archivos existentes:

```powershell
$env:KAREN_CORE_DB = 'C:\karen\.private\conversations.sqlite3'
$env:KAREN_TASKS_DB = 'C:\karen\.private\karen-tasks.sqlite3'
& "$env:LOCALAPPDATA\Programs\Karen Desktop Pet\Karen Desktop Pet.exe" --settings
```

Solo se consultan metadatos de las últimas 50 tareas; no se ejecuta su contenido.
La primera consulta establece una línea base. Se anuncian cambios posteriores
observados mientras Karen está abierta, con el mismo ID de tarea. No se presentan
filas antiguas como eventos que acaban de ocurrir. Si no se puede leer el archivo,
se registra el problema y se conserva la compañía sin anunciar datos imaginados.

**Revisar tarea** prepara `/tareas estado ID`. El usuario pulsa Enviar para consultar
el estado local. Las propuestas no aprueban, cancelan ni reanudan trabajos. Un
resultado `uncertain` o `interrupted` se anuncia como pendiente de revisión.

El diario de propuestas pertenece al perfil Pet. La clásica comparte el archivo de
tareas, pero esta entrega no incorpora el centro de iniciativa en Tk ni unifica
por completo las sesiones internas de los dos clientes.

## Capturas verificadas

Son capturas de Electron real con perfiles temporales y conexión al Gateway
desactivada. El saludo y los avisos son producidos por la implementación; las tareas,
presencia y salto de reloj de las pruebas son datos controlados y no servicios reales.

![Conversación](../desktop-pet/qa/initiative/conversation.png)

![Apariencia](../desktop-pet/qa/initiative/appearance.png)

![Iniciativa](../desktop-pet/qa/initiative/initiative.png)

## Pruebas reproducibles

Desde `C:\karen\desktop-pet`:

```powershell
npm test -- --reporter=dot
npm run build
npm run test:voice:contracts
npm run test:styles
npm run test:variants
npm run test:initiative
```

Para comprobar el ejecutable y la síntesis Qwen local real, con reproducción muda:

```powershell
$env:KAREN_SMOKE_EXECUTABLE = 'C:\karen\desktop-pet\release\initiative-180-20261102\win-unpacked\Karen Desktop Pet.exe'
$env:KAREN_QA_INITIATIVE_VOICE = '1'
npm run test:initiative
```

Estos comandos usan perfiles temporales; no utilizan credenciales del perfil real,
no abren el micrófono y no envían peticiones al Gateway. El smoke de iniciativa
simula presencia y reloj del proceso principal y crea filas SQLite de prueba.
La voz opcional sí usa recursos Qwen reales de `C:\karen`. Tiene que estar instalada.

Resultados verificados antes de la entrega final:

- 161 pruebas TypeScript, 24 archivos: OK, 8,88 s.
- 25 contratos Python de voz: OK, 0,370 s.
- 165 pruebas de la clásica: OK, 22,636 s.
- 120 combinaciones de estilo/estado visual, teclado y movimiento reducido: OK.
- Iniciativa desde fuente y EXE: persistencia, pausa, denegación en No molestar,
  aviso automático sobre tarea controlada, revisión con envío explícito y voz local
  real cancelable: OK. No sustituyen una conversación física con el usuario.
- Se volvió a ejecutar el smoke del paquete final para incluir el globo a escala 50 %.
- Regresión de variantes desde fuente: juego de luz, estiramiento y estrellas
  con espera real; interrupción, reaparición, movimiento reducido y persistencia: OK.

Resultados JSON y capturas: `desktop-pet/qa/initiative/`. La medición de nueve
actualizaciones consecutivas fue 69,89 ms en el intercambio IPC de fuente y 76,81 ms
en la última prueba del EXE. **No mide tiempo de fotograma ni respuesta del modelo.**
No se inventa una mejora nueva de latencia de IA a partir de esa cifra.

## Paquete y arranque

NSIS x64 para Windows, sin firma y sin publicación:

`C:\karen\desktop-pet\release\initiative-180-20261102\Karen Desktop Pet Setup 1.8.0.exe`

- Tamaño: 129.230.005 bytes.
- SHA256: `8363ADC48E88AD09D4E558725EFDCDB0F6E585171C5F04A03DD7AE444C11C6A8`.

El resultado de instalación y los últimos smokes se registran en la sección 15 de
`IMPLEMENTATION_REPORT.md`: instalado, salida NSIS 0 y archivos cotejados con el
paquete. Se preservaron preferencias y vault; se habilitaron los dos interruptores
de iniciativa por petición explícita. Se observó conexión real a OpenClaw y el
indicador de escucha, sin enviar mensajes de prueba a la sesión del usuario.
Para desarrollo: `cd C:\karen\desktop-pet; npm ci; npm run dev`.
`npm ci` requiere acceso a las dependencias; esta entrega no añadió ninguna.

## Recuperación

- Código/datos anteriores: `backups/before-initiative-20261101/`, 202 archivos
  verificados. El nombre de ese directorio se creó al continuar el trabajo anterior.
- Entrega final con código, datos y diez capturas/reportes QA:
  `backups/delivery-interface-180-20261102/`, con manifiesto verificado.
- Ajustes y vault cifrado antes de instalar: `backups/pet-profile-before-180-20261102/`.
  Copia y hashes verificados, sin descifrar las credenciales.
- Para repetir una copia del perfil, cerrar Pet y ejecutar:
  `python qa/backup_pet_profile.py backups/NOMBRE_NUEVO`.
- Antes de revertir, cerrar Pet y respaldar el estado actual. Reinstalar el paquete
  1.7.0 conservado; los campos de iniciativa son adicionales y el diario separado es
  ignorado por esa versión. No es necesario restaurar conversaciones ni tareas.
- Restaurar ajustes antiguos solo si se desea deshacer preferencias. No sustituir
  una base SQLite nueva por una vieja sin exportar primero sus cambios.
- Si `initiative.json` se corrompe, cerrar Pet y copiarlo a un respaldo antes de
  apartarlo del perfil. Al arrancar sin ese archivo se crea un diario nuevo cuando
  se registra la primera propuesta; no se elimina el original automáticamente.

## Límites reales

No se implementó un agente autónomo general, automatizaciones de servidores,
captura continua, memoria semántica automática ni conversación de audio dúplex.
La iniciativa no infiere lo que aparece en aplicaciones externas ni registra teclas
fuera de sus propias ventanas. No anuncia eventos ocurridos mientras estaba cerrada.
No se validó nueva inferencia sin GPU ni estabilidad de varias horas. El arranque
frío del modelo de voz local puede seguir tardando; esta entrega conserva el motor
y la aceleración de la entrega anterior.

Se observó un arranque vacío intermitente en el perfil habitual. El diagnóstico no
encontró errores JavaScript y el arranque posterior mostró la interfaz completa.
La causa sigue sin aislarse. Si reaparece, usar el icono de bandeja para salir y
abrir de nuevo; conservar el perfil y consultar Diagnóstico cuando esté disponible.
No se borró la caché ni se cambiaron permisos del sistema para esta verificación.
