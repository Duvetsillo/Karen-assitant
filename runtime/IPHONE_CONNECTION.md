# Karen desde iPhone

## Alcance corregido por el propietario

El usuario aclaró que busca automatizar ubicación y apps del iPhone, comenzando
por llegar/salir de casa o trabajo. No busca el panel de OpenClaw. El acceso
Serve se deshabilitó nuevamente (gateway.tailscale.mode=off) y se comprobó
que Tailscale ya no tiene rutas Serve. La integración iPhone deseada todavía
se concretó después en abrir ChatGPT, Obsidian y Spotify en la PC con
confirmación. Se creó un receptor independiente con ruta privada TCP 8080
y dirección Tailscale 100.73.94.38; el propietario confirmó `ready` desde
Safari. Se retiró la ruta 8443 porque el dominio no resolvía en el iPhone;
consultar `IPHONE_ROUTINES.md`. El panel OpenClaw sigue deshabilitado para
acceso Tailscale y los lugares se seleccionarán en el propio
iPhone. Las comprobaciones HTTPS del panel descritas abajo son evidencia histórica del
intento anterior, no el estado actual ni la solución pedida.

Ruta alternativa preparada el 13 de octubre de 2026:
iPhone → Tailscale → gateway OpenClaw de la PC Windows.
No utiliza el servidor del homelab ni WhatsApp para transportar el chat.
La PC y su gateway deben estar encendidos y tener conectividad. Un modelo cloud
sigue necesitando Internet; este acceso no ejecuta Karen dentro del iPhone.

## Estado actual

Tailscale está conectado en la PC y se observó un dispositivo iOS conectado.
El panel local responde en http://127.0.0.1:18789.
El propietario habilitó Serve/HTTPS en Tailscale y se activó
gateway.tailscale.mode=serve. El gateway confirmó el listener administrado,
HTTPS y WSS en desktop-jg4b3kn.tail1ff8ed.ts.net. Se verificó HTTP 200 con
validación normal del certificado y HTML del panel. El proveedor Ollama usa
127.0.0.1:11434 en esta PC y el modelo actual es gemma4:31b-cloud.
El panel autenticó también la conexión del navegador de Codex por HTTPS y
cargó las sesiones y el compositor de chat de F.R.I.D.A.Y. sin introducir
credenciales. No se enviaron mensajes de prueba a la conversación existente.
La prueba de chat desde el iPhone queda pendiente de la respuesta del usuario.

## Pasos pendientes

1. En el iPhone, activar Tailscale y abrir
   https://desktop-jg4b3kn.tail1ff8ed.ts.net/ en Safari.
2. Completar la autenticación/emparejamiento que solicite el panel. Aprobar
   únicamente el dispositivo del usuario identificado durante esta conexión.
3. Probar un intercambio desde el iPhone. Solo entonces confirmar la conexión.

Se mantiene la autenticación existente y la escucha local del gateway. Usar
Serve privado; no Funnel público. No copiar tokens a este documento ni al chat.
Conservar sesiones, memoria, modelo y la integración WhatsApp existentes.

## Recuperación

Si el gateway no arranca por Serve, ejecutar
`openclaw config set gateway.tailscale.mode off` y arrancar la tarea Windows
`OpenClaw Gateway`. Evitar reinicios duplicados: los cambios de configuración
pueden iniciar por sí mismos un reinicio supervisado.

El respaldo anterior a este cambio está en `.private/openclaw-before-iphone-20261013.json`.
Contiene configuración privada: no exportarlo, imprimirlo ni compartirlo.
Preferir restaurar solo el campo modificado para conservar cambios posteriores.

Referencia: https://docs.openclaw.ai/web/control-ui/connect-and-pair
