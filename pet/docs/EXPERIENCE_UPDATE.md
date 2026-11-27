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
- [x] 2. Estados visuales, prioridades/blending, idle no cíclico y saludos.
- [x] 3. Cápsula multimedia compacta/expandible y ocultación sin robar foco.
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


### Fase 2 verificada

Treinta estados independientes del proveedor, con prioridades de interacción/voz,
poses interpoladas y clasificación visual de metadatos reales de herramientas.
Cinco intensidades, selección no cíclica de idle y pausas variables. Reutiliza
parpadeo aleatorio, respiración y resorte existentes. Frecuencia de saludo:
inicio, diario, regreso tras dos horas de bloqueo/suspensión o solo vista previa.
El evento de regreso conserva la guardia de escritorio y no habilita micrófono.

Pet siempre flotante por petición del usuario. Los perfiles antiguos y peticiones
IPC no reactivan extremidades; se retiraron los controles correspondientes.
216 tests, typecheck/Vite/Electron correctos. QA nativa: treinta estados, ocho
formas flotantes, escalas 50/100/200 %, tres clips idle reales, interrupción por
tarea, persistencia, movimiento reducido y cero errores. Idle medido en 23 FPS;
CPU puntual de los dos renderers ~0,67/0,69 %, sin atribuirlo al total del sistema.
Regreso físico tras dos horas y audición humana siguen pendientes.


### Fase 3 verificada

Cápsula flotante de 392×88 DIP, ~80,5 % menos superficie que 380×465 anterior.
Se expande según controles/sesiones, con portada, progreso y transporte compacto.
Seek, volumen, aleatorio y repetición aparecen solo si la sesión los admite;
preferencias requieren historial autorizado. No deja un reproductor grande en ajustes.
Aparición automática optativa, guardia de escritorio, ocultación por pausa, cierre
respetado por pista, hover/clic y Escape. Color de portada opcional y local.
Interfaz común MediaProvider; otros reproductores Windows requieren metadatos
musicales nativos fuertes y nunca promueven un navegador ambiguo.

221 tests Pet y typecheck/Vite/Electron correctos. Electron/HTTP local real con
sesiones/control simulados verifica dimensiones, foco conservado, controles,
múltiples sesiones, filtrado, historial, ocultación real al pausar e IPC restringido.
La guardia Windows omitió la reapertura automática en esta pasada; casos seguro,
protegido y respuesta tardía están cubiertos en pruebas de política. No se afirma
aceptación comercial multiplataforma ni ausencia de fugas por estas pruebas.

### Fase 4: selección local verificada

Manager de metadatos bajo demanda que importa LocalModels y ResourcePolicy del
Core, sin duplicar su ranking. Consulta instalada real: ocho modelos válidos;
clasificación de código y ranking coherentes. Se rechazan marcadores cloud y
metadatos remotos. El endpoint se obtiene del proveedor Ollama de OpenClaw y se
valida como loopback. No carga pesos ni descarga modelos al consultar.

Once rutas, elección manual, catálogo/capacidades y seis perfiles visibles. El
router intersecta instalados, capacidades, presupuesto estimado y configuración
real del Gateway; confirma el cambio de sesión antes del envío. Fallback solo
antes de enviar, nunca repite una orden aceptada. Cancelación durante preparación,
cambio de conexión y envíos simultáneos cubiertos. Juego/Silencio no inician LLM;
los comandos Core deterministas continúan disponibles. Memoria y persona conservadas.

Arbitraje OS de inferencia compartido con Core; liberación al evento terminal o
cancelación. Se conserva el contrato del micrófono. Carga/descarga y parámetros de
inferencia del Gateway siguen bajo OpenClaw/Ollama: el cliente no inventa opciones
SDK ni descarga modelos compartidos. La reserva es estimada, no física. Otros
proveedores y gestión de pesos requieren su adaptador y se explican como límites.
233 tests Pet, 425 runtime, 26 contratos voz, typecheck/build y QA 17 secciones en
dos tamaños correctos. Confirmación normal instalada y empaquetado pendientes.
