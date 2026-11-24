# Karen en el iPhone

Cliente web instalable que conversa con el modelo configurado en `settings.json`
y comparte el archivo de conversaciones de Karen clásica (`KAREN_CORE_DB`, si
está definido). No requiere App Store, Xcode ni una cuenta de desarrollador.
Los archivos están en `mobile/`; el servidor independiente es `mobile_server.py`.
No modifica ni expone `core_local_api.py`.

## Inicio en el PC

Desde `C:\karen`:

```powershell
./start_karen_mobile.ps1 -Origin 'https://NOMBRE-DEL-PC.TU-RED.ts.net'
```

La consola debe permanecer abierta. También puedes probar solo en el PC con
`python mobile_server.py serve` y abrir `http://127.0.0.1:18793`.
Usa el mismo entorno de Python que Karen; necesita `requests` y los módulos
de personalidad de `desktop-pet/python`, ya usados por la aplicación clásica.
Sin `-Origin`, el script detecta el nombre del PC en Tailscale y muestra la URL
y el código de entrada en la consola local. La ruta de Serve debe existir.

## Acceso privado desde el iPhone

1. Conecta el iPhone a la misma red Tailscale que el PC.
2. En otra consola del PC ejecuta `tailscale serve --bg --https=443 http://127.0.0.1:18793`.
   Comprueba primero `tailscale serve status`: si 443 ya sirve otra aplicación,
   elige un puerto HTTPS libre y añádelo también a `-Origin`.
3. Abre en Safari la URL HTTPS devuelta por Tailscale.
4. Ejecuta `python mobile_server.py code` en el PC y pega el código en la app.
   El código es una credencial privada; no lo envíes por chat ni lo pongas en la URL.
5. En Safari pulsa Compartir, Añadir a pantalla de inicio y Añadir.

Serve conserva la ruta privada en segundo plano. Karen móvil debe seguir
ejecutándose y el PC debe estar encendido, conectado y sin suspender.
No se configura inicio automático con Windows. No se usa Funnel ni se abre
un puerto público o de LAN. Para desactivar solo este acceso HTTPS usa
`tailscale serve --https=443 off`; no uses `reset` si tienes otros servicios.

## Funciones

### Acceso directo cuando Safari no resuelve el nombre

El servidor admite un origen adicional explícito por IP Tailscale. Por ejemplo:

```powershell
python mobile_server.py serve --origin 'https://NOMBRE-DEL-PC.TU-RED.ts.net' --tailnet-origin 'http://100.73.94.38:18795'
tailscale serve --bg --tcp=18795 tcp://127.0.0.1:18793
```

Abre `http://100.73.94.38:18795` con Tailscale conectado. Sustituye la IP si
tu equipo tiene otra. El transporte entre dispositivos está cifrado por
Tailscale; este acceso no añade TLS de navegador y no admite service workers
ni caché sin conexión. Usa el HTTPS principal para todas las funciones PWA.
El servidor continúa en loopback y solo acepta la IP y el origen configurados.
El código de entrada sigue siendo el mismo. No se crea acceso público.
Para quitar este acceso: `tailscale serve --tcp=18795 off`.

- Chat con la personalidad de Karen y el proveedor/modelo configurado en el PC.
- Historial compartido: hasta 50 chats y los últimos 20 turnos del chat elegido.
- La nueva conversación móvil no cambia la selección activa del escritorio.
- Consulta de tareas, alertas y recuerdos públicos por proyecto mediante los
  contratos Core existentes. No crea mediciones ni ejecuta tareas.
- Lectura opcional con las voces del iPhone y dictado mediante el teclado de iOS.
- Pantalla instalada y recursos estáticos disponibles sin conexión; los datos
  privados y las respuestas requieren conexión con el PC y nunca se cachean.

No implementa activación por voz en segundo plano, notificaciones push,
herramientas administrativas, control de casa ni sesiones OpenClaw. El chat
usa el motor clásico configurado; no replica la sesión interna de Desktop Pet.
Los comandos `/…` se rechazan en el chat móvil. Los recuerdos se consultan,
pero no se transfieren automáticamente al modelo. Si el proveedor es remoto,
recibe el mensaje y el contexto de la conversación seleccionada, igual que
en el cliente clásico. La configuración del proveedor no se puede cambiar desde el móvil.

## Acceso y verificación

El secreto se guarda cifrado con DPAPI en `.private/mobile-access.dpapi`.
La sesión es una cookie firmada, HttpOnly y SameSite=Strict, con Secure en HTTPS
y duración de 14 días. El servidor solo escucha en loopback y valida Host y
Origin; no habilita CORS. Hay un límite de intentos de entrada y una generación
simultánea. Los errores no incluyen credenciales ni detalles internos del proveedor.

Para revocar todas las sesiones: detén el servidor, ejecuta
`python mobile_server.py rotate` y vuelve a iniciarlo. El comando muestra el
nuevo código únicamente en la consola local. Desconectar en Ajustes elimina
la cookie de ese navegador.

```powershell
python -m unittest qa.test_mobile_server
node --check mobile/app.js
node --check mobile/sw.js
```

Las pruebas usan SQLite temporal y un modelo simulado. Para validar en un
iPhone real, prueba instalación desde Safari, teclado abierto, orientación
horizontal, dictado del teclado, voz, regreso desde segundo plano y conexión
por datos móviles con Tailscale. La emulación de escritorio no sustituye estas pruebas.

Referencias: [instalación en iPhone](https://support.apple.com/en-az/guide/iphone/iphea86e5236/26/ios/26)
y [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).
