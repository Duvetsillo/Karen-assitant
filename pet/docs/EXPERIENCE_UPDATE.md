# Experience, Intelligence & Visual Update — 2026-11-26

## Alcance confirmado

Destino: Karen-assitant/main; Windows 11, RTX 2060 compartida de 6 GB.
Entrega instalada al terminar, con acceso de escritorio y datos conservados.
No reconstruir Core Python ni Pet Electron/React/Pixi. No descargar modelos,
activar APIs pagadas, desplegar Proxmox ni ampliar permisos por inferencia.

## Auditoría y reutilización

- UI: main.tsx, chat/, ModelPicker, Perception e InitiativePanel. Jerarquía de
  ajustes funcional pero todavía centrada en un chat convencional. Los tokens
  están dispersos entre style.css y settings-surface.css.
- Avatar: PetMachine, PresenceMotion, SpeechMotion, IdleActivities e IntroRenderer.
  Quince estados; scheduler de idle cíclico y prioridades parciales.
- Música: GSMTC por eventos, adaptador Windows, complemento autenticado, clasificador
  estricto y MusicCommentEngine. Reproductor mínimo de 330×400, apertura manual.
- IA: OpenClawAdapter filtra catálogo local y conserva sesión/memoria; una selección
  heredada cloud puede quedar activa y bloquear envíos. Core ya tiene LocalModels,
  InferenceQueue y ResourcePolicy: extender, no duplicar un servidor.
- Memoria/Obsidian/herramientas: implementadas en Core con promoción explícita,
  permisos de documentos y scheduler READ. No confundir chat de un modelo con hechos.
- Referencia conceptual revisada: https://github.com/lachydotmcg/capri-desktop
  (presencia, introducciones, controles discretos). Se conserva el personaje propio.

## Dirección de implementación

Construcción directa en código con recursos existentes. Presencia del personaje
como inicio; conversación como herramienta secundaria. Centro de control modular,
material oscuro sobrio y acentos hielo/lavanda; tipografía Segoe. Diseño centralizado
con variables semánticas. No se necesitan imágenes generadas ni otro stack.

## Fases y evidencia

- [x] 1. Tokens, presencia principal y centro de control con opciones reales.
- [ ] 2. Estados visuales, prioridades/blending, idle no cíclico y saludos.
- [ ] 3. Cápsula multimedia compacta/expandible y ocultación sin robar foco.
- [ ] 4. Manager/router local, selección razonada, disponibilidad y recursos.
- [ ] 5. Contexto optativo, permisos independientes y proactividad existente.
- [ ] 6. Regresión, QA nativa/medidas, documentación, paquete e instalación.

Proveedores sin adaptador, visión/captura no autorizadas y voz full-duplex no
certificada deben explicar su dependencia. Ningún control decorativo se presenta
como una capacidad funcional. Pruebas de escritura solo con datos temporales.

Base verificada anterior: 425 tests runtime, 210 Pet, 26 contratos de voz, cuatro
legacy y tres interoperabilidades. No constituyen evidencia de esta actualización.


### Fase 1 verificada

Inicio Presencia, personaje dominante y navegación secundaria. Centro de control
con trece áreas funcionales o dependencia explícita (Obsidian sin conexión directa
al panel); accesos Core preparan comandos sin ejecutarlos. Paleta y espaciado en
src/design/tokens.css. Se conservan presets, voz y vistas existentes.
210 tests Pet, typecheck y Vite correctos. QA nativa de 17 secciones en 1120×800
y 820×640, memoria preparada, búsqueda, borrador, copia y lectura segura sin errores.
Capturas antes reutilizadas del estado 84e5dd5; nuevas en qa/interface-design/after
(ignoradas por Git). Resto de fases e instalación final siguen pendientes.
