---
name: Karen Desktop Pet
description: Una criatura de vidrio holográfico que acompaña al asistente OpenClaw en Windows.
colors:
  action-lavender: "#b7b2f5"
  hologram-ice: "#8be4f3"
  connected-mint: "#96d9c3"
  warning-peach: "#f2c297"
  canvas-indigo: "#11141ef0"
  navigation-indigo: "#151824e8"
  field-indigo: "#151a28"
  control-indigo: "#202638"
  control-hover: "#30384f"
  navigation-selected: "#2c2c48"
  text-primary: "#edf0fb"
  text-secondary: "#a5adca"
  text-control: "#e1e7fa"
  text-selected: "#ddd7ff"
  divider: "#292e40"
  focus-lavender: "#c7c0ff"
typography:
  headline:
    fontFamily: '"Segoe UI Variable", "Segoe UI", sans-serif'
    fontSize: "27px"
    fontWeight: 600
    letterSpacing: "-0.025em"
  title:
    fontFamily: '"Segoe UI Variable", "Segoe UI", sans-serif'
    fontSize: "19px"
    fontWeight: 500
    letterSpacing: "-0.02em"
  section:
    fontFamily: '"Segoe UI Variable", "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 600
    letterSpacing: "-0.012em"
  body:
    fontFamily: '"Segoe UI Variable", "Segoe UI", sans-serif'
    fontSize: "14px"
    lineHeight: 1.65
  control:
    fontFamily: '"Segoe UI Variable", "Segoe UI", sans-serif'
    fontSize: "12px"
  label:
    fontFamily: '"Segoe UI Variable", "Segoe UI", sans-serif'
    fontSize: "11px"
    fontWeight: 500
  diagnostic:
    fontFamily: "Consolas, monospace"
    fontSize: "11px"
rounded:
  field: "7px"
  control: "8px"
  message: "9px"
  composer: "10px"
  toolbar: "12px"
  bubble: "13px"
spacing:
  control-gap: "8px"
  field-inline: "12px"
  compact-page: "24px"
  workspace-gap: "28px"
  page-inline: "32px"
components:
  button-primary:
    backgroundColor: "{colors.action-lavender}"
    textColor: "#202038"
    rounded: "{rounded.control}"
    padding: "8px 13px"
  button-primary-hover:
    backgroundColor: "#cdc7ff"
    textColor: "#202038"
  button-secondary:
    backgroundColor: "{colors.control-indigo}"
    textColor: "{colors.text-control}"
    rounded: "{rounded.control}"
    padding: "8px 13px"
  button-secondary-hover:
    backgroundColor: "{colors.control-hover}"
  input:
    backgroundColor: "{colors.field-indigo}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.field}"
    padding: "10px 12px"
  navigation-selected:
    backgroundColor: "{colors.navigation-selected}"
    textColor: "{colors.text-selected}"
    rounded: "{rounded.control}"
    padding: "11px 12px"
  message-assistant:
    backgroundColor: "#1c2232"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.message}"
    padding: "13px 14px"
  speech-bubble:
    backgroundColor: "#172136f5"
    textColor: "#e9f3ff"
    rounded: "{rounded.bubble}"
    padding: "13px 25px 13px 15px"
---

# Design System: Karen Desktop Pet

## Overview

**Creative North Star: "Vidrio de estudio"**

Karen es una criatura pequeña de vidrio holográfico: volumen azul hielo, aletas laminadas lavanda, cara hundida índigo y ojos luminosos con iris y reflejos. Su corazón incrustado y sus bordes orgánicos le dan identidad incluso con las partículas apagadas. Es una criatura original, no humana; el personaje vive en la ventana transparente del escritorio.

La interfaz de ajustes es una herramienta nativa de Windows: sobria, oscura y ordenada, con navegación lateral y controles junto a una vista de Karen. El panel combina material acrílico nativo de Windows 11 con capas índigo semitransparentes y niveles tonales, mientras el vidrio, los gradientes y el resplandor del personaje conservan su propia profundidad. La dirección se implementó directamente desde el brief; semilla de dirección registrada: `3a07d84c`.

**Key Characteristics:**

