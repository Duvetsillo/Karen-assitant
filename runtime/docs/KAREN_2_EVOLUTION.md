# Karen 2: evolución incremental, 20 de noviembre de 2026

## Estado encontrado

Python/Tkinter, móvil/Jarvis HTTP y una mascota Electron separada. Core v1 comparte SQLite de conversaciones, preferencias, eventos y actividad. Core 2 ya ofrece modelos Ollama locales, exclusión mutua de inferencia, selección según RAM/VRAM, roles lógicos, planes con dependencias, permisos, cancelación/reanudación, evidencia cifrada, diagnóstico y visión manual. Se reutilizan esos componentes.

La memoria v1 ya era independiente del modelo. Core 2 añadía cuatro tipos y relaciones, pero carecía de historial de ediciones y procedimientos estructurados. Su búsqueda es léxica, acotada a 200 recuerdos recientes por proyecto. No había búsqueda vectorial. Marcar un paso como completado sin exigir evidencia permitía recordar un procedimiento incompleto.

Home Assistant contaba con descubrimiento REST mediante variables de entorno y un webhook privado limitado a cinco switches. El webhook y sus permisos permanecen intactos. La nueva conexión REST/WebSocket no reutiliza el secreto del webhook: son credenciales distintas.

Clásica y móvil pueden usar Core 2. La mascota conserva OpenClaw y comparte parcialmente Core v1; no se ha unificado su motor ni modificado ese repositorio. La coordinación de micrófono, voz y personalidad existente no se sustituye. Siguen pendientes las pruebas físicas de voz, sincronización simultánea y recuperación de periféricos.

## Memoria: contrato implementado

- Mismo archivo SQLite y contratos v1. Tablas y triggers aditivos; no se eliminan columnas ni conversaciones.
- Tipos `semantic`, `episodic`, `procedural`, `contextual`, `temporal`, `relational`; alias histórico `project` conservado.
- Estado `VERIFICADO`, `INFERIDO`, `PENDIENTE`, `DESACTUALIZADO`, confianza, importancia, procedencia, etiquetas, caducidad y clave opcional de hecho.
- Una clave de hecho igual con texto diferente genera una relación `contradicts`. No resuelve contradicciones mediante el modelo. Ambos extremos vigentes se excluyen del contexto confirmado de Core 2.
- Journal de contenido: captura inserciones y ediciones, incluso desde clientes antiguos. La primera apertura incorpora el estado actual; no reconstruye versiones que nunca existieron. Sustituir un recuerdo conserva el anterior y lo caduca para clientes v1.
- Consolidación propone revisión; nunca borra, fusiona o confirma información automáticamente. Grafo y consolidación muestran hasta 20 nodos actuales; recuperación considera hasta 200 recientes. Estos límites no representan una revisión exhaustiva.
- Procedimientos requieren plan completado y resultados de todos sus pasos. Guardado explícito mediante el flujo existente. Conservan objetivo, pasos, herramientas, dependencias, requisitos, permisos, riesgos, resultado esperado/real, versión de Core y ejecuciones con hashes de evidencia. El mismo ID de plan no incrementa dos veces el contador. Versiones externas no medidas quedan sin afirmar.
- Borrado selectivo elimina también versiones, relaciones, usos y evidencias asociadas. No borra copias de respaldo ya exportadas.
- Exportación pública ampliada conserva metadatos, versiones, relaciones y hashes de procedimientos. El respaldo SQLite existente de `maintenance.py` conserva la base completa y verifica integridad. No se restaura sobre una base activa.

Privacidad: no hay captura automática de conversaciones ni sensores hacia memoria. Escrituras contextuales rechazan patrones de credenciales en texto y metadatos; el filtro es heurístico y requiere revisión del usuario. Recuerdos sensibles se excluyen de recuperación, grafo, historial y exportación pública. Promover a sensible oculta también sus versiones anteriores. Core 2 limita el contexto del modelo a tres recuerdos confirmados de 400 caracteres; no envía toda la base. Las políticas previas de transferencia explícita de clientes v1 se conservan.

### Uso

```powershell
python memory_cli.py add Homelab 'Jellyfin usa puerto 8096' --kind temporal --fact-key jellyfin.port --tag servicio
python memory_cli.py search Homelab Jellyfin
python memory_cli.py history ID
python memory_cli.py procedure ID
python memory_cli.py timeline Homelab --kind temporal --since 2026-11-01T00:00:00+00:00
python memory_cli.py graph Homelab
python memory_cli.py consolidate Homelab
python memory_cli.py export-engine Homelab ARCHIVO_NUEVO.json
```

Opcional `--db RUTA_ABSOLUTA` antes del subcomando. Los comandos previos siguen disponibles.

