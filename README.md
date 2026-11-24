# Karen Desktop Pet

Mascota holográfica original para **Windows** y **servidores autoalojados**.
Karen representa tu asistente de [OpenClaw](https://docs.openclaw.ai/): no incorpora
otro modelo de IA ni sustituye las herramientas o permisos de tu agente.

Cada instalación usa los recursos de quien la ejecuta: su servidor, Gateway,
proveedores de modelos, credenciales y facturación. Este proyecto no ofrece una
API central ni acceso a las cuentas o infraestructura del mantenedor. Descargar
Karen no da permiso para usar esos recursos. No compartas tus claves ni abras
tu Gateway para dar servicio a otras instalaciones.

**Windows:** mascota transparente sobre el escritorio, bandeja, arrastre, expresiones,
conversación y voz del sistema. **Servidor:** panel y mascota en el navegador,
conversación de texto, eventos y animaciones; no necesita escritorio ni Electron.

## Windows

1. Instala y configura tu propio **OpenClaw Gateway**. Karen es la interfaz del
   asistente; no instala OpenClaw ni aporta un modelo o credenciales.
2. Descarga el archivo `Setup.exe` de la versión deseada en
   [Releases](https://github.com/Duvetsillo/karen-desktop-pet/releases) y ejecútalo.
   El instalador incluye Electron: **no necesitas Node ni herramientas de desarrollo**.
3. Al terminar, el instalador abre Karen. También puedes usar el acceso directo.
   Si aún no encuentra una credencial, abre Ajustes automáticamente. En **OpenClaw**,
   elige «En este equipo» y pulsa
   **Guardar y conectar**. Karen usa la configuración local de OpenClaw.
4. Si el Gateway está en otro equipo, elige «En otro equipo», introduce su
   dirección `wss://`, el agente y tu token, y pulsa **Guardar y conectar**.
   OpenClaw puede pedir la aprobación del dispositivo: sigue el aviso de Karen,
   aprueba solo la solicitud esperada en el host del Gateway y vuelve a conectar.

El instalador sin certificado puede mostrar un aviso de editor desconocido.
Para compilar desde el código en vez de usar el instalador:

```powershell
git clone https://github.com/Duvetsillo/karen-desktop-pet.git
cd karen-desktop-pet
npm ci
npm run build
npm run dev
# Para generar el instalador:
npm run package
```

`node scripts/native-smoke.cjs` comprueba ventanas, ajustes, voz Windows, conexión al Gateway y errores del renderizador. Para conservar capturas y perfil QA anteriores, ejecútalo desde un directorio temporal nuevo usando la ruta absoluta del script; la aplicación se localiza desde el propio script. Define `KAREN_SMOKE_EXECUTABLE` con la ruta absoluta de `win-unpacked/Karen Desktop Pet.exe` para comprobar también el ejecutable empaquetado. La prueba no envía un mensaje al modelo ni valida el instalador NSIS tras instalarlo.

Para compilar se requiere Node 24; las funciones nativas requieren Windows 11
x64. No se necesita Rust ni MSVC. Abre Ajustes en cualquier momento con doble
clic en Karen o desde la bandeja. La configuración local se lee de
`~/.openclaw/openclaw.json`; los tokens remotos y la identidad del dispositivo
se guardan cifrados con DPAPI en tu cuenta Windows.

- Arrastra el cuerpo para moverla. Clic derecho abre el menú nativo.
- Las zonas transparentes dejan pasar clics mediante una máscara alfa.
- **Ctrl+Alt+K** o la bandeja recuperan el control tras ignorar clics.
- Activa opcionalmente inicio con Windows, prioridad de ventana y bajo consumo.
- **Sistema → Modo de funcionamiento** o el menú de bandeja: Normal, Gaming y No molestar. Gaming aplica 15 FPS, quita partículas, animación, seguimiento del cursor, burbujas y prioridad de ventana; conserva la voz configurada. No molestar además suspende la escucha continua y la voz automática. Volver a Normal restaura las preferencias guardadas. La selección es manual: no detecta juegos ni cambia Windows.
- Los quince estados incluyen reposo, escucha, procesamiento, habla, risa, enojo, tristeza, sorpresa, orgullo, curiosidad y errores.
- La expresión de una respuesta sigue las palabras de Karen; no interpreta el ánimo privado del usuario.
- **Apariencia → Tamaño del PET:** escala de 50 a 200 %, presets y vista previa en directo.
- **Apariencia → Cinco formas:** Cristal, Nube, Órbita, Lucero y Flor. Todas tienen manos y piernas; las dos nuevas destacan más sus gestos. Cambio inmediato y selección guardada.
- **Conversación / OpenClaw → Modelo de IA:** catálogo real por proveedor, modelo actual y regreso al predeterminado del agente.
- El modelo se cambia para la sesión actual. Otros clientes de esa sesión comparten el cambio; no se modifica la configuración global.
- El tamaño se recuerda al abrir y se limita al monitor sin deformar la mascota.
- Pupilas independientes, cejas y ojos asimétricos hacen más visibles la mirada y las expresiones.
- El modo de bajo consumo y el reposo limitan el renderizado a 15 FPS.
- La boca sigue el audio real mediante Web Audio, no una animación de habla falsa.
- Las respuestas y avisos aparecen bajo Karen; pulsa una respuesta para leerla completa en Conversación.
- **Voz:** prueba la salida de Windows y configura dictado local con tus propios recursos.
- **Percepción:** transcribe audio del PC por WASAPI y revisa capturas antes de enviarlas al modelo con visión.
- **Señalamiento:** toca una captura de pantalla para que Karen marque el lugar en el escritorio, o pídele que encuentre un objeto con tu modelo de visión. La marca dura ocho segundos y deja pasar los clics.
- Al señalar, Karen levanta la mano del lado del objetivo. El gesto se interrumpe al quitar la marca y respeta movimiento reducido.
- [Configurar micrófono, audio del PC y pantalla](docs/PERCEPTION.md).
- [Crear una voz original compartida con Karen Local y WhatsApp](docs/SHARED_VOICE.md).
- [Estilos del PET y selección de modelos](docs/STYLES_AND_MODELS.md).

## Servidor Linux / Docker

El servidor aloja la misma interfaz y reutiliza el adaptador oficial de OpenClaw.
Cada usuario debe aportar su propio Gateway y credenciales. No se incluyen cuentas,
llaves, conversaciones, modelos ni datos del mantenedor.

```sh
git clone https://github.com/Duvetsillo/karen-desktop-pet.git
cd karen-desktop-pet
cp .env.example .env
mkdir -p secrets
chmod 700 secrets
openssl rand -hex 32 > secrets/karen_access_token
# Escribe tu token de OpenClaw sin incorporarlo al código:
read -r -s -p 'OpenClaw token: ' OPENCLAW_TOKEN
printf '%s' "$OPENCLAW_TOKEN" > secrets/openclaw_gateway_token
unset OPENCLAW_TOKEN
chmod 600 secrets/*
```

Edita `.env` con tu dominio HTTPS y Gateway WSS. Después:

```sh
docker compose up -d --build
```

Configura un proxy HTTPS hacia `127.0.0.1:3000` y conserva el encabezado Host.
Entra desde tu dominio y utiliza el contenido de `secrets/karen_access_token`.
**El token del navegador es distinto del token del Gateway.**

El servidor funciona como un único asistente compartido por personas de confianza.
No hay aislamiento entre cuentas o conversaciones. Usa instancias y credenciales
separadas para grupos distintos. Quien acceda puede ejecutar las herramientas del
agente con sus permisos de OpenClaw.

Consulta [despliegue detallado](docs/SELF_HOSTING.md) para Node sin Docker, SSH,
proxy TLS, vinculación de dispositivo, persistencia y recuperación.

### English quick start

Clone this repository and use Node 24. Run `npm ci`, `npm run build`, then configure
the environment and start `npm run start:server`, or use Docker Compose behind HTTPS.
Provide your own OpenClaw Gateway and a separate random browser access token. See
[self-hosting](docs/SELF_HOSTING.md). Windows desktop and system voice features
belong to the native client; server mode supports text chat, state animations and
settings without a GUI on the host.

## Voz opcional en Windows

La voz instalada de Windows funciona sin recursos del mantenedor. Prefiere una voz
española disponible y genera WAV para sincronización RMS y selección de salida.

Los adaptadores de voz local son opcionales. Configura `KAREN_PROJECT_ROOT` con tus
propios recursos: `voice_worker.py`, `voice-runtime/Scripts/python.exe`, modelos
locales y, para el servicio expresivo, `voice-models/.expressive-token`. No se
incluyen modelos, voces privadas ni los servicios originales del mantenedor.
Sin estos recursos se mantienen disponibles el texto y la voz de Windows.

El micrófono solo se abre tras una acción explícita. No se usa cámara. La interfaz
`WakeWordDetector` admite futuros detectores; **no hay palabra clave activada**.
El modo servidor no incluye TTS/STT. No se afirma que estén activos si faltan sus
dependencias.

## Integración y seguridad

- Cliente oficial `@openclaw/gateway-client` y protocolo `2026.8.1`, wire v4.
- Reto firmado Ed25519, identidad persistida y reconexión exponencial de 1–30 s.
- Permisos `operator.read`/`operator.write`; capacidad `tool-events`.
- Sesión `agent:<id>:main`; `chat.send`, `chat.history`, `chat.abort`.
- Streaming incremental y eventos de herramientas asociados por runId.
- La configuración de modelos pertenece a tu OpenClaw, no a esta aplicación.
- El servidor exige autenticación, cookies HttpOnly/SameSite=Strict, origen exacto,
  protección de mutaciones y límites de acceso. No envía secretos al navegador.
- Los datos persistidos se guardan fuera del código. No publiques tu directorio
  privado de OpenClaw como archivos web.

Lee [SECURITY.md](SECURITY.md) antes de exponer una instancia.

## Desarrollo y pruebas

```sh
npm ci
npm run typecheck
npm test
npm run audit:source
npm run build
```

Las pruebas usan datos sintéticos y un servidor de contrato WebSocket. No necesitan
llaves reales ni envían tareas a tu agente. Cubren estados, configuración, sesiones,
streaming, firma, reconexión y seguridad del servidor. CI valida Windows y Linux y
construye la imagen de contenedor.

`npm run preview` abre una vista de desarrollo sin conexión real; no es el servidor
autenticado. Usa `npm run start:server` para autoalojar la aplicación compilada.
Las pruebas nativas opcionales requieren Windows; los recursos de voz adicionales
y las pruebas de hardware requieren configuración propia.

## Arquitectura

| Capa | Ubicación |
| --- | --- |
| Ventanas y funciones Windows | `electron/main.ts` |
| Adaptador oficial aislado | `electron/gateway.ts` |
| Servidor autenticado y eventos SSE | `server/app.ts` |
| Identidad cifrada del servidor | `server/storage.ts` |
| Validación y proyección de eventos | `shared/` |
| Renderizador original y estados | `src/pet/`, `src/state/` |
| Puente HTTP del navegador | `src/server-bridge.ts` |
| Adaptadores de audio | `src/voice/`, `electron/voice.ts` |

La apariencia puede sustituirse sin modificar OpenClaw. Electron usa más memoria
que Tauri; el renderizador reduce efectos y FPS y se pausa al ocultarse. El servidor
no ejecuta Electron ni un modelo de IA adicional.

## Contribuir

Licencia [MIT](LICENSE). Consulta [CONTRIBUTING.md](CONTRIBUTING.md). Los cambios
deben resolver problemas reales y pasar por pull requests y revisiones verificables.
No se aceptan credenciales, datos personales ni actividad ficticia para métricas.
