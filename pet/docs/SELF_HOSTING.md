# Desplegar Karen en un servidor

El cliente Windows vive sobre el escritorio. El servidor funciona sin entorno
gráfico y muestra la mascota en una pestaña del navegador. No instala OpenClaw,
Ollama, modelos ni recursos privados de voz. Todas las sesiones autorizadas
comparten el mismo agente; no es un servicio con aislamiento entre usuarios.

## Variables

| Variable | Uso |
| --- | --- |
| `KAREN_ACCESS_TOKEN` / `_FILE` | Token aleatorio de al menos 32 caracteres para acceder a Karen |
| `KAREN_GATEWAY_URL` | Gateway existente, WSS remoto o WS loopback |
| `OPENCLAW_GATEWAY_TOKEN` / `_FILE` | Bootstrap de tu Gateway |
| `OPENCLAW_GATEWAY_PASSWORD` / `_FILE` | Alternativa para Gateway con contraseña |
| `KAREN_AGENT_ID` | Agente, por defecto `main` |
| `KAREN_PUBLIC_ORIGIN` | Origen HTTPS exacto, sin ruta; coincide con Host y Origin |
| `KAREN_DATA_DIR` | Directorio privado persistente; por defecto `./data` |
| `HOST` / `PORT` | Por defecto `127.0.0.1:3000`; Docker usa `0.0.0.0` dentro del contenedor |
| `KAREN_SECURE_COOKIES` | `true` en producción. `false` solo permite un origen loopback de pruebas |

Los archivos `_FILE` tienen precedencia. No hay credenciales predeterminadas.
`.env` y `secrets/` se excluyen de Git y Docker.

## Node sin Docker

Instala Node 24. Clona el repositorio, ejecuta `npm ci` y `npm run build`.
Para una prueba local en Bash con secretos nuevos:

```sh
export KAREN_ACCESS_TOKEN="$(openssl rand -hex 32)"
export KAREN_PUBLIC_ORIGIN=http://127.0.0.1:3000
export KAREN_SECURE_COOKIES=false
export KAREN_GATEWAY_URL=ws://127.0.0.1:18789
# Añade tu propio bootstrap para conectar tu Gateway:
# export OPENCLAW_GATEWAY_TOKEN_FILE=/ruta/privada/openclaw-token
npm run start:server
```

Node no carga `.env` automáticamente. Puedes usar
`node --env-file=.env dist-electron/server/index.js` si ese archivo contiene las
variables necesarias y tiene permisos restrictivos. Para consultar el token de
esta prueba local utiliza tu terminal; no lo añadas a capturas o reportes.

Para producción, usa systemd o un supervisor equivalente con usuario sin privilegios,
directorio de datos privado, archivos de secretos y proxy TLS. No incluyas tokens
en argumentos de proceso ni en unidades versionadas.

## Proxy HTTPS

Ejemplo Caddy en el mismo host que el puerto publicado por Compose:

```caddyfile
karen.example.com {
    reverse_proxy 127.0.0.1:3000 {
        flush_interval -1
    }
}
```

Configura `KAREN_PUBLIC_ORIGIN=https://karen.example.com`. Conserva Host, permite SSE
y desactiva el almacenamiento en búfer del proxy. Las cookies Secure viajan por
HTTPS desde el navegador aunque el tramo proxy→Karen sea local. No añadas CORS
abierto ni debilites las comprobaciones de origen.

## Conexión con OpenClaw

Usa tu endpoint WSS autenticado existente. No se modifica ni debilita la política
de autenticación, origen, vinculación o permisos del Gateway.

Para un túnel SSH en el host donde corre Node:

```sh
ssh -N -L 127.0.0.1:18789:127.0.0.1:18789 usuario@tu-servidor-openclaw
```

Node puede conectar a `ws://127.0.0.1:18789`. El loopback de un contenedor es el
propio contenedor: no apunta al host. Para Docker usa un endpoint WSS alcanzable
o configura tu red explícitamente sin relajar la exigencia de TLS remoto.

El primer acceso puede requerir vinculación. En el host de OpenClaw revisa
`openclaw devices list` y aprueba solo el dispositivo esperado. Después reconecta
desde Karen. No se solicitan permisos administrativos.

## Persistencia y revocación

El volumen contiene ajustes, identidad Ed25519 y tokens de dispositivo cifrados
con AES-256-GCM. La clave está en `vault.key`: protege el volumen completo y sus
copias. Esto no protege frente a quien tenga acceso completo al host. Los archivos
se crean con permisos restrictivos y no se sirven por HTTP. Los tokens bootstrap
no se guardan en el volumen.

Cambiar el origen del Gateway descarta su token de dispositivo anterior. No
compartas identidades entre instalaciones. Para revocar navegadores, reinicia la
instancia (las sesiones están en memoria) y rota el token de acceso. La revocación
del dispositivo se gestiona en OpenClaw. Son credenciales independientes.

`/healthz` comprueba HTTP, no certifica autenticación ni disponibilidad del modelo.
Diagnóstico muestra la conexión real. No se registran conversaciones ni audio en
los logs del servidor. Protege también los logs del proxy y las copias de seguridad.
