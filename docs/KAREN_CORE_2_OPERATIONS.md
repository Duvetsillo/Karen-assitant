# Karen Core 2 — uso y recuperación

## Escritorio clásico

Reabre con `./start_karen.ps1`. La ventana existente incorpora la pestaña
**Core 2**: preparar, revisar, ejecutar/reanudar, cancelar, recordar procedimientos,
consultar estado/memoria y analizar una ventana bajo demanda. Las confirmaciones
siguen en la ventana de administración existente.

Comandos disponibles:

```text
/plan Diagnostica mi PC
/ejecutar ID
/core2 planes
/core2 plan ID
/core2 reanudar ID
/core2 cancelar ID
/core2 recordar ID
/core2 estado
/vision activar
/vision ventana
/vision pantalla
/vision clic CAPTURE_ID X Y
/vision pausar
```

El panel muestra el plan y evidencias públicas, no cadena de pensamiento interna.

La orden de clic solo acepta una captura vigente y exige aprobación de escritorio.
La visión queda pausada por defecto; su ampliación se pospone por decisión del usuario
del 19 de noviembre de 2026. Jarvis tiene prioridad.

## Jarvis e iPhone

El mismo `mobile_server.py` sirve la interfaz habitual y la alternativa:

- En este PC: `http://127.0.0.1:18793/jarvis`.
- Por el acceso privado ya configurado: añade `/jarvis` a la URL de Karen.
- Mantiene el mismo código y cookie de acceso; no crea credenciales nuevas.

Jarvis permite conversar, preparar planes, ejecutar lecturas, cancelar y reanudar
lecturas interrumpidas, consultar recuerdos y pedir un análisis de ventana.
Las escrituras quedan pendientes de aprobación en el escritorio. No envíes una
propiedad `approved` en JSON: se rechaza y nunca concede permisos.

El acceso Tailscale sigue siendo transporte privado del teléfono. La inferencia
siempre ocurre en el PC; no usa el teléfono, otro servidor ni servicios cloud.
El servidor debe seguir abierto y el PC despierto para responder.

## Pet y API local

Compila Pet con `npm run build` y vuelve a abrirlo para cargar cambios de código.
Conserva conversación, voz, percepción, estilos, modos e IPC anteriores.
Con `KAREN_TASKS_DB` compartido puede consultar, sin ejecutar:

```text
/planes listar
/planes estado ID
```

La API Core v1 sigue autenticada, en loopback y de lectura. Añade `/v1/plans`
y `/v1/plans/ID`, que entregan estados y herramientas, nunca argumentos
cifrados, resultados privados ni nuevos permisos de ejecución.

## CLI

```powershell
python -m karen_core2 models
python -m karen_core2 status
python -m karen_core2 plan 'Diagnostica mi PC'
python -m karen_core2 run ID
python -m karen_core2 resume ID
python -m karen_core2 inspect ID
python -m karen_core2 cancel ID
python -m karen_core2 remember ID
python -m karen_core2 vision --scope window --capture
python alert_monitor.py watch-pc --interval 60 --trends
```

`--capture` es una acción explícita; no habilita captura continua. La CLI solicita
aprobación por cada escritura. No uses una cuenta de Windows distinta para
descifrar planes DPAPI del usuario original.

## Fallos y reversión

- Ollama no responde: verifica `ollama list` y su servicio local; no cambies a cloud.
- Sin presupuesto RAM/VRAM: cierra aplicaciones voluntariamente o espera. El
  router no mata procesos ni descarga modelos para eludir el límite.
- Sin modelo visual utilizable: las otras funciones siguen disponibles. Revisa
  las capacidades con el catálogo, no infieras visión por el nombre.
- Plan `interrupted`: inspecciona y reanuda explícitamente; las lecturas completas no se repiten.
- Plan `uncertain`: comprueba el efecto externo. No hay repetición automática de escrituras.
- Falta Pillow: la integración de visión informa la dependencia; no se instala automáticamente.

Antes del despliegue se conservaron archivos fuente y snapshots SQLite bajo
`.private/core2-recovery/`. Las migraciones añaden tablas y claves de extensión;
no eliminan las tablas v1. Puedes volver a la revisión de recuperación y conservar
las bases: los clientes v1 ignoran las extensiones. No sustituyas una base activa
por una copia antigua sin cerrar clientes y verificar qué datos nuevos perderías.

No se modifican `settings.json`, políticas administrativas ni archivos de
credenciales. Rebecca permanece fuera del alcance.
