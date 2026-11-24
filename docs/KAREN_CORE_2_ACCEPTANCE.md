# Karen Core 2 — aceptación y pendientes

Fecha: 19 de noviembre de 2026. Equipo de prueba: Windows, Ryzen 5 5500,
RTX 2060 de 6 GiB y 16 GiB RAM. Esta entrega amplía el código existente.
No reconstruye la aplicación ni modifica Rebecca.

## Prioridad acordada

El usuario priorizó Jarvis durante la implementación. La interfaz alternativa
queda disponible en `/jarvis`, con la vista habitual conservada. La ampliación
de visión se pospone: la integración existente queda preparada, pausada por
defecto y plegada en Jarvis. No se realiza captura continua ni descarga de modelos.

## Resultados comprobados

| Comprobación | Evidencia y alcance |
| --- | --- |
| Regresión Karen | `python -m unittest discover -s qa -p 'test_*.py'`: 253 pruebas correctas. Línea base: 207. Incluye la ventana Tk real con Core 2 y almacenes temporales. |
| Regresión Desktop Pet | `npm test -- --reporter=dot`: 163 pruebas correctas en 25 archivos. Línea base: 161. |
| Transporte y aceleración de voz Pet | `python -m unittest discover -s tests -p 'test_*.py'` desde `desktop-pet`: 25 pruebas correctas. |
| Compilación Pet | `npm run build`: TypeScript, Vite y Electron correctos. Advertencia de tamaño del bloque Pixi de 522,63 kB; no impide la compilación. |
| JavaScript Jarvis | `node --check mobile/jarvis.js` correcto. |
| Plan real | Seis pasos de diagnóstico del PC terminados y verificados, una ejecución por paso. Lecturas reales; no se efectuó mantenimiento destructivo. |
| Plan generado por IA | Ollama generó y validó un plan estructurado para listar `C:/karen`. El plan generado no se ejecutó. |
| Memoria | El procedimiento del diagnóstico verificado se guardó y recuperó como memoria procedimental confirmada en una base temporal. |
| Recuperación y cancelación | Pruebas de lectura interrumpida, dependencias, bloqueo entre procesos, cancelación, reintentos limitados y escritura incierta que no se repite. |
| Modelos locales | Se consultaron capacidades reales de ocho modelos utilizables. Se excluyeron referencias cloud y metadatos no verificables. Cero modelos descargados. |
| Visión preparada | Antes de posponer su ampliación, `qwen3.5:4b` reconoció «ERROR 503» en una ventana sintética propia. No se guardaron capturas del usuario. No certifica control visual general. |
| Jarvis en navegador | Se preparó y ejecutó el diagnóstico de seis etapas, se revisaron resultados, se recordó el procedimiento y se consultó la memoria. Visión queda plegada. |
| Adaptación móvil | A 390 px, el contenido y la ventana medían 380 px útiles: sin desbordamiento horizontal. Verificación de navegador; no sustituye una prueba física de Safari. |
| Acceso existente | `/jarvis`, `/api/core2/status` y `/api/v1/chats` dieron HTTP 200 autenticado por localhost, HTTP privado de Tailscale y HTTPS privado existentes. Estado local-only y visión pausada confirmados. |
| Configuración | SHA-256 de `settings.json` idéntico antes y después. Se mantienen código y archivos de credenciales existentes. |

La aceptación local se ejecutó con `python qa/verify_core2_live.py`, sobre bases
temporales. La evidencia técnica detallada está en
`.private/core2-live-acceptance.json`, excluida de Git. La captura de Jarvis está
en `qa/karen-core2-jarvis.jpg`, también excluida de Git.

## Latencias observadas

Son mediciones de una sola ejecución, no un benchmark estadístico ni una promesa:

| Uso | Modelo | Tiempo total de generación |
| --- | --- | --- |
| Plan estructurado | qwen3.5:2b | 7,866 s |
| Conversación corta, carga en frío | gemma3:1b | 14,527 s |
| Análisis de ventana sintética | qwen3.5:4b | 8,132 s |

La conversación clásica conserva streaming. El chat HTTP móvil conserva su
contrato de respuesta completa. El router limita contexto y salida, serializa
clientes Python, descarga de VRAM los modelos grandes al terminar y conserva
los pequeños como máximo 60 segundos. El resto de aplicaciones que utilicen
Ollama directamente no participa en ese bloqueo. Los límites de concurrencia
globales del lanzador solo se aplican cuando este inicia un Ollama nuevo.

## Permisos y compatibilidad

El planificador solo acepta herramientas registradas y parámetros validados.
No registra un ejecutor de comandos arbitrarios. Las herramientas administrativas
anteriores conservan sus confirmaciones. La API móvil no puede heredar la
aprobación de escritorio ni concederla mediante JSON. Las escrituras inciertas
requieren revisión externa antes de cualquier nuevo intento.

Los planes y evidencias completas usan DPAPI del usuario de Windows; la API v1
solo publica metadatos. La auditoría registra herramienta, actor, tiempos,
estado y huellas de parámetros/resultados. La memoria contextual rechaza
credenciales. Las capacidades de un agente lógico no conceden permisos nuevos.

Se conservan los puntos de entrada, herramientas e integraciones anteriores.
Las pruebas automatizadas y la compilación no demuestran por sí solas el correcto
funcionamiento de todos los dispositivos o servicios reales del usuario.

## Pendientes explícitos

- [ ] Visión: ampliar pruebas de ventanas reales, varios monitores, DPI, pausa
  durante inferencia, aplicaciones elevadas y acciones visuales autorizadas.
  Pospuesto por el usuario. No activar captura ni descargar modelos automáticamente.
- [ ] Probar Jarvis físicamente en Safari del iPhone y como aplicación añadida a inicio.
- [ ] Reabrir el cliente Pet compilado y probar voz, activación por nombre, estilos,
  cancelación y convivencia con el escritorio clásico usando los dispositivos reales.
- [ ] Verificar operaciones reales de Gmail, calendario, recordatorios WhatsApp,
  Home Assistant, SSH y Proxmox cuando el usuario las necesite. No se enviaron
  mensajes, alteraron calendarios ni cambiaron equipos externos durante la aceptación.
- [ ] Recoger suficientes muestras del monitor para evaluar tendencias durante
  uso normal. Las alertas de servicios se probaron como lógica; no se provocaron
  fallos en servicios reales. Correlación no equivale a causa.
- [ ] Medir latencia fría/caliente y convivencia de Ollama con voz y otras aplicaciones.

## Recuperación

Ambos repositorios usan la rama `codex/karen-core-2`. Un commit de recuperación
registra el trabajo que ya existía antes de esta evolución, separado de los commits
nuevos. Los archivos originales y copias SQLite verificadas se conservan en
`.private/core2-recovery/20261119T055905Z`. No se publicó ni subió código remoto.
Consulta `KAREN_CORE_2_OPERATIONS.md` antes de revertir una base de datos.
