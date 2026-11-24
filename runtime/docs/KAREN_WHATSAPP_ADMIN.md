# Administración desde WhatsApp y recordatorios

Karen usa OpenClaw en WhatsApp. Es una integración distinta del chat Ollama de
la app móvil y del agente Admin de la ventana clásica.

## Qué se verificó

La política efectiva de exec del Gateway ya era `full` con `ask=off` y sandbox
desactivado. Una lista de ejecutables preaprobados vacía no bloquea ese modo.
Una prueba local del mismo agente ejecutó `Get-Date -Format o` mediante exec
y devolvió la fecha real. No se envió ningún mensaje de WhatsApp para probarlo.

`repair_openclaw_hints.py --apply` aclara los mensajes de runtime sobre la lista
vacía y la ausencia de procesos activos. Conserva la resolución de permisos,
las herramientas y sus políticas. Guarda el módulo anterior en `.private/`.
Es una corrección local de la instalación OpenClaw 2026.9.5; una actualización
puede reemplazarla. La herramienta rechaza formatos desconocidos.

## Privilegios reales de Windows

Ejecuta `./enable_karen_admin.ps1` y acepta el aviso UAC de Windows.
El script respalda el XML de las tareas OpenClaw Gateway y OpenClaw Node,
comprueba que sus acciones correspondan a OpenClaw, cambia RunLevel a Highest
y reinicia ambos servicios con sus comandos oficiales. No cambia identidad,
credenciales, disparadores ni puertos. El estado queda en
`.private/admin-setup-status.json`.

`python karen_admin_status.py` comprueba TokenElevation de los procesos actuales.
`elevated=true` prueba un token elevado; `false` indica permisos limitados y
`null` que Windows no permitió verificarlo. Guardar Highest sin comprobar el
proceso no prueba elevación. Las siguientes ejecuciones de las tareas conservan
Highest; puede restaurarse el XML respaldado desde una consola elevada.

Los comandos pedidos al agente heredan los derechos del Gateway. No se evita
UAC, no se conceden derechos por afirmar «soy administradora» y no se expone
el gateway fuera de loopback. El uso por WhatsApp conserva el control de
remitentes y autenticación de OpenClaw existente.

## Recordatorios relativos

Para una petición concreta como «recuérdame tomar agua en 30 minutos», Karen
debe ejecutar el helper con texto como un argumento separado:

```powershell
python C:/karen/friday_reminders.py --in-minutes 30 --message 'Tomar agua'
```

El helper calcula la fecha a partir del reloj real, crea un trabajo nativo de
una sola ejecución y solo confirma éxito cuando el programador devuelve un ID
habilitado. Para horas absolutas conserva `--at ISO_CON_ZONA`. Un trabajo ya
existente no se duplica ni se rehabilita automáticamente si está deshabilitado.

Comprobaciones sin programar ni enviar:

```powershell
python friday_reminders.py --check
python friday_reminders.py --in-minutes 30 --message 'Prueba' --dry-run
python -m unittest qa.test_friday_reminders qa.test_openclaw_hints
```

El receptor sigue siendo el WhatsApp personal previamente configurado en el
helper. El PC, Gateway y conexión WhatsApp deben estar disponibles para la
entrega. Programar un trabajo no demuestra recepción; hay que consultar su
estado de entrega. No se recrea el recordatorio citado por el usuario porque
no se conoce su texto ni se pidió volver a enviarlo.