- Criatura de vidrio con silueta orgánica, aletas expresivas y corazón incrustado.
- Índigo oscuro para operar; hielo y lavanda para la presencia de Karen.
- Jerarquía nativa de Windows con controles discretos y foco visible.
- Movimiento suave, interrumpible y dependiente del estado real.
- Recursos gráficos locales que mantienen la identidad sin efectos adicionales.

## Colors

La paleta combina índigos profundos de trabajo con luz fría y lavanda suave; el frontmatter conserva los valores normativos extraídos del código.

### Primary

- **Lavanda de acción** (`action-lavender`): acciones principales, interruptores, rangos y acentos de navegación.
- **Hielo holográfico** (`hologram-ice`): tono inicial configurable del personaje, halo y partículas.

### Secondary

- **Menta conectada** (`connected-mint`): indicador de conexión confirmada.
- **Melocotón de aviso** (`warning-peach`): atención y recuperación de errores; Karen recibe también una variación naranja temporal.

### Neutral

- **Índigo de lienzo**, **índigo de navegación** e **índigo de campo**: distinguen el fondo, la barra lateral y los campos sin tarjetas anidadas.
- **Índigo de control** y **control en hover**: sitúan los botones secundarios dentro de la superficie.
- **Texto principal**, **texto secundario**, **texto de control** y **texto seleccionado**: separan lectura, ayuda y estados interactivos.
- **Separador**: organiza grupos y registros. **Lavanda de foco** hace visible la posición del teclado.

**The Estado Legible Rule.** Toda conexión o estado de Karen se acompaña de texto; el color nunca lleva por sí solo el significado.

## Typography

**Display and Body Font:** Segoe UI Variable, con Segoe UI y sans-serif como alternativas. La elección es deliberada para una herramienta nativa de Windows.

**Label/Mono Font:** Segoe para etiquetas; Consolas para datos técnicos y fragmentos de diagnóstico.

La letra tiene una presencia clara y tranquila. La densidad del panel se resuelve con jerarquía de tamaño, peso y espacio, sin transformar cada dato en un titular.

### Hierarchy

- **Headline:** título de página; tamaño y peso en `typography.headline`.
- **Title:** títulos del estado vacío de conversación; rol `typography.title`.
- **Section:** nombres de grupos de ajustes; rol `typography.section`.
- **Body:** base del documento y párrafos, con interlineado amplio; rol `typography.body`.
- **Control:** navegación, mensajes y campos principales; rol `typography.control`.
- **Label:** ayuda, etiquetas de campo, estados y diagnóstico; rol `typography.label`.
- **Diagnostic:** información técnica con ajuste de palabras para cadenas largas.

## Layout

Los ajustes usan una barra lateral fija de 198px. El espacio de trabajo restante contiene un encabezado y un área desplazable; esta última dispone controles flexibles y una vista lateral de Karen de 250px. Los márgenes horizontales de página y el espacio entre columnas corresponden a `spacing.page-inline` y `spacing.workspace-gap`.

Al llegar a 950px de anchura o menos, la barra lateral pasa a 175px, la vista de Karen a 200px, el espacio entre columnas a 20px y el margen del cuerpo a `spacing.compact-page`. La implementación conserva las dos columnas en el mínimo de escritorio revisado. Los grupos de ajustes se separan con una regla inferior, 25px de espacio inferior y 25px de margen; no añaden superficies independientes.

La ventana de mascota ocupa un lienzo totalmente transparente. El renderizador se centra y escala según su contenedor; los globos, la barra de acciones y el compositor se colocan en relación con ese lienzo. La vista de ajustes y la mascota comparten los mismos recursos del personaje.

## Elevation & Depth

El panel solicita material acrílico nativo de Windows 11 en una ventana con fondo transparente. La raíz del documento no pinta un fondo; el lienzo y la navegación añaden capas índigo semitransparentes según el frontmatter. Los niveles tonales y los bordes finos completan la profundidad sin sombras de tarjetas. El globo de conversación utiliza una sombra ambiental (`0 5px 18px #06112329`) para conservar legibilidad al superponerse al escritorio. Karen combina una sombra elíptica suave, halo radial, reflejos de borde, cara hundida y gradientes de vidrio; estos efectos se dibujan una vez en texturas locales.

