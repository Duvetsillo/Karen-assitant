# Memoria personal de Karen Pet

La interfaz principal para el usuario es **Desktop Pet**. El cliente Tkinter se
conserva como herramienta opcional y no es necesario abrirlo para gestionar memoria.

## Qué significa aprender en esta fase

La personalización usa recuerdos y fuentes persistentes en SQLite. No modifica
pesos del modelo. Un enlace compartido por el usuario identifica una fuente propia;
el contenido público de esa fuente no se convierte automáticamente en biografía,
preferencia actual ni autorización para usar herramientas.

`runtime/personal_learning.py` añade un registro explícito de perfiles Facebook,
Instagram y Spotify, con validación de dominio, formato y procedencia. Registra
observaciones con fuente y fecha. Las afirmaciones biográficas no confirmadas se
marcan `PENDIENTE` / `inferred` y se excluyen del contexto confirmado. Los perfiles
no se consultan automáticamente desde ese programa: las observaciones deben
proceder de una revisión autorizada.

Los enlaces reales, datos personales, observaciones y respaldos se guardan
localmente en rutas privadas e ignoradas por Git. Los tests usan perfiles
sintéticos. No se guardan cookies ni contraseñas, no hay scraping de cuentas
privadas y no se infieren atributos sensibles a partir de fotos o música.

## Arrancar Pet con la memoria existente

```powershell
.\start_pet.ps1 -CheckOnly
.\start_pet.ps1
```

El lanzador lee `KAREN_CORE_DB` del proceso o de la configuración del usuario
Windows, verifica rutas y arranca el Pet de `runtime/desktop-pet`. Acepta
`-PetRoot`, `-CoreDatabase` y `-ProjectRoot` si las instalaciones están en otras
carpetas. Requiere código y dependencias del Pet ya preparados; no descarga
modelos ni crea otra base. Desde código, `npm run dev` compila y abre Electron.

Un Pet ya abierto necesita reiniciarse para tomar una variable de entorno nueva.
Este lanzador lee también la configuración persistente, aunque la consola o el
Explorador se hubieran abierto antes de cambiarla. `-CheckOnly` comprueba rutas y
herramientas; no certifica micrófono, modelo, Gateway ni inferencia de voz.

En su chat:

```text
/memoria listar Personal
/memoria buscar Personal | música
/memoria preparar Personal | música
/memoria enviar
```

Listar y buscar son lecturas locales sin Gateway. Preparar muestra hasta tres
recuerdos confirmados con un máximo de 400 caracteres cada uno. Enviar autoriza
ese contenido a la sesión del proveedor activo. **Si ese proveedor es remoto,
los recuerdos enviados salen del PC.** No se envían automáticamente por importar
o registrar una fuente. No se alteraron esos permisos durante la incorporación.

La recuperación automática del perfil personal dentro del Pet y el panel visual
«Mis datos» siguen pendientes. No se presenta esta incorporación como ese panel
terminado, ni como aprendizaje autónomo continuo de todas las redes.

## Incorporar fuentes sin usar el cliente verde

Desde `runtime/`, usando la misma base que Pet:

```powershell
$personalDb = [Environment]::GetEnvironmentVariable('KAREN_CORE_DB', 'User')
python personal_learning.py --db $personalDb register instagram URL_DEL_PERFIL
python personal_learning.py --db $personalDb observe ID_DE_FUENTE 'Texto observado en la fuente'
python personal_learning.py --db $personalDb observe ID_DE_FUENTE 'El perfil afirma una ocupación' --claim
python personal_learning.py --db $personalDb list --query música
```

Reemplaza URL_DEL_PERFIL e ID_DE_FUENTE por el enlace y el ID devuelto. El registro
no inicia sesión ni descarga contenido. Facebook admite `profile.php?id=ID`,
Instagram una URL de perfil y Spotify `/user/ID`. Se rechazan enlaces con
credenciales, parámetros ajenos y dominios que imitan al proveedor.

Una observación de Spotify puede añadir `--evidence-url` con la URL pública de
la lista concreta, manteniendo separado el perfil del propietario y la evidencia.
Una canción en una lista demuestra presencia en esa lista en la fecha observada;
no demuestra frecuencia de escucha, estado emocional ni gusto actual. Las
recomendaciones automáticas de la plataforma no cuentan como elecciones propias.
Las afirmaciones laborales y otros datos antiguos requieren confirmación antes
de usarse como hechos personales actuales.

Para corregir o eliminar datos se conserva el gestor local:

```powershell
python memory_cli.py --db $personalDb edit ID_DE_RECUERDO 'Contenido corregido'
python memory_cli.py --db $personalDb delete ID_DE_RECUERDO
```

Eliminar un recuerdo del registro no borra las copias en respaldos anteriores.
Las fotos y exportaciones privadas deben entregarse voluntariamente e importarse
por una vía revisada; la carga de fotografías en memoria del Pet sigue pendiente.

## Validación

- Nueve pruebas nuevas: perfiles y dominios permitidos, procedencia, fechas,
  persistencia, deduplicación, exclusión de afirmaciones pendientes, rechazo de
  credenciales y separación entre perfil y evidencia de una lista.
- Lectura de la base operativa con el `CoreStore` real de Pet, sin abrir una
  conexión a OpenClaw ni enviar datos.
- El código probado del Pet sigue en su repositorio separado; esta fase usa su
  puente Core existente y no modifica ese cliente para ejecutar herramientas.
- Regresión completa del runtime: **342 pruebas OK en Python 3.11, 60.508 s**.
  Puente Core/Gateway del Pet: **34 pruebas OK**. Cliente histórico: **4 pruebas
  pytest OK**. Lanzador verificado con `-CheckOnly`, análisis sintáctico de
  PowerShell y rechazo de una base inexistente; no se abrió una nueva instancia.
