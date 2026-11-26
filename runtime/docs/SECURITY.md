# Seguridad vigente

Se conservan AdminRuntime, TaskEngine, Plans, esquemas, aprobaciones por operación,
DPAPI y autenticación de las APIs existentes. No hay shell arbitrario generado
por LLM ni autoridad procedente de documentos.

El vocabulario existente de permisos se mantiene: read corresponde a READ;
reversible a WRITE; sensitive a SENSITIVE; destructive a DESTRUCTIVE. No se
introduce aprobación global. EXECUTE y EXTERNAL requieren políticas específicas
en sus adaptadores existentes; no se infieren del texto del modelo.

Obsidian exige carpetas autorizadas, rutas relativas Markdown y hashes de lectura.
Rechaza traversal, rutas reservadas, carpetas ocultas, nombres sensibles, reparse
points, enlaces duros y credenciales detectables. Las escrituras pasan por Plans
y autorización exacta del paso, con lock cooperativo, backup y publicación atómica.
No se toca `.obsidian/`. Ver límites de carreras externas en KNOWN_ISSUES.

Las búsquedas devuelven `trust: untrusted_data`. No entran automáticamente al
prompt de conversación ni ejecutan instrucciones. La importación de conocimiento
revisado conserva su circuito de consentimiento anterior.

EventBus solo acepta topic, UUID/hash y códigos validados. El journal carece de
contenido de conversaciones, notas, argumentos o excepciones. Los detectores de
secretos reducen riesgo; no constituyen garantía de detectar toda credencial.

Handoffs son datos reportados cifrados en reposo. No modifican código, permisos,
políticas ni capacidades por sí mismos. Mantener `.private/` fuera de Git.

Delete de Obsidian exige confirmación ligada a plan_id y step_id. Un booleano
genérico no autoriza el paso destructivo. Move/rename nunca sobrescriben destino.
La apertura usa el protocolo local de Obsidian y requiere permiso sensible.

El scheduler vuelve a validar cada receta contra el registro actual. Solo READ
puede ejecutarse automáticamente; escrituras propuestas solo admiten simulación.
Un cambio de permiso bloquea y deshabilita la tarea. No se aceptan comandos libres.

FTS5 excluye recuerdos sensibles y verifica proyecto, caducidad y validación al
recuperar. Los clientes antiguos mantienen el índice mediante triggers. La ruta
MemoryStore rechaza nuevas credenciales antes de escribir datos o versiones.
Las reglas de lenguaje natural solo se aplican a la intervención actual del usuario.
La redacción cubre encabezados con esquema Bearer completo, valores de claves
privadas y asignaciones de contraseñas en español. Los marcadores de prueba son
sintéticos; los eventos continúan registrando solo metadatos validados.

La importación valida el paquete completo antes de escribir. La huella liga el
contenido y proyecto; cada promoción exige otra huella sobre recuerdo y procedencia
vigentes. Los duplicados privados o confirmados no se modifican ni exponen IDs.
Las declaraciones externas de verificación, relaciones y ejecución permanecen
reportadas. Los campos autoritativos del recibo de procedimiento no provienen de details.

Las nuevas lecturas de schedules/handoffs respetan core.read, autenticación móvil
y bases existentes. No descifran payloads ni conceden ejecución, edición, promoción
de memorias o acceso documental adicional. Pet no envía esas respuestas al Gateway.

Las políticas programadas solo aceptan predicados y temas de evento enumerados.
No contienen scripts, comandos ni instrucciones del modelo. Las métricas desconocidas
aplazan el trabajo. Los eventos se validan como metadatos, usan el reloj receptor y
no conceden permisos; los planes vuelven a comprobar READ antes de ejecutarse.
El runner permanece apagado por defecto. Las horas de silencio no borran pendientes.
