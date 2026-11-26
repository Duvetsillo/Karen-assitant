# Karen Home Glass — 24 de noviembre de 2026

El usuario pidió sustituir el diseño claro por una interfaz homogénea tipo Apple
Home, oscura, con vidrio y un fondo natural compartido. Esta entrega sucede a
Karen Calm; el nombre interno del tema se conserva para no romper preferencias.

## Implementación

- Un fondo local de bosque y lago con niebla, generado para esta interfaz.
- Material común de vidrio carbón, texto claro y acentos ámbar de estado.
- Radio de 22 px, reflejo interior discreto y blur de 18 px; navegación y accesos usan 12 px en móvil.
- Accesorios nativos dispuestos verticalmente, alineados a la izquierda; dos
  columnas en móvil. Se conservan handlers, permisos, diálogos y teclado de HA.
- Navegación, lecturas, accesos, chat, ubicaciones y contenido multimedia usan
  la misma paleta y material. Fondo estable entre las vistas principales.
- Sin nuevas librerías, servicios de IA obligatorios ni controles físicos nuevos.
  No se modifica memoria, selección de modelos ni ejecución de herramientas.
- Fallback opaco para navegadores sin backdrop-filter. Presión visual acotada,
  sin animaciones perpetuas, y respeto a prefers-reduced-motion.

## Recursos

`integrations/home_assistant/karen-home-forest.png` es el fondo de producción.
`docs/design/ha-homekit-dark-reference.png` es una referencia ilustrativa, no una
captura de HA ni una prueba de estados. La primera propuesta clara se descartó
al recibir la corrección del usuario. No se usa como resultado final.

Se adaptan las skills design-taste-frontend-v1, frontend-design e
imagegen-frontend-web a la aplicación existente. La homogeneidad, el modo oscuro
y Apple Home mandan sobre recetas de marketing, variación extrema o movimiento
continuo. Se mantiene HA nativo; no se incorpora React, Tailwind o iconos nuevos.

## Verificación

Las 15 pruebas específicas de contexto, privacidad, HTTP, voz sintética,
conservación de configuración, XSS/borradores y animación pasaron tras cambiar
el material. Sintaxis JS y comprobación de whitespace correctas. La publicación
estática y el fondo se validan por SHA-256. Se conservan copias previas del
dashboard y recursos; las revisiones de tema y código permanecen en Git.

Aceptación visual real: Inicio de escritorio y móvil de 390 px, sin desbordamiento;
dos columnas de accesorios de 168 px en móvil. CSS calculado: vidrio rgba(25,36,41,.78),
radio 22 px y blur 18 px; disposición vertical de 142 px y acción de icono nativa
conservada. Karen y Familia comparten la misma superficie. Los iconos de luz,
abanico y nevera se ajustaron a su función real, sin cambiar entidades o acciones.
Las imágenes generadas son referencias y el fondo; no sustituyen pruebas de HA.

Voz física y conversación general siguen con los límites de la entrega anterior;
esta entrega es visual. No se accionan luces, enchufes o escenas durante QA.
