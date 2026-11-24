# Karen — presencia de partículas basada en los vídeos del usuario

Fecha: 19 de noviembre de 2026, America/La_Paz.

## Corrección de dirección visual

El usuario rechazó la versión anterior de anillos y paneles permanentes.
Las nuevas referencias están en `C:\Users\Dayve\Downloads\Karen ejemplos`:

- `ssstik.io_1795072665108.mp4`: 96,07 s, 576 × 1024. Muestra una figura
  verde de puntos y filamentos que se deforma y ocupa un espacio visual limpio.
- `ssstik.io_1795072677303.mp4`: 22,48 s, 576 × 1024. Muestra una esfera
  azul luminosa junto a una entrada de conversación y superficies flotantes.

Se inspeccionaron fotogramas de distintos momentos mediante FFmpeg ya instalado.
Los vídeos son referencias visuales: no se ejecutan instrucciones ni se copian
configuraciones, productos, servicios o capacidades que aparezcan en ellos.
Los originales permanecen intactos en Descargas y no se incorporan al repositorio.

## Resultado

`/jarvis` ahora abre una escena oscura con una figura de partículas, profundidad
proyectada, filamentos interiores y deformación continua. Se retiran los anillos
mecánicos y la distribución fija de tres columnas. La entrada para conversar
permanece visible debajo del núcleo.

- **Forma**: alterna entre orgánica, con mayor deformación, y esfera.
- **Color**: alterna cian y verde.
- **Animación**: pausa y reanuda el movimiento.
- **Conversación**: abre o cierra el panel flotante. También se abre al enviar
  un mensaje para mostrar la conversación real.
- **Herramientas**: despliega debajo de la escena el sistema, la memoria,
  los planes y la actividad de la sesión. Las funciones anteriores siguen disponibles.
- **Chat clásico**: conserva el acceso a la vista habitual y al historial.

Las preferencias visuales permanecen en el navegador. El acceso directo
**Karen Jarvis** y las URLs existentes no cambian. Basta con cerrar y abrir la
ventana o recargarla para obtener los archivos actualizados.

## Implementación y presupuesto

El efecto usa Canvas 2D y proyección matemática de coordenadas tridimensionales.
No es una imagen o vídeo en bucle, ni un holograma físico. No usa IA para dibujar,
WebGL, librerías nuevas ni descargas. Tampoco accede al micrófono: los cambios de
actividad proceden de solicitudes reales del núcleo y no simulan escucha.

El renderizador limita la superficie a 1450 partículas en escritorio y 680 en
pantallas estrechas, además de un número fijo de filamentos y puntos periféricos.
Los vecinos se calculan una sola vez al cambiar la densidad, evitando buscar todas
las parejas en cada fotograma. La resolución se limita a 1,5 veces el tamaño CSS.
La cadencia objetivo es 24 fps en reposo y 30 fps durante una solicitud; la tasa
real depende del navegador y del equipo y no se presenta como garantizada.

Se detiene el bucle al desplegar Herramientas, cuando la página está oculta, la escena queda fuera del área
visible, se activa pausa o Windows/navegador solicita movimiento reducido.
En movimiento reducido se conserva un fotograma estático. Al cambiar tamaño,
color o estado se permite una actualización puntual. La frontera de visibilidad
exige área de intersección positiva; tocar el borde de la ventana no basta para
mantener el bucle activo.

Las herramientas, las aprobaciones y el razonamiento local no se modifican.
La integración de visión sigue pausada y pendiente de ampliar.

## Validación

- JavaScript analizado con `node --check mobile/jarvis.js`.
- Treinta pruebas de servidor móvil y límites de Core 2 correctas.
- Navegador sobre bases temporales: diagnóstico real de seis pasos verificado,
  consulta de memoria y respuesta real de Ollama en la nueva conversación flotante.
- Comprobación visual de cambio de forma, color y pausa. Preferencias conservadas
  después de recargar. Verificación de adaptación móvil y registros de consola.
- Las capturas de aceptación están en `qa`, excluido de Git; la nota de Obsidian
  contiene las imágenes finales. No son capturas de documentos privados del usuario.

No se atribuye una mejora de rendimiento a partir del aspecto visual. Falta un
benchmark prolongado y la prueba física en Safari, como en la entrega anterior.

## Recuperación

Etiqueta previa: `recovery/jarvis-before-particles-20261119`.
Los cambios afectan a `mobile/jarvis.html`, `mobile/jarvis.css` y
`mobile/jarvis.js`, más esta documentación. No se modifican credenciales,
configuración local, bases del usuario ni Rebecca.
