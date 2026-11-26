# Roadmap por fases


## Nitidez y conversación de escritorio

- [x] Texturas adaptadas y primer plano de Awakening sin cuerpo/boca prematuros.
- [x] Regreso con fotograma preparado y despedida breve al salir.
- [x] Saludo con reloj de audio, reintento y salida seleccionada.
- [x] Tres formas del chat, editor multilínea y acciones secundarias agrupadas.
- [x] 197 pruebas y aceptación nativa de 54 secuencias más chat/despedida.
- [ ] Audición y aceptación visual humana; monitores físicos 4K/HiDPI.

## Solicitud independiente: Music Presence

- [x] Puente GSMTC por eventos con .NET del sistema y controles de capacidades.
- [x] Clasificador determinista conservador y complemento opcional restringido.
- [x] Minirreproductor, configuración, comandos offline y gestos del avatar existente.
- [x] Política de comentarios, cancelación y seis clips con la voz local original.
- [x] Memoria musical compartida, borrado aislado y resumen READ para scheduler.
- [x] Pruebas sintéticas, transporte/ventanas reales, interoperabilidad y mediciones.
- [x] Spotify Desktop real: detección, clasificación y minirreproductor con portada,
  sin órdenes de reproducción ni historial real.
- [ ] Certificar controles reales de Spotify Desktop, Spotify Web, Apple Music Desktop/Web, YouTube Music y
  YouTube musical en cuentas/aplicaciones reales. Validar llamadas, juegos,
  presentaciones y consumo prolongado. Aceptación auditiva humana.
- [ ] Configurar la exportación periódica a Obsidian con permisos explícitos;
  actualmente el resumen se exporta manualmente y READ puede programarse.

## Solicitud independiente: entradas cinematográficas de Pet

- [x] Seis secuencias con las ocho apariencias originales y transición al Pet.
- [x] Capa Electron independiente, cancelación, guardia Windows y fallback.
- [x] Preferencias persistentes, vista previa y comandos deterministas locales.
- [x] Generar 40 saludos con la voz local configurada y metadatos faciales.
- [x] Pruebas unitarias, nativas y matriz de las 48 combinaciones.
- [ ] Aceptación humana visual/auditiva, Escape físico, múltiples DPI/monitores,
  videojuegos y sesiones de presentación reales. Actualizar el ejecutable instalado
  cuando corresponda; esta entrega modifica fuentes y audios locales.

## Continuación del Core

- [x] Fase 0: inspección, contexto Obsidian, Git, pruebas base y mediciones.
- [ ] Fase 1: completar fundamentos. Router, permisos, planes y diagnóstico existen;
  eventos, cola con prioridades y cancelación de streams GPU al entrar en gaming
  se verificaron. Faltan eventos de todos los productores y cobertura completa de modos.
- [ ] Fase 2: completar memoria y conocimiento. Obsidian y handoffs integrados;
  move/rename/delete/open y edición YAML/tags/tareas implementados;
  memoria de usuario/autobiográfica/prospectiva y metadatos de acceso implementados.
  importación portable y revisión por recuerdo implementadas. Faltan capacidades
  documentales basadas en evidencia y aceptación humana de apertura.
- [ ] Fase 3: validar voz real, AEC/barge-in y transcripción incremental sin cambiar el timbre original.
- [ ] Fase 4: Pet y móvil consultan metadatos de automatizaciones/handoffs con los
  permisos existentes. Queda control documental remoto con alcances por cliente;
  ampliar roles solo cuando aporten valor y verificar percepción bajo demanda.
- [ ] Fase 5: scheduler READ con triggers, condiciones, cooldown, deduplicación,
  quiet hours, simulación e idempotencia verificados. Faltan productores adicionales
  de recursos/juegos y proactividad coordinada con preferencias del usuario.
- [ ] Fase 6: aceptación integral, restauración portable, endurecimiento y medidas repetibles.

Siguiente incremento: permisos por cliente para documentos, interfaz móvil y
productores de eventos basados en mediciones. Aceptación física de voz requiere al usuario.
Mantener pruebas con bases y vault temporal. La aceptación física de voz requiere al usuario.
No cargar embeddings ni otro modelo sin demostrar mejora medible.