API móvil autenticada existente, solo lectura para las nuevas rutas:

- `GET /api/core2/memory/graph?project=Homelab`
- `GET /api/core2/memory/consolidate?project=Homelab`
- `GET /api/core2/memory/timeline?project=Homelab&since=FECHA&until=FECHA&kind=temporal`
- `GET /api/core2/memory/ID/history`
- `GET /api/core2/memory/ID/procedure`

Fechas requieren zona horaria. Línea temporal y grafo son contratos de datos; aún no tienen una nueva visualización.

## Pendientes concretos

1. Índice semántico local opcional con modelo de embeddings instalado, invalidación por edición y filtros de privacidad. Actualmente solo hay búsqueda por palabras; cambiar modelo de conversación no afecta los recuerdos.
2. Revisión explícita de estados/metadatos y versiones completas de esos metadatos. Detección de contradicciones sin clave de hecho y consolidación semántica supervisada.
3. Paginación de recuperación/grafo y filtro temporal para reconstruir una configuración completa a una fecha. El journal permite consultar versiones individuales.
4. Interfaz Jarvis para gestión, línea temporal y mapa. Conservar su identidad visual; no rehacerlo.
5. Unificar motor/permisos de la mascota mediante contratos compartidos, con pruebas entre procesos. No modificar repositorios externos dentro de esta entrega.
6. Validación física de TTS, barge-in, activación Karen/Caren, esfera y mascota. No se cambió el motor de voz.

Las fases 4 y 5 no se amplían mientras permanezcan pendientes las bases de memoria e integración.

## Home Assistant: transporte y seguridad

Implementado y probado contra servidor local de prueba HTTP/WebSocket, sin dispositivos físicos:

- REST: descubrimiento dinámico de estados, control restringido y lectura posterior para verificar el resultado. Un POST aceptado por sí solo nunca confirma el estado deseado.
- WebSocket: autenticación, registros de áreas/dispositivos/entidades, suscripción `state_changed`, filtro explícito por entidad, reconexión acotada con backoff y cancelación cooperativa. Rechazo de autenticación detiene reintentos.
- Solo lectura por defecto. Lista de entidades y servicios permitidos, bloqueo prioritario, parámetros restringidos y aprobación concreta antes del control. Cerraduras, alarmas, scripts, escenas, automatizaciones y servicios administrativos no se habilitan en este módulo.
- DPAPI para URL/token/permisos en `.private/ha-api.dpapi`. Token capturado con entrada oculta; no se imprime ni incluye en errores/estado. Se rechazan redirecciones y HTTP fuera de loopback; no se desactiva TLS.
- Cada control recarga permisos del archivo protegido. Un cambio durante la aprobación cancela la operación. No hay reintento automático de escrituras.
- Core 2 registra `home_entities` de lectura y `home_control` sensible en el motor de planes existente. El segundo exige aprobación del paso y permiso de entidad; móvil no hereda la aprobación de escritorio. Los resultados pasan por verificador y auditoría de planes existentes.
- `/casa entidades` conserva variables de entorno y, cuando no están definidas, lee la misma conexión DPAPI. El webhook previo conserva su configuración y funcionamiento.
- `GET /api/core2/home/status` usa autenticación móvil existente y omite secretos. Informa último estado observado, no una comprobación continua.

```powershell
# Opcional: solo para WebSocket. REST reutiliza requests existente.
python -m pip install -r requirements-home.txt
python -m karen_core2.home configure https://SERVIDOR:8123
python -m karen_core2.home states
python -m karen_core2.home registries
python -m karen_core2.home events light.entidad_de_prueba
# Autoriza solo una entidad que conozcas. Exige confirmación escrita del ID.
python -m karen_core2.home allow light.entidad_de_prueba turn_on turn_off
python -m karen_core2.home block light.entidad_de_prueba
```

No se ejecutaron `configure` ni cambios de permisos sobre la instalación real. No se instalaron dependencias. `aiohttp` ya estaba disponible. Sin esa dependencia, REST y el resto de Karen siguen funcionando; WebSocket requiere instalar el archivo opcional.

Conexiones reales comprobadas: `GET /api/tags` de Ollama loopback respondió con nueve modelos locales. `/casa estado luz` del webhook existente devolvió `Luz: encendido.` No se enviaron órdenes de encendido/apagado. No existe configuración REST DPAPI ni variables REST en esta sesión; la conexión nueva contra el hogar real queda pendiente.

Pendiente: configurar URL/token de HA, validar registros/eventos contra esa instancia y autorizar una entidad de prueba. Después, integrar reglas de prioridad/No molestar e historial de alertas existentes; preparar diferencias de automatizaciones con aprobación, creación y verificación. Administración permanece deshabilitada. No se afirma aprendizaje automático del hogar ni comprensión natural dinámica de habitaciones.

