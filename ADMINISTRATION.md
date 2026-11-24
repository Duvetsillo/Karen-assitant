# Administración de Karen

La pestaña **Admin** activa el agente de administración para el modelo Ollama
seleccionado. También muestra el nivel de privilegios de Windows, los destinos
autorizados y el registro de operaciones.

## Uso

Escribe una petición concreta, por ejemplo:

- «Lista los procesos de mi PC y resume el consumo».
- «Abre la aplicación NOMBRE», usando su nombre instalado.
- «Consulta el espacio disponible en mis discos».
- «Revisa el servidor Home».
- «Copia el archivo C:\\ruta\\origen.txt a C:\\ruta\\copia.txt».
- «Reinicia el servicio NOMBRE».
- «Configura Docker en friday-home», especificando el cambio deseado.

El prefijo `/admin` fuerza el agente cuando una frase no activa la detección
normal. Las preguntas que comienzan con «cómo» conservan el flujo de explicación.
El calendario iCloud conserva su integración propia.

## Capacidad

Las herramientas específicas consultan sistema, CPU/RAM, procesos, servicios,
aplicaciones del menú Inicio, discos, conexiones, tareas programadas, eventos,
archivos y destinos. Permiten abrir carpetas/aplicaciones, copiar/mover/escribir
archivos, crear carpetas, enviar elementos a la papelera, detener procesos,
gestionar servicios y programar apagado/reinicio con 30 segundos de margen.

PowerShell local y scripts SSH amplían la capacidad a instalación de software,
reparaciones, configuración, Linux, Windows con SSH, Docker y Proxmox. Estos
scripts siempre requieren revisión y aprobación del usuario. El script y su
comprobación posterior aparecen completos en la ventana de confirmación. El
modelo debe crear respaldos antes de editar configuraciones; en scripts generales
esto se comprueba al revisar el script, no mediante una garantía automática.

La escritura de texto con la herramienta específica crea una copia del archivo
previo. La copia específica no sobrescribe destinos existentes. La eliminación
específica usa la papelera; no realiza eliminación permanente recursiva.

## Autonomía y acceso

Consultas y apertura de recursos son directas. Crear carpetas y copiar archivos
en el proyecto, Documentos, Escritorio y Descargas son tareas habituales directas.
Otros cambios de archivos, detención de procesos, servicios, apagados/reinicios y
scripts generales requieren confirmación. Cancelar no ejecuta la operación.

Karen conserva los permisos del usuario que la abre. **Reabrir con privilegios ·
UAC** solicita elevación mediante Windows y abre otra instancia. La instancia
anterior se cierra cuando Windows acepta el lanzamiento. La nueva instancia
recupera la configuración guardada y el último chat. Esta función no evita UAC
ni obtiene privilegios por sí sola. La elevación real necesita interacción del
usuario y no forma parte de las pruebas automáticas.

Los destinos SSH deben existir en `~/.ssh/config`, con autenticación no interactiva
y clave de host conocida. Se usa `StrictHostKeyChecking=yes`. Para Windows remoto,
el script SSH selecciona `shell=powershell`; para Linux usa `sh`. La consulta SSH
específica de estado está destinada a Linux/Proxmox.

Autoriza nuevos aliases o subredes desde Admin. La exploración admite subredes
IPv4 privadas de hasta 256 direcciones. Descubrir un equipo no concede acceso
administrativo. Las herramientas de red y SSH validan sus destinos contra
`admin_policy.json`. Los scripts generales tienen acceso a los recursos del
usuario; su alcance completo debe revisarse antes de aprobarlos.

## Resultados y límites

El agente procesa hasta ocho herramientas por petición, de forma secuencial.
Rechazos, fallos, tiempos agotados y operaciones repetidas detienen el flujo.
No hay reintentos automáticos de cambios. Un timeout puede dejar un resultado
incierto; se debe consultar el estado antes de repetir una operación.