**The Forma Antes de Efectos Rule.** La silueta, la cara y los ojos deben conservar la identidad de Karen con las partículas apagadas y con luminosidad reducida.

## Shapes

Los controles emplean esquinas suavizadas, con radios diferenciados para campos, botones, mensajes, compositor y globo según el frontmatter. Los interruptores son cápsulas y las muestras de tono son circulares. Las reglas finas organizan superficies sin añadir contornos pesados.

Karen se construye con curvas Bézier asimétricas, aletas altas y laminadas, pequeños brazos y una base festoneada. Los ojos contienen iris, brillo principal y reflejo secundario; la cara se integra como una cavidad en la carcasa. Los gradientes y las líneas de escaneo tenues pertenecen a ese material y no se convierten en decoración del panel.

## Components

### Buttons

Los botones son discretos y táctiles. El primario usa lavanda y texto índigo; el secundario usa índigo con borde fino. El hover cambia la superficie y el borde, y el estado presionado oscurece el secundario. El foco compartido es un contorno visible de 2px con separación de 3px. Los estados deshabilitados reducen opacidad. Los botones de icono llevan nombres accesibles y no usan glifos de texto como iconos.

### Inputs / Fields

Los campos tienen superficie índigo, borde fino y radio de campo. El foco coincide con los botones. El texto largo de respuestas y diagnósticos permite ruptura de palabras; las respuestas conservan sus saltos de línea. Los valores de los rangos usan cifras tabulares.

### Navigation

La navegación lateral mantiene icono, texto y estado seleccionado en una fila de al menos 43px. El seleccionado usa una superficie lavanda índigo y texto claro. El hover conserva un tratamiento tonal; la jerarquía no depende de animaciones.

### Status and Switches

La conexión combina punto, etiqueta y descripción. Los interruptores usan `role="switch"` y `aria-checked`; su deslizador cambia de posición y tono. Las muestras de color seleccionadas añaden contorno y marca visual.

### Messages and Speech Bubble

Los mensajes de usuario y asistente se distinguen por superficie y etiqueta. El compositor mantiene acciones junto al campo; el globo de la mascota tiene cierre accesible y texto seleccionable. Los errores aparecen como avisos con explicación y cierre, sin reemplazar el estado real de conexión.

### Karen

El renderizador de PixiJS reutiliza texturas originales locales para cuerpo, aletas, brazos, ojos, halo, sombra y partículas. Las transformaciones y unos pocos trazos faciales expresan los nueve estados: IDLE, LISTENING, THINKING, SPEAKING, HAPPY, CONFUSED, ERROR, SLEEPING y DRAGGING. No depende de imágenes remotas.

El movimiento usa amortiguación exponencial, flotación con ondas lentas superpuestas y parpadeos de intervalos variables. La boca responde a la energía de audio medida; SPEAKING sin audio no inventa movimiento labial. La cadencia máxima es 60 FPS en la mascota, 30 FPS en vista previa y 15 FPS en reposo o bajo consumo. El renderizado se pausa al ocultarse el documento; una caída de rendimiento reduce partículas. La resolución se limita a una densidad de 2.

Los controles usan transiciones de 150–180ms con `cubic-bezier(.23,1,.32,1)`. `prefers-reduced-motion` desactiva transiciones de controles y movimiento ornamental del personaje. La cara conserva la información de estado.

## Do's and Don'ts

### Do:

- **Do** conservar la silueta orgánica, la cara hundida, los ojos con reflejos y el corazón incrustado.
- **Do** usar el índigo para operar y reservar la luz fría más intensa para Karen y los estados que la necesitan.
- **Do** acompañar los estados con texto y mantener el foco de teclado visible.
- **Do** reutilizar texturas locales y animar transformaciones suaves e interrumpibles.
- **Do** respetar reducción de movimiento, reposo y bajo consumo.

### Don't:

- **Don't** convertir a Karen en una persona, una mujer anime, un emoji o un círculo con dos puntos por ojos.
- **Don't** añadir recursos gráficos remotos que puedan desaparecer.
- **Don't** comunicar conexión, error o actividad únicamente mediante color.
- **Don't** presentar movimiento labial sintético como prueba de audio real.
- **Don't** sustituir la jerarquía operativa del panel por tarjetas anidadas y efectos ornamentales.
