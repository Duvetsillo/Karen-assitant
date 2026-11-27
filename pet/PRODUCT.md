# Karen Desktop Pet

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Uso personal en Windows: conversar, trabajar y escuchar música con un asistente local que acompaña sin ocupar el escritorio. No se presupone un público comercial.

## Product Purpose

Dar presencia visible al asistente Karen: criatura flotante de vidrio holográfico, con aletas, ojos luminosos y corazón. El personaje refleja actividad y permite conversación por texto o voz. Éxito: entender su estado, encontrar ajustes y volver al trabajo sin interrupciones innecesarias.

## Positioning

Presencia animada conectada a la memoria y herramientas existentes de Karen Core y OpenClaw, con inferencia local verificada y permisos independientes del modelo.

## Operating Context

Electron en Windows; React, TypeScript, Zustand, PixiJS y audio local. Runtime Python en ../runtime. El servidor Node reutiliza la conexión oficial; las funciones de Windows requieren el cliente instalado. Obsidian, modelos y recursos de voz se conservan en sus raíces autorizadas; no se incluyen datos privados en paquetes.

## Capabilities and Constraints

Presencia, conversación, centro de control, 30 estados, ocho formas flotantes, saludos/despedida, música optativa y contexto general opcional. El manager consulta LocalModels del Core y selecciona modelos instalados/configurados para la tarea. Solo cambia el modelo de la sesión; OpenClaw mantiene herramientas y sus permisos. Ollama administra la carga/descarga. No se simulan proveedores ausentes ni reservas físicas de GPU. No hay cámara, keylogging ni captura permanente de audio/pantalla. La voz física, AEC y llamadas de navegador requieren aceptación humana adicional.

## Brand Commitments

Karen; «Vidrio de estudio». Compañía serena y clara en español. Mantener el cuerpo flotante sin brazos ni piernas, aletas y expresiones; no representa a una persona. Conservar las ocho variantes y los recursos locales existentes.

## Evidence on Hand

docs/EXPERIENCE_UPDATE.md distingue pruebas, transporte simulado, medidas y límites. QA nativa y capturas se generan en qa/ (fuera de Git). No hay testimonios ni métricas comerciales; no inventarlos.

## Product Principles

- El personaje protagoniza; los controles aparecen cuando hacen falta.
- El estado visible corresponde a evidencia real.
- Observar, interpretar y actuar conservan permisos separados.
- Una conversación conserva identidad y memoria al cambiar de modelo.
- Los fallos indican un siguiente paso y no repiten acciones aceptadas.

## Accessibility & Inclusion

Teclado, foco visible, movimiento reducido y escalas configurables. No se afirma conformidad WCAG completa ni accesibilidad de lectura del canvas sin una auditoría.