El registro `.private/admin-audit.sqlite3` conserva herramienta, parámetros,
estado e identificador. Scripts, comprobaciones y texto escrito se representan
por SHA-256 en el registro; no se guarda su contenido allí. Los resultados se
envían al modelo seleccionado para elaborar la respuesta. Con un modelo Cloud,
esos datos salen del PC. El historial de conversación conserva la respuesta
visible según las reglas normales del cliente.

El agente requiere un modelo Ollama compatible con herramientas. La API Karen
personalizada conserva sus operaciones locales previas y no recibe este protocolo
de herramientas nuevo. Los resultados de lanzamiento solo confirman aceptación
por Windows, no la aparición de una ventana. Las listas y lecturas están acotadas;
no constituyen un inventario exhaustivo.

## Gmail

Karen busca y lee mensajes seleccionados mediante el OAuth local de gog. La cuenta conectada inicialmente es `dayvermoreta@gmail.com`.
Para leer, primero busca y usa el ID real devuelto por Gmail; el cuerpo se entrega
al modelo y se trata como contenido externo no confiable. La lectura no cambia
el mensaje. El permiso de lectura/envío ya configurado es suficiente.

Karen también puede crear un recordatorio cuando se lo pidas, con fecha/hora y
texto claros. Se programa en el scheduler personal existente y se entrega al
WhatsApp personal documentado. Esto no crea eventos de calendario ni envía
correos. Si falta la zona horaria u otro dato necesario, Karen debe preguntarlo.

Además, mueve los mensajes seleccionados a la papelera mediante el OAuth
local de gog. La cuenta conectada inicialmente es `dayvermoreta@gmail.com`.
Puedes pedir «Borra los correos promocionales de mi Gmail». Se consultan las
cuentas, se buscan mensajes reales y se muestra cuenta, remitente, asunto, fecha
e ID antes de pedir confirmación. El límite es 25 mensajes por operación.
El correo se trata como contenido externo, nunca como instrucciones.

En Admin, **Permitir borrar correos · Google** abre el consentimiento de Google
para la cuenta seleccionada. El permiso existente de lectura/envío no basta:
se solicita `gmail.modify`, manteniendo lectura y envío. La función queda
habilitada cuando Google confirma el permiso. El adaptador utiliza `gmail trash`,
con IDs explícitos y sin borrado permanente, y comprueba la etiqueta TRASH después.
Un error o resultado parcial detiene el flujo sin repetir el borrado.

Las pruebas `qa/test_gmail_tools.py` usan mensajes sintéticos. No se borran
correos reales para probar la integración. La operación requiere consentimiento
OAuth del usuario y aprobación de una selección concreta de mensajes.

El permiso necesario está documentado en [messages.trash de Google](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/trash?hl=en).

El chat OpenClaw comparte el adaptador mediante `automation/friday_mail.py`:
`capabilities` consulta permisos actuales; `prepare-trash --account CUENTA
--query FILTRO --max 25` devuelve metadatos y un plan sin borrar; `trash --plan
TOKEN --confirm` se usa únicamente tras confirmar esa selección. El plan está
vinculado a su contenido mediante SHA-256, expira en 15 minutos y solo puede
invocarse una vez, incluso si el resultado es incierto. Las instrucciones del
chat y su memoria reflejan el permiso gmail.modify actual; no deben reutilizar
respuestas históricas de solo lectura/envío para negar esta capacidad.

## Verificación

`qa/test_admin_runtime.py` cubre validación, autorización, denegación sin ejecución,
rutas protegidas, respaldos, sobrescritura, incertidumbre, comprobación posterior,
deduplicación, aislamiento SSH y herramientas del modelo. `qa/test_conversations.py`
incluye los controles de escritorio y la cancelación de confirmación.
`qa/verify_admin_live.py` consulta el PC y los aliases autorizados sin cambios en
el sistema, comprueba una llamada real del modelo a una herramienta y valida
la escritura de un archivo sintético en un directorio temporal aislado.

La integración sigue el [protocolo de herramientas de Ollama](https://docs.ollama.com/capabilities/tool-calling).
El lanzamiento elevado usa [Start-Process con RunAs de Microsoft](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1).