Referencias de protocolo: [REST oficial](https://developers.home-assistant.io/docs/api/rest/) y [WebSocket oficial](https://developers.home-assistant.io/docs/api/websocket/).

## Validación y archivos de esta entrega

Suite completa final: `python -m unittest discover -s qa -p 'test_*.py'`: **294 pruebas, OK**. `compileall` y `git diff --check`: OK. Las pruebas cubren memoria entre instancias/modelos simulados, aislamiento por proyecto, contradicciones, rollback, versiones, respaldo/recuperación temporal, borrado, privacidad, procedimientos idempotentes, REST/WebSocket reales contra servidor de prueba, reconexión, permisos, revocación durante aprobación y planes HA con verificación. La continuidad conversacional con dos modelos físicos no se probó en esta entrega.

Archivos: `karen_memory.py`, `karen_core2/memory.py`, `memory_cli.py`, `mobile_server.py`, `karen_core2/home.py`, `karen_core2/runtime.py`, `ha_control.py`, `requirements-home.txt`, `qa/test_core2.py`, `qa/test_core2_mobile.py`, `qa/test_memory_engine.py`, `qa/test_home_engine.py` y este informe. No se modificaron configuraciones reales, conversaciones, mascota ni repositorios externos.

Clasificación: memoria y transporte/permisos HA **implementados y probados** en los límites anteriores; REST/WebSocket del hogar **preparados pero no conectados**. Voz física, interfaz visual de conocimiento, búsqueda vectorial, automatizaciones administradas y nuevas capacidades de fases 4–5 **pendientes**. No se declara una capacidad adicional terminada sin prueba.


## Entrega posterior: Karen nativa e interfaz (21 de noviembre de 2026)

Esta sección corresponde a cambios reales posteriores, autorizados por el usuario. Las frases anteriores sobre no modificar HA describen únicamente la primera entrega. Se detiene el trabajo al terminar la interfaz, según la última instrucción.

### Estado inicial y reutilización

El inicio de HA tenía un enlace a Jarvis. La entidad Fire TV anterior pertenecía a Jellyfin/Wholphin; no representaba todas las aplicaciones. Los trackers restaurados podían parecer recientes tras reiniciar HA. En Jarvis, abrir herramientas detenía una esfera todavía visible.

Se reutilizan Core 2, Ollama, historial SQLite, motor de planes, runtime de transcripción existente, voz local actual, autenticación HA, Assist y mascota gráfica existente. Se conservan interfaces clásica, móvil/Jarvis y mascota de escritorio. El componente Panorama y sus controles se conservan; las otras vistas del dashboard se compararon y permanecen iguales.

### IMPLEMENTADO Y PROBADO

- Agente nativo `conversation.karen`, con conversación de dos turnos comprobada desde HA hasta Core/Ollama. El segundo turno recordó el identificador del primero. Usa historial central sin cambiar el chat activo del escritorio.
- Canal de conversación separado del acceso móvil: credencial limitada, DPAPI en Windows, archivo 0600 en HA y socket Unix privado mediante SSH. Sin claves en tarjetas, repositorio ni logs. Reconexión comprobada tras reiniciar el Core. El agente no anuncia capacidad CONTROL ni ejecuta herramientas administrativas.
- Proveedores nativos `stt.karen` y `tts.karen`: contratos y transporte comprobados con audio sintético, sin cargar modelos durante la partida del usuario. Se creó pipeline Karen con estos proveedores y `prefer_local_intents=false`; el pipeline anterior se conserva.
- Inicio con tarjeta Karen: chat nativo, botón Assist del pipeline Karen, mascota que reacciona al estado de respuesta, borradores estables, errores visibles, texto del modelo sin interpretar HTML y conversaciones acotadas en pantalla. No abre Jarvis ni necesita exponer credenciales al navegador.
- Fire TV conectado mediante Android Debug Bridge con autorización explícita. HA reconoció Netflix y estado playing mientras el usuario reproducía Lupin. La tarjeta usa datos reales y abre el reproductor nativo sin enviar controles físicos durante las pruebas.
- Ubicación por dispositivo: GPS disponible, precisión, fecha de reporte real, última ubicación conocida y solicitud de actualización. Sensores propios guardan solamente fechas de reportes GPS válidos, nunca coordenadas ni direcciones adicionales. Un estado restaurado, no disponible o antiguo no confirma presencia actual. Precisión cero significa desconocida.
- Solicitudes de actualización aceptadas para los dos celulares. El iPhone envió posteriormente un nuevo reporte GPS; Mami no confirmó una posición actual durante la verificación. No se cambiaron permisos de teléfonos ni fuentes de personas/automatizaciones.
- Acceso HTTPS privado de HA en puerto 8443 mediante Tailscale, con proxy autorizado, sin Funnel. El servicio preexistente de 443 se conserva. Respuesta HTTPS real 200 y comprobación de configuración HA correctas.
- Esfera Jarvis: sigue animada al escribir y esperar respuesta con herramientas abiertas. Conserva pausa, suspensión fuera de vista y movimiento reducido.
- Interfaz real comprobada en escritorio y viewport móvil de 390 px: una columna, controles accesibles, sin desbordamiento horizontal de Karen. Se reforzó contraste sobre el fondo existente. No se sustituyó el dashboard completo.

### IMPLEMENTADO PERO NO VERIFICADO

La cadena física micrófono → reconocimiento local → respuesta hablada en el navegador no se probó mientras el usuario jugaba. Los proveedores y pipeline existen y pasan pruebas de contrato; esto no acredita calidad de voz, latencia o compatibilidad física de cada cliente. Para probarla, acceder mediante la URL HTTPS privada y usar «Hablar con Karen» tras iniciar sesión.

### PREPARADO PERO NO CONECTADO

El cliente REST/WebSocket de Core hacia HA sigue sin token REST configurado. Sus pruebas de servidor local, permisos, eventos y reconexión no equivalen a conexión real de ese cliente. Es distinto del canal HA → Karen, que sí está conectado y probado.

### Problemas observados y PENDIENTE

- Netflix devuelve metadatos vacíos en `dumpsys media_session`: aplicación y reproducción funcionan, pero el Fire TV no publica el título Lupin. No se inventa el título ni se promete obtenerlo de todas las aplicaciones.
- Mami conserva GPS antiguo sin nueva confirmación. Los sensores de dirección de los celulares están deshabilitados por la integración. Sin un reporte nuevo no puede afirmarse su ubicación exacta actual. No se envían coordenadas a geocodificadores externos.
- Permanecen entidades ajenas no disponibles, como air fryer y cargador. No se declara reparado todo HA.
- No se implementan conversación de voz continua con interrupciones, escucha permanente Karen/Caren en HA, sincronización completa de estados de la mascota de escritorio, latencia de la referencia Reddit, ni automatizaciones administrativas nuevas.
- Siguen pendientes búsqueda vectorial, consolidación aplicada con autorización, administración de automatizaciones y ampliaciones de fases 4–5. No se continúa con ellas en esta entrega.

### Archivos y comprobaciones

Cambios posteriores: `ha_conversation.py`, `ha_tunnel.py`, `ha_voice.py`, `mobile_server.py`, `integrations/home_assistant/custom_components/karen/`, `integrations/home_assistant/karen-home-card.js`, `integrations/home_assistant/karen-pet.png`, `deploy_ha_karen_card.py`, `qa/test_ha_conversation.py`, `qa/test_ha_voice.py`, `qa/test_jarvis_motion.py`, `qa/ha_native_contract.py` y este informe.

- Suite previa completa: 294 pruebas correctas, antes de ampliar la integración nativa.
- Suite específica posterior: `python -m unittest qa.test_ha_conversation qa.test_ha_voice qa.test_jarvis_motion`: 11 pruebas correctas. Tras agregar casos de GPS no disponible/precisión cero, las dos pruebas de navegador volvieron a pasar.
- `qa/ha_native_contract.py` ejecutado dentro del contenedor HA instalado: cliente HTTP, ConversationEntity sin CONTROL, persistencia de fechas sin coordenadas y proveedores STT/TTS correctos. Usa respuestas y audio sintéticos; no mueve dispositivos ni ejecuta inferencia.
- Sintaxis JS, compilación Python y comprobación de whitespace correctas. El detector visual señaló la imagen multimedia sin src inicial: permanece oculta hasta recibir imagen válida del proxy HA. Los avisos de colores/radios corresponden a esta superficie HA, que conserva el tema existente; no son una auditoría WCAG completa.
- Publicación estática verificada por SHA-256. Configuración guardada desde la interfaz HA comparada con la propuesta revisada; otras vistas sin cambios. Copias previas de configuración y base de datos permanecen privadas.

Para repetir el contrato en un host con el componente instalado: `docker exec -i homeassistant python - < qa/ha_native_contract.py`. No instala Home Assistant en Windows ni forma parte del descubrimiento normal de unittest.

Todos los cambios se organizan en commits de trabajo real y se suben individualmente a `codex/karen-core-2`. No se modifica la rama predeterminada. El archivo preexistente `ollama-openclaw.Modelfile` queda sin tocar.
