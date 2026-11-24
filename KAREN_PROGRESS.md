# Karen — repositorio e integración del runtime

Fecha: 24 de noviembre de 2026.

## Destino correcto

- Repositorio: `https://github.com/Duvetsillo/Karen-assitant`.
- Carpeta: `C:\Users\Dayve\Documents\GitHub\Karen-assitant`.
- La publicación anterior fue a `Duvetsillo/karen-classic-core`, cuyo checkout
  operativo está en `C:\karen`. Esa diferencia explica por qué los cambios no
  aparecían en este repositorio.

## Integración

El código operativo ya validado se incorpora bajo `runtime/`, conservando
`cliente.py`, `config.py`, documentación y pruebas históricas en la raíz.
Los siete commits de la actualización mantienen autoría, fechas y mensajes
al aplicarse a ese directorio. La base anterior se importa como snapshot;
no se mezclan dos clientes con contratos diferentes en los mismos archivos.

Antes de añadir esta documentación se comprobó igualdad exacta entre el árbol
`runtime/` y el commit original `e7a1f1b`: ambos tienen Git tree
`b88c13a04531bf24c84cfdc6d85765e90e558050`.

Las dependencias de código locales usadas en la verificación se enlazan mediante
junctions ignorados por Git. No se copian modelos, archivos privados, configuración
de usuario ni los cambios de Home Assistant que seguían sin commit en `C:\karen`.

## Validación

- Evidencia anterior: 333 pruebas correctas sobre código limpio en Python 3.11.
- Suite Windows desde `runtime/` en esta carpeta: **333 pruebas OK, Python 3.11,
  60.844 s**.
- Cliente histórico: **4 pruebas pytest OK, 0.03 s**; `python cliente.py --help`
  correcto. `cliente.py`, `config.py` y `tests/` conservan su contenido anterior.
- CI portable de la raíz: limitada explícitamente a las pruebas históricas en
  `tests/`, evitando mezclar módulos `config` y dependencias Windows del runtime.
- Comandos, límites y siguientes fases: `runtime/docs/PERSONAL_AI_UPGRADE.md`.

## Siguiente tarea

Continuar el desarrollo y publicar los próximos cambios en este repositorio.
La siguiente fase funcional de Karen sigue siendo full-duplex con AEC comprobable
y STT incremental, según el registro del runtime. La integración utiliza avance
normal de `main`, sin forzar el push ni sustituir su historial anterior.
