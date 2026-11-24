# Rutina al llegar: abrir apps en la PC con confirmación

Preparada el 13 de octubre de 2026. El iPhone detecta la llegada mediante
Atajos y pide permiso; después envía la orden a esta PC por Tailscale.
No necesita el homelab ni el gateway de OpenClaw. No se configura domótica.

## Estado

- Receptor independiente: `iphone_routines.py`, escuchando solo en 127.0.0.1:18791.
- Acceso privado: http://100.73.94.38:8080.
- Tarea Windows: `Karen iPhone Routines`, inicio al iniciar sesión del usuario.
- Apps permitidas: ChatGPT, Obsidian y Spotify, identificadas con Get-StartApps.
- Solo se solicitan aperturas: no reproducción automática, escritura ni cierre de apps.
- Atajo **Karen** creado en el iPhone y probado manualmente: el usuario confirmó
  que se abrieron ChatGPT, Obsidian y Spotify. La ejecución por llegada queda
  pendiente de una prueba real del disparador de ubicación.

La PC debe estar encendida, con sesión Windows iniciada y Tailscale conectado.
El iPhone debe tener Tailscale activo. No se despertará una PC apagada.

## Configurar Atajos

La guía privada `.private/iphone-shortcut-setup.md` contiene los valores exactos
y el token necesario. No compartir esa guía: quien tenga el token y acceso a
la red Tailscale puede solicitar este único preset de aperturas.

1. Crear un atajo llamado **Karen** (nombre usado por el usuario).
2. Agregar **Elegir del menú** con la pregunta «¿Abrir ChatGPT, Obsidian y
   Spotify en la PC?» y las opciones **Sí, abrir** y **Ahora no**.
3. En **Sí, abrir**, agregar **Obtener contenido de URL**:
   URL `/prepare`, método POST, encabezado Authorization con Bearer y token,
   cuerpo JSON con `routine` (Texto) = `arrival_apps`.
   Antes de esta petición agregar **Tailscale → Connect (Conectar)** y
   **Tailscale → Get Status (Obtener estado)**. Si está desconectado, detener
   el atajo sin enviar el encabezado de autenticación. No usar Toggle,
   porque podría desconectar una VPN que ya estaba activa.
4. Agregar **Obtener valor del diccionario**, clave `ticket`, de la respuesta.
5. Agregar otro **Obtener contenido de URL**: URL `/confirm`, método POST,
   mismo encabezado, cuerpo JSON con `ticket` (Texto) = valor obtenido y
   `confirmed` (Booleano) = verdadero. No usar el texto "true".
6. Agregar **Quick Look**, debajo de `/confirm` y antes de **Ahora no**,
   seleccionando **Contents of URL** de la segunda petición. En la versión
   del iPhone del usuario no apareció **Show Result** en la búsqueda.
7. En **Ahora no**, agregar **Detener este atajo**. No enviar ninguna orden.
8. Probar el atajo manualmente con **Ahora no** primero.
9. En Atajos → Automatización → + → **Llegar**, seleccionar casa o trabajo
   en el mapa del propio iPhone y elegir este atajo. Elegir **Ejecutar
   inmediatamente** si aparece: eso inicia la pregunta, no la apertura.
   Si tu versión solo ofrece ejecución tras confirmación, mantenerla.
10. Probar la rama **Sí, abrir** únicamente cuando quieras abrir las apps.

Si el iPhone está bloqueado, puede pedir desbloquearlo para mostrar el menú.
El menú requiere una elección explícita; no hay aprobación predeterminada.
Puede reutilizarse el atajo en Llegar a otro lugar; Salir requiere crear
otro disparador explícito si también se desea el mismo preset al salir.

## Verificación y fallos

El iPhone informó «No se encuentra el servidor» al abrir el dominio. El
usuario confirmó `ready` al abrir http://100.73.94.38:8080/health. Se conservó
el reenvío TCP privado 8080 para evitar la dependencia del DNS del iPhone.
Las rutas HTTPS de prueba 443 y 8443 se retiraron. El transporte de este HTTP
es el túnel WireGuard cifrado entre iPhone y PC; requiere Tailscale conectado.
El usuario confirmó la apertura real de las tres apps desde el atajo manual.
La activación por llegada física a casa/trabajo sigue sin verificarse.

Cinco pruebas cubren cancelación, expiración, confirmación única persistente,
confirmaciones concurrentes y rechazo de órdenes arbitrarias o sin token.
Se verificó originalmente HTTPS desde esta PC y cancelación real sin
abrir ninguna app. Después, el usuario probó **Sí, abrir** desde su iPhone y
confirmó «bien, se abrio todo». Falta la prueba de llegada física.

Los planes vencen en cinco minutos. Una confirmación repetida devuelve el estado
guardado y no repite aperturas. Si falla durante el envío a Windows, el resultado
queda incierto y no se reintenta automáticamente. `completed` significa que se
intentó solicitar las aperturas; revisar `apps` para fallos. No confirma que
las ventanas se hayan mostrado ni que exista conexión a las cuentas de las apps.

Para comprobar conectividad, abrir `/health` en Safari: debe devolver
`status: ready` y `confirmation_required: true`. No se pueden abrir apps con GET.

## Desactivar

En PowerShell:

```powershell
Stop-ScheduledTask -TaskName 'Karen iPhone Routines'
Disable-ScheduledTask -TaskName 'Karen iPhone Routines'
tailscale serve --tcp=8080 off
```

Esto retira solo esta ruta y no modifica el gateway WhatsApp. No usar
`tailscale serve reset`, que también retiraría rutas de otros servicios.

Referencias Apple:
- https://support.apple.com/en-euro/guide/shortcuts/apd8ebfc4e8e/ios
- https://support.apple.com/guide/shortcuts/use-the-choose-from-menu-action-apdd7bf369da/9.0/ios/26
- https://tailscale.com/docs/features/mac-ios-shortcuts
- https://tailscale.com/docs/reference/connection-types
