# Karen — interfaz Jarvis y acceso desde el escritorio

> El diseño visual de anillos descrito aquí fue sustituido por la [presencia de partículas](KAREN_JARVIS_PARTICLES.md), siguiendo los vídeos aportados después por el usuario. Los lanzadores y el acceso directo siguen vigentes.

Actualizado: 19 de noviembre de 2026, America/La_Paz.

## Solicitud y alcance

El usuario aportó referencias de interfaces tipo Jarvis: núcleo luminoso,
anillos concéntricos, paneles oscuros e instrumentación cian y ámbar.
Esta actualización adapta `/jarvis` a esa dirección visual. La aplicación
clásica y el chat móvil habitual conservan sus puntos de entrada.

La vista alternativa reúne el núcleo animado en el centro, los recursos y la
memoria a la izquierda, y conversación y actividad de sesión a la derecha.
Los planes permanecen debajo, accesibles desde la navegación y desde el núcleo.
En teléfono, los paneles se apilan sin desplazar contenido fuera de pantalla.

## Uso

Abre **Karen Jarvis** en el escritorio de Windows. El enlace ejecuta
`C:\karen\launch_jarvis.ps1` sin dejar una consola visible. Si el servidor
móvil ya responde, lo reutiliza. Si no existe un listener en el puerto 18793,
inicia el mismo `mobile_server.py` en segundo plano y espera a que esté listo.
No detiene procesos ni sustituye servicios que ocupen el puerto.

Microsoft Edge abre la vista en una ventana de aplicación, maximizada.
Si Edge no está disponible, se usa el navegador predeterminado.
No es una aplicación nativa nueva: comparte el servidor y núcleo existentes.

- URL local: `http://127.0.0.1:18793/jarvis`.
- Acceso privado del iPhone: conserva la misma URL anterior con `/jarvis`.
- Chat habitual: enlace **Chat clásico** en la cabecera y junto a la conversación.
- Acceso: el mismo código privado. Otro navegador puede pedirlo una vez.
- Reinstalar el enlace: `powershell.exe -NoProfile -File .\install_jarvis_shortcut.ps1`.
- Comprobar el servidor sin abrir ventana: `powershell.exe -NoProfile -File .\launch_jarvis.ps1 -NoOpen`.

El lanzador consulta Tailscale, si está disponible, para conservar los orígenes
privados del teléfono al iniciar un servidor. No cambia la configuración de
Tailscale ni publica el puerto en la red local o en Internet. No incluye códigos
de acceso, tokens ni contraseñas en el enlace o en estas notas.

## Núcleo y controles visuales

Los gráficos son SVG y CSS locales; no usan WebGL, vídeos, modelos adicionales,
fuentes remotas ni bibliotecas nuevas. Los anillos giran lentamente en reposo y
cambian de ritmo cuando existe una solicitud pendiente. El indicador muestra
disponibilidad del núcleo y de Ollama; no representa conciencia ni garantiza
que una acción haya terminado.

**Animación** pausa o reanuda los anillos. **Color** alterna cian y ámbar.
Ambas preferencias quedan en el almacenamiento del navegador. También se respeta
`prefers-reduced-motion` y se pausa el movimiento cuando la página está oculta.
La animación usa transformaciones CSS con velocidad lineal; no ejecuta un bucle
JavaScript de renderizado. El único temporizador permanente es el reloj de La Paz.

La actividad está limitada a veinte eventos en esta sesión del navegador.
No reemplaza la auditoría persistente del ejecutor. El porcentaje de CPU se
identifica como última muestra; si envejece más de cinco minutos aparece el aviso.
RAM y VRAM disponibles proceden de las sondas existentes. No se muestran valores
inventados para energía, micrófono, correo o notificaciones.

La conversación conserva el mismo contrato HTTP y la inferencia local de Core 2.
Preparar un plan no lo ejecuta. Las escrituras mantienen sus aprobaciones.
Visión sigue plegada y pausada; su ampliación continúa pendiente según lo acordado.

## Verificación de esta actualización

- `node --check mobile/jarvis.js`: correcto.
- `python -m unittest qa.test_core2_mobile qa.test_mobile_server`: 30 pruebas correctas.
- Scripts PowerShell analizados y ejecutados para instalar el enlace y reutilizar
  el servidor mediante `-NoOpen`. El `.lnk` apunta al lanzador y directorio correctos.
- Navegador con bases temporales: diagnóstico real de seis pasos verificado,
  cambio de color, pausa/reanudación de animación y conservación de preferencias
  después de recargar. Ninguna operación de mantenimiento destructivo.
- Chat real con `gemma3:1b`: respuesta de Ollama recibida junto al holograma.
- Navegador a 390 px: 380 px de contenido y 380 px útiles; sin desbordamiento horizontal.
- Sin errores ni advertencias de consola en la sesión de aceptación.
- Captura de evidencia local: `C:\karen\qa\karen-jarvis-hud.jpg`.

No se repitieron las suites de voz y Pet: esta actualización solo modifica
archivos de la vista web y añade lanzadores. Sus resultados anteriores constan
en `KAREN_CORE_2_ACCEPTANCE.md`. Sigue pendiente la prueba física en Safari.
La ruta de arranque de servidor detenido está implementada; en esta aceptación
el servidor ya estaba activo y se comprobó su reutilización.

## Archivos y recuperación

- `mobile/jarvis.html`: estructura y núcleo SVG.
- `mobile/jarvis.css`: identidad visual, distribución y movimiento accesible.
- `mobile/jarvis.js`: estados, actividad, preferencias y conexión a funciones existentes.
- `launch_jarvis.ps1`: reutilización/inicio del servidor y ventana de aplicación.
- `install_jarvis_shortcut.ps1`: creación del enlace y copia del anterior si existe.

Punto previo: etiqueta Git `recovery/jarvis-before-hud-20261119`.
Los cambios se guardan en commits locales separados. No se sobrescriben
credenciales, configuración de modelos ni bases del usuario. Rebecca no se modifica.
