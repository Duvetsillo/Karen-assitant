---
name: Karen
description: Conversación nativa en español, encabezado verde y superficies claras.
colors:
  brand-green: "#146B55"
  brand-active: "#0F5845"
  canvas: "#EAF1ED"
  panel: "#FFFFFF"
  input: "#F1F6F3"
  text: "#173D32"
  muted: "#526C62"
  border: "#9DB9AC"
  welcome: "#E8F4ED"
  hover: "#DFEEE6"
typography:
  headline:
    fontFamily: "Bahnschrift"
    fontSize: "28pt"
    fontWeight: 700
  body:
    fontFamily: "Segoe UI"
    fontSize: "13pt"
    fontWeight: 400
  control:
    fontFamily: "Segoe UI"
    fontSize: "10pt"
    fontWeight: 400
rounded:
  square: "0px"
spacing:
  small: "4px"
  control: "12px"
  panel: "16px"
  inset: "24px"
---

# Design System: Karen

## Dirección

Un escritorio claro para conversar. El verde profundo identifica a Karen y las
acciones principales; la conversación ocupa una superficie blanca amplia.
Bahnschrift da jerarquía a los títulos y Segoe UI mantiene controles familiares.
Diseño implementado en Tkinter: `ui.py`, con estados en `karen_app.py`.

La búsqueda de ui-ux-pro-max sugirió Flat Design y una familia teal. Su estructura
promocional no corresponde a este cliente. Esta implementación adapta la paleta
y las reglas generales de jerarquía, contraste y foco a una aplicación nativa;
no es una coincidencia de stack Tkinter en la base de la skill.

## Estructura

- Encabezado compacto: identidad, propósito y estado con texto explícito.
- Columna de 360 px con pestañas Modelo, Audio y Pruebas. Ajustes desplazables.
- Conversación flexible con cuerpo de 13 pt y autores diferenciados.
- Bienvenida con tres sugerencias que preparan el mensaje; no lo envían.
- Campo con etiqueta Tu mensaje y acción Enviar siempre al pie.
- Ventana inicial 1360 × 900; mínimo de área cliente 1180 × 850.

## Interacción

Enter envía el mensaje; Ctrl+L enfoca el campo. El foco en ajustes inferiores
desplaza su panel para mantenerlos visibles. Botones con estados de hover,
foco y deshabilitado, sin movimiento del contenido ni animación decorativa.
La bienvenida desaparece al registrar el primer mensaje del usuario.
El estado de micrófono, errores y procesamiento conserva texto visible.

## Funciones preservadas

Modelos locales y `gemma4:31b-cloud`, selección por nodo, reconocimiento,
voz, cancelación, reintentos confirmados y controles Aetherion.
La selección cloud indica que las preguntas se envían a Ollama Cloud.
Las pruebas de modelos requieren una acción explícita del usuario.

## Verificación

`qa/verify_voice.py` valida captura, cancelación, estados, sugerencias sin envío,
ocultación de bienvenida y desplazamiento al foco de teclado.
`qa/verify_redesign.py` valida catálogo, sesiones, respuesta final y benchmark.
Capturas de la ventana propia mediante PrintWindow en tamaño inicial y mínimo:
`qa/karen-ui-ux-pro-max.png` y `qa/karen-ui-ux-minimum.png`.
Estas comprobaciones no equivalen a una auditoría con lector de pantalla.
