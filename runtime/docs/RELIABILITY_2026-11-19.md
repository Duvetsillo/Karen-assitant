# Mejoras de estabilidad — 19 de noviembre de 2026

Esta entrega corrige nueve problemas de voz, catálogo e integraciones. Cada
corrección incluye una prueba de regresión y su propio commit.

## Cambios

| Área | Problema corregido |
| --- | --- |
| Voz | Un fragmento con miles de frases agotaba la pila por llamadas recursivas. |
| Voz | Finalizar dos veces una respuesta repetía la última frase. Ahora finalizar es idempotente y se rechazan fragmentos posteriores. |
| Catálogo | Un callback fallido impedía notificar a los demás suscriptores. Ahora se registra el error y continúan las notificaciones. |
| Catálogo | Metadatos cloud inválidos podían impedir usar los modelos locales. Ahora la consulta opcional valida sus capacidades. |
| Home Assistant | Respuestas malformadas provocaban excepciones o podían mostrar éxito tras un error HTTP. Ahora se valida el estado HTTP, el objeto de respuesta y sus estados. |
| Home Assistant | Un archivo de configuración ilegible o con tipos incorrectos podía cerrar el flujo de consulta. Ahora se devuelve un error sin enviar una orden. |
| Proxmox | Valores infinitos o NaN podían fallar al convertirse a enteros. Ahora se descartan y se conservan las métricas válidas. |
| Proxmox | Estados de invitados recibidos como listas u objetos interrumpían el inventario. Ahora se muestran como desconocidos. |
| Catálogo | URLs con IPv6 incompleto, puertos inválidos, credenciales, query o fragmento podían fallar antes de manejar errores. Ahora se rechazan antes de consultar la red. |

## Verificación

Las 16 pruebas nuevas no requieren micrófono, modelos activos, credenciales ni
servidores físicos. Usan respuestas HTTP simuladas y comprueban también que no
se envían peticiones cuando la configuración es inválida.

```powershell
python -m unittest qa.test_response_stream qa.test_catalog qa.test_ha_resilience qa.test_proxmox_resilience
python -m unittest discover -s qa -p 'test_*.py'
```

Las 16 pruebas nuevas se verificaron además sobre una exportación limpia de
`git archive`, para comprobar que no dependen de archivos locales sin commit.
La suite completa requiere las dependencias y los módulos de Desktop Pet
descritos en el README. Las pruebas simuladas no validan conectividad real,
audio ni efectos sobre dispositivos físicos.

Los cambios que ya estaban pendientes en el directorio de trabajo se conservan
fuera de estos commits. Esta entrega no los publica ni los incorpora como
parte de las correcciones anteriores.
