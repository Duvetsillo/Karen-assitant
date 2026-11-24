# Estilos y modelos — 1.6.0

## Apariencia

Abre Ajustes con doble clic en Karen y entra en **Apariencia**.
Selecciona **Cristal**, **Nube** u **Órbita**. La vista previa y el PET cambian
al instante. Puedes usar Tab y las flechas para elegir. Se guarda la selección
para el próximo arranque; las instalaciones anteriores conservan Cristal.

Cada forma tiene silueta, apéndices y material propios. Comparte los nueve
estados, mirada, arrastre y sincronización de boca con el audio real. No cambia
la identidad de voz ni el asistente. Los recursos se generan dentro de la
aplicación, sin imágenes remotas, descargas ni modelos de IA adicionales.

## Modelo de IA

En **Conversación** o **OpenClaw**, usa **Modelo de IA**. La lista muestra los
modelos configurados por tu Gateway, agrupados por proveedor. Seleccionar una
opción aplica el cambio; **En uso** muestra el modelo confirmado por OpenClaw.
**Predeterminado del agente** elimina la elección específica y recupera el
modelo predeterminado. **Actualizar modelos** vuelve a consultar el Gateway.

El alcance aparece bajo el selector. Con el agente `main`, la sesión actual
es `agent:main:main`. **Otros clientes de esa misma sesión también usan el
modelo seleccionado.** No es una preferencia privada de esta ventana. No se
modifican modelos globales, proveedores, claves, permisos, voz ni servicios.
Cada instalación aporta sus propios modelos, recursos y facturación.

Durante una respuesta el selector se bloquea. Si otro cliente tiene una tarea
activa, espera a que termine y pulsa actualizar. Si el Gateway rechaza una
elección, se muestra el error y se conserva el último estado confirmado.
La disponibilidad del catálogo no garantiza que un proveedor responda: puede
requerir recursos locales, saldo, conexión o credenciales del propietario.

## Integración y pruebas

El adaptador aislado usa el cliente oficial de OpenClaw y protocolo v4:

- `models.list`: `{ agentId, view: "configured" }`.
- `sessions.list`: `{ search: sessionKey, limit: 50 }`; se filtra la clave exacta.
- `sessions.patch`: `{ key: sessionKey, model: "provider/model" }`; `null` restaura el predeterminado.

Solo solicita `operator.read` y `operator.write`. No usa `config.patch` ni
reinicia el Gateway. Las credenciales permanecen en el proceso nativo o servidor.
La edición web usa las mismas operaciones, detrás de autenticación, comprobación
de origen y cabecera de cliente existentes. Una vista estática sin backend no
simula conexión ni modelos.

Referencias primarias: esquema distribuido por `@openclaw/gateway-protocol`
2026.8.1, documentación oficial
[control de sesiones](https://docs.openclaw.ai/gateway/protocol/rpc-session-control)
y [modelos](https://docs.openclaw.ai/concepts/models).

Pruebas repetibles: `npm run typecheck`, `npm test`, `npm run test:styles`,
`npm run test:server:browser` y `npm run audit:source`. El smoke de estilos usa
un perfil QA separado, verifica las tres formas y nueve estados, teclado,
movimiento reducido y persistencia. Las pruebas de contrato comprueban selección,
rechazos y exclusión de cambios globales. Las pruebas contra un Gateway real
dependen de la instalación y sus credenciales; no se ejecutan en CI público.
